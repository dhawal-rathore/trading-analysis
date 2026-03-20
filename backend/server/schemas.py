from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import datetime

class RunBacktestRequest(BaseModel):
    symbol: str = "SPY"
    timeframe: str = "1day"
    start: str = "2022-01-01"
    end: str = "2023-01-01"
    strategy: str
    strategy_params: Dict[str, Any] = {}
    initial_capital: float = 10000.0
    lookback: int = 50
    commission_pct: float = 0.001
    auto_fetch: bool = True
    include_benchmark: bool = True

class StrategyParamSchema(BaseModel):
    name: str
    type: str
    default: Any
    required: bool

class StrategyInfoSchema(BaseModel):
    name: str
    params: List[StrategyParamSchema]
    docstring: str

class TradeSchema(BaseModel):
    symbol: str
    side: str
    quantity: float
    fill_price: float
    timestamp: datetime.datetime
    commission: float
    pnl: float

class BacktestResultSchema(BaseModel):
    final_equity: float
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    trades: List[TradeSchema]
    equity_curve: List[List[Any]] # [datetime string, equity]

class RunBacktestResponse(BaseModel):
    results: Dict[str, BacktestResultSchema]
