import datetime
import math
from dataclasses import dataclass
from typing import List, Tuple
import pandas as pd

from .models import Trade

@dataclass
class BacktestResult:
    initial_capital: float
    final_equity: float
    total_return_pct: float
    equity_curve: List[Tuple[datetime.datetime, float]]
    trades: List[Trade]
    sharpe_ratio: float
    max_drawdown_pct: float

def calculate_metrics(initial_capital: float, equity_curve: List[Tuple[datetime.datetime, float]], trades: List[Trade]) -> BacktestResult:
    """
    Computes Sharpe Ratio, Max Drawdown, and formats the BacktestResult.
    """
    if not equity_curve:
        return BacktestResult(initial_capital, initial_capital, 0.0, [], trades, 0.0, 0.0)

    final_equity = equity_curve[-1][1]
    total_return_pct = ((final_equity / initial_capital) - 1.0) * 100.0

    # Convert equity curve to pandas Series for vectorized metric calculation
    df = pd.DataFrame(equity_curve, columns=['timestamp', 'equity']).set_index('timestamp')
    
    # Calculate daily returns for Sharpe Ratio
    # We resample to daily in case data is intraday
    daily_equity = df['equity'].resample('D').last().dropna()
    daily_returns = daily_equity.pct_change().dropna()
    
    # Annualized Sharpe Ratio (assuming risk-free rate = 0 for simplicity)
    # Approx 252 trading days in a year
    if len(daily_returns) > 1 and daily_returns.std() != 0:
        sharpe_ratio = math.sqrt(252) * (daily_returns.mean() / daily_returns.std())
    else:
        sharpe_ratio = 0.0

    # Max Drawdown
    cumulative_max = df['equity'].cummax()
    drawdowns = (df['equity'] - cumulative_max) / cumulative_max
    max_drawdown_pct = abs(drawdowns.min() * 100.0) if len(drawdowns) > 0 else 0.0

    return BacktestResult(
        initial_capital=initial_capital,
        final_equity=final_equity,
        total_return_pct=total_return_pct,
        equity_curve=equity_curve,
        trades=trades,
        sharpe_ratio=sharpe_ratio,
        max_drawdown_pct=max_drawdown_pct
    )
