from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging

from api.backtest import BacktestAPI
from server.schemas import RunBacktestRequest, RunBacktestResponse, StrategyInfoSchema

logger = logging.getLogger(__name__)

app = FastAPI(title="Backtest API Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/strategies")
def get_strategies():
    names = BacktestAPI.list_strategies()
    # Filter out benchmark from user selection
    names = [n for n in names if n != "BuyAndHoldStrategy"]
    strategies = []
    for name in names:
        info = BacktestAPI.get_strategy_info(name)
        strategies.append(info)
    return strategies

@app.get("/api/strategies/{name}")
def get_strategy(name: str):
    try:
        return BacktestAPI.get_strategy_info(name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/backtest", response_model=RunBacktestResponse)
def run_backtest(req: RunBacktestRequest):
    try:
        # Build strategy
        strat = BacktestAPI.build_strategy(req.strategy, **req.strategy_params)
        
        # Run 
        raw_results = BacktestAPI.run(
            symbol=req.symbol,
            timeframe=req.timeframe,
            start=req.start,
            end=req.end,
            strategies={req.strategy: strat},
            initial_capital=req.initial_capital,
            lookback=req.lookback,
            commission_pct=req.commission_pct,
            flat_commission=0.0,
            auto_fetch=req.auto_fetch,
            include_benchmark=req.include_benchmark
        )

        # Format results for JSON response
        formatted_results = {}
        for strat_name, res in raw_results.items():
            formatted_trades = []
            for t in res.trades:
                formatted_trades.append({
                    "symbol": t.symbol,
                    "side": t.side.name,
                    "quantity": t.quantity,
                    "fill_price": t.fill_price,
                    "timestamp": t.timestamp,
                    "commission": t.commission,
                    "pnl": t.pnl
                })
            
            formatted_equity_curve = [
                [dt.isoformat(), val] for dt, val in res.equity_curve
            ]
            
            formatted_results[strat_name] = {
                "final_equity": res.final_equity,
                "total_return_pct": res.total_return_pct,
                "sharpe_ratio": res.sharpe_ratio,
                "max_drawdown_pct": res.max_drawdown_pct,
                "trades": formatted_trades,
                "equity_curve": formatted_equity_curve
            }
            
        return {"results": formatted_results}
    except Exception as e:
        logger.error(f"Backtest error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
