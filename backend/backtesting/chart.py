import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.figure
import pandas as pd
from typing import Dict, Optional

from .results import BacktestResult

def plot_results(results: Dict[str, BacktestResult], filename: Optional[str] = 'backtest_result.png', show: bool = False) -> Optional[matplotlib.figure.Figure]:
    """
    Plots the equity curves and drawdown curves for multiple strategies on the same chart.
    Uses integer-based x-axis so weekends and holidays are skipped (no gaps).
    Saves to a file and optionally displays the plot. Returns the Figure object.
    """
    if not results:
        print("No results to plot.")
        return None

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})
    
    colors = ['blue', 'black', 'green', 'orange', 'purple', 'red']
    
    # We'll build one shared label list from the first valid result so the formatter
    # can map integer x positions back to date strings on both subplots.
    x_labels = None

    for i, (name, result) in enumerate(results.items()):
        if not result.equity_curve:
            continue
            
        color = colors[i % len(colors)]

        df = pd.DataFrame(result.equity_curve, columns=['timestamp', 'equity']).set_index('timestamp')

        # Use integer positions so the x-axis has no gaps for missing dates
        xs = range(len(df))

        if x_labels is None:
            x_labels = df.index.strftime('%Y-%m-%d').tolist()

        # --- Top Subplot: Equity Curve ---
        label = f"{name} (Ret: {result.total_return_pct:.1f}%, Sharpe: {result.sharpe_ratio:.2f})"
        ax1.plot(xs, df['equity'], label=label, color=color, linewidth=2, alpha=0.8)
        
        # --- Bottom Subplot: Drawdown Curve ---
        cumulative_max = df['equity'].cummax()
        drawdown_pct = ((df['equity'] - cumulative_max) / cumulative_max) * 100.0
        
        ax2.plot(xs, drawdown_pct.values, label=name, color=color, linewidth=1.5, alpha=0.7)
        ax2.fill_between(xs, drawdown_pct.values, 0, color=color, alpha=0.1)

    # Build the date formatter using the shared x_labels list
    if x_labels:
        def make_formatter(labels):
            def fmt(x, pos=None):
                idx = int(round(x))
                if 0 <= idx < len(labels):
                    return labels[idx]
                return ''
            return fmt

        date_formatter = ticker.FuncFormatter(make_formatter(x_labels))

        # Apply to both subplots, letting Matplotlib choose tick positions automatically
        for ax in (ax1, ax2):
            ax.xaxis.set_major_formatter(date_formatter)
            # Use ~8 evenly spaced ticks across the data range
            ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=8, integer=True))

    # --- Formatting Top Subplot ---
    ax1.set_title('Strategy Comparison: Equity Curve', fontsize=14)
    ax1.set_ylabel('Equity ($)')
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax1.legend(loc='upper left')
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=30, ha='right')

    # --- Formatting Bottom Subplot ---
    ax2.set_title('Strategy Comparison: Drawdown (%)', fontsize=12)
    ax2.set_ylabel('Drawdown (%)')
    ax2.grid(True, linestyle='--', alpha=0.7)
    ax2.legend(loc='lower left')
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30, ha='right')

    plt.tight_layout()

    if filename:
        fig.savefig(filename, dpi=300)
        print(f"Chart saved to {filename}")

    if show:
        plt.show()

    return fig
