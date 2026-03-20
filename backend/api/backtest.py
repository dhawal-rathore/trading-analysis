import datetime
import inspect
import logging
from typing import Dict, List, Optional, Type, Union

from api.models import StrategyInfo, StrategyParamInfo

from backtesting.registry import StrategyRegistry
from backtesting.strategy import Strategy
from backtesting.engine import BacktestEngine
from backtesting.results import BacktestResult
from backtesting.strategies.baseline import BuyAndHoldStrategy

from db.manager import OHLCVManager
from ingestion.engine import IngestionEngine
from ingestion.yfinance_provider import YFinanceIngester

logger = logging.getLogger(__name__)

class BacktestAPI:

    @staticmethod
    def list_strategies() -> List[str]:
        """Return names of all auto-discovered Strategy subclasses."""
        StrategyRegistry.load_all()
        return StrategyRegistry.list_available()

    @staticmethod
    def get_strategy_info(name: str) -> StrategyInfo:
        """Return typed parameter metadata for a strategy."""
        StrategyRegistry.load_all()
        strat_class = StrategyRegistry.get(name)
        
        docstring = inspect.getdoc(strat_class) or ""
        params_info = []
        
        # Get strategy parameters
        params = StrategyRegistry.get_strategy_params(name)
        for param_name, param in params.items():
            arg_type = param.annotation.__name__ if hasattr(param.annotation, '__name__') else str(param.annotation)
            
            is_required = param.default == inspect.Parameter.empty
            default_val = None if is_required else param.default
            
            params_info.append(StrategyParamInfo(
                name=param_name,
                type=arg_type,
                default=default_val,
                required=is_required
            ))
            
        return StrategyInfo(name=name, params=params_info, docstring=docstring)

    @staticmethod
    def build_strategy(name: str, **kwargs) -> Strategy:
        """Instantiate a strategy by name with typed kwargs."""
        StrategyRegistry.load_all()
        strat_class = StrategyRegistry.get(name)
        return strat_class(**kwargs)

    @staticmethod
    def run(
        symbol: str,
        timeframe: str,
        start: Union[str, datetime.datetime],
        end: Union[str, datetime.datetime],
        strategies: Dict[str, Strategy],
        initial_capital: float = 10000.0,
        lookback: int = 50,
        commission_pct: float = 0.001,
        flat_commission: float = 0.0,
        auto_fetch: bool = True,
        include_benchmark: bool = True,
    ) -> Dict[str, BacktestResult]:
        """
        Run a full backtest. Handles DB connection, optional ingestion,
        and engine execution. Returns raw results - no side effects.
        Dates can be "YYYY-MM-DD" strings or aware datetime objects.
        """
        # Parse dates if they are strings
        if isinstance(start, str):
            start = datetime.datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
        if isinstance(end, str):
            end = datetime.datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)

        db_manager = OHLCVManager()
        
        # Auto-fetch data if needed
        if auto_fetch:
            logger.info(f"Ensuring data for {symbol} is available in the database from {start.date()} to {end.date()}...")
            provider = YFinanceIngester()
            ingestion_engine = IngestionEngine(db_manager, provider)
            ingestion_engine.ingest(symbol, timeframe, start, end)

        # Check if we have data
        db_range = db_manager.get_data_range(symbol, timeframe)
        if not db_range:
            raise ValueError(f"No data found for {symbol} {timeframe} in the database.")
            
        # Verify the requested range is at least partially covered
        if db_range[0] > end or db_range[1] < start:
            raise ValueError(f"Data in DB ({db_range[0].date()} to {db_range[1].date()}) does not overlap with requested range ({start.date()} to {end.date()}).")
            
        logger.info(f"Database contains {symbol} data from {db_range[0]} to {db_range[1]}")

        # Setup strategies
        run_strategies = strategies.copy()
        if include_benchmark and "Buy & Hold" not in run_strategies:
            run_strategies["Buy & Hold"] = BuyAndHoldStrategy()

        # Initialize and run engine
        engine = BacktestEngine(
            strategies=run_strategies,
            db_manager=db_manager,
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
            initial_capital=initial_capital,
            lookback=lookback, 
            commission_pct=commission_pct,
            flat_commission=flat_commission
        )

        return engine.run()
