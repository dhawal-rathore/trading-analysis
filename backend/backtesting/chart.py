import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.figure
import pandas as pd
from typing import Dict, Optional

from .results import BacktestResult

def plot_results(results: Dict[str, BacktestResult], filename: Optional[str] = 'backtest_result.png', show: bool = False) -> Optional[matplotlib.figure.Figure]:
    """
    Plots the equity curves and drawdown curves for multiple strategies on the same chart.
    Saves to a file and optionally displays the plot. Returns the Figure object.
    """
    if not results:
        print("No results to plot.")
        return None

    # Create figure with 2 subplots (Equity Curve and Drawdown Curve)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})
    
    # Colors for different strategies
    colors = ['blue', 'black', 'green', 'orange', 'purple', 'red']
    
    for i, (name, result) in enumerate(results.items()):
        if not result.equity_curve:
            continue
            
        color = colors[i % len(colors)]

        # Convert to dataframe for easier plotting
        df = pd.DataFrame(result.equity_curve, columns=['timestamp', 'equity']).set_index('timestamp')

        # --- Top Subplot: Equity Curve ---
        label = f"{name} (Ret: {result.total_return_pct:.1f}%, Sharpe: {result.sharpe_ratio:.2f})"
        ax1.plot(df.index, df['equity'], label=label, color=color, linewidth=2, alpha=0.8)
        
        # --- Bottom Subplot: Drawdown Curve ---
        # Calculate Drawdown
        cumulative_max = df['equity'].cummax()
        drawdown_pct = ((df['equity'] - cumulative_max) / cumulative_max) * 100.0
        
        ax2.plot(drawdown_pct.index, drawdown_pct.values, label=name, color=color, linewidth=1.5, alpha=0.7)
        ax2.fill_between(drawdown_pct.index, drawdown_pct.values, 0, color=color, alpha=0.1)

    # --- Formatting Top Subplot ---
    ax1.set_title('Strategy Comparison: Equity Curve', fontsize=14)
    ax1.set_ylabel('Equity ($)')
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax1.legend(loc='upper left')
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))

    # --- Formatting Bottom Subplot ---
    ax2.set_title('Strategy Comparison: Drawdown (%)', fontsize=12)
    ax2.set_ylabel('Drawdown (%)')
    ax2.grid(True, linestyle='--', alpha=0.7)
    ax2.legend(loc='lower left')
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=0)

    # Layout adjustments
    plt.tight_layout()

    if filename:
        fig.savefig(filename, dpi=300)
        print(f"Chart saved to {filename}")

    if show:
        plt.show()
    
    # Do not call plt.close() if we want the user to be able to use the returned figure.
    # The caller can manage the figure lifecycle.
    
    return fig
