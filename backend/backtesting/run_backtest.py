import argparse
import datetime
import logging
import sys
import re

from api import BacktestAPI
from backtesting.chart import plot_results

# Set up logging to see engine output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def print_available_strategies():
    print("\nAvailable Strategies:")
    for name in BacktestAPI.list_strategies():
        info = BacktestAPI.get_strategy_info(name)
        if info.params:
            param_strs = [f"{p.name}: {p.type}={p.default}" for p in info.params]
            print(f"  {name:<20} ({', '.join(param_strs)})")
        else:
            print(f"  {name:<20} (no parameters)")
    print("\nBenchmark Strategy:")
    print(f"  {'BuyAndHoldStrategy':<20} (Always included for comparison)")
    print()

def build_chart_filename(results: dict, symbol: str, timeframe: str) -> str:
    """Builds a sanitized filename like backtest_RSIStrategy_vs_Buy_and_Hold_SPY_1day.png"""
    names = list(results.keys())
    if not names:
        return f"backtest_comparison_{symbol}_{timeframe}.png"
        
    # Sanitize each name: replace unsafe chars and spaces with underscore
    sanitized_names = []
    for name in names:
        # replace any char that is not word, digit, or hyphen with underscore
        clean = re.sub(r'[^\w\-]', '_', name)
        # merge multiple underscores into one
        clean = re.sub(r'_+', '_', clean)
        # strip leading/trailing underscores
        clean = clean.strip('_')
        sanitized_names.append(clean)
        
    joined_names = "_vs_".join(sanitized_names)
    return f"backtest_{joined_names}_{symbol}_{timeframe}.png"

def main():
    # Pre-parse just the top-level arguments to intercept --list-strategies or extract the chosen strategy
    parser = argparse.ArgumentParser(description="Run Backtest Comparison", add_help=False)
    parser.add_argument("--list-strategies", action="store_true", help="List all available strategies and their arguments")
    parser.add_argument("--strategy", type=str, default="RSIStrategy", help="The strategy class to run")
    
    # We parse known args so we don't fail on strategy-specific arguments yet
    known_args, remaining_args = parser.parse_known_args()

    if known_args.list_strategies:
        print_available_strategies()
        sys.exit(0)

    # Now create the full parser
    full_parser = argparse.ArgumentParser(description="Run Backtest Comparison")
    full_parser.add_argument("--strategy", type=str, default="RSIStrategy", help="The strategy class to run")
    full_parser.add_argument("--symbol", type=str, default="SPY", help="Ticker symbol (e.g. SPY)")
    full_parser.add_argument("--timeframe", type=str, default="1day", help="Timeframe (e.g. 1day, 1hr)")
    full_parser.add_argument("--start", type=str, default="2020-01-01", help="Start date YYYY-MM-DD")
    full_parser.add_argument("--end", type=str, default="2023-01-01", help="End date YYYY-MM-DD")
    full_parser.add_argument("--lookback", type=int, default=50, help="Number of historical bars to pass to strategy per tick")
    full_parser.add_argument("--no-fetch", action="store_true", help="Disable auto-fetching missing data")
    full_parser.add_argument("--aux", type=str, nargs='*', help="Auxiliary series to load as 'SYMBOL:TIMEFRAME', e.g. 'SPY:1min' 'QQQ:1hr'")

    # Add dynamically discovered arguments for the chosen strategy
    try:
        strat_info = BacktestAPI.get_strategy_info(known_args.strategy)
        
        if strat_info.params:
            strat_group = full_parser.add_argument_group(f"'{known_args.strategy}' parameters")
            for param in strat_info.params:
                # Builtins mappings for argparse types
                type_map = {"int": int, "float": float, "str": str, "bool": bool}
                arg_type = type_map.get(param.type, str)
                
                # If no default is provided, make it required
                if param.required:
                    strat_group.add_argument(f"--{param.name}", type=arg_type, required=True)
                else:
                    strat_group.add_argument(f"--{param.name}", type=arg_type, default=param.default)
    except ValueError as e:
        logging.error(e)
        sys.exit(1)

    args = full_parser.parse_args()

    # Build kwargs for strategy constructor
    strat_kwargs = {}
    for param in strat_info.params:
        strat_kwargs[param.name] = getattr(args, param.name)

    try:
        strat = BacktestAPI.build_strategy(args.strategy, **strat_kwargs)
    except Exception as e:
        logging.error(f"Failed to build strategy: {e}")
        sys.exit(1)

    # Initialize Strategies
    strategies = {
        args.strategy: strat
    }

    # Parse aux series
    auxiliary_series = []
    if args.aux:
        for aux_str in args.aux:
            parts = aux_str.split(':')
            if len(parts) == 2:
                auxiliary_series.append((parts[0], parts[1]))
            else:
                logging.warning(f"Ignoring invalid aux format '{aux_str}', expected SYMBOL:TIMEFRAME")

    # Run
    try:
        results = BacktestAPI.run(
            symbol=args.symbol,
            timeframe=args.timeframe,
            start=args.start,
            end=args.end,
            strategies=strategies,
            initial_capital=10000.0,
            lookback=args.lookback,
            commission_pct=0.001, # 0.1% fee
            flat_commission=0.0,
            auto_fetch=not args.no_fetch,
            include_benchmark=True,
            auxiliary_series=auxiliary_series
        )
        
        # Print Summary Table
        print("\n" + "="*85)
        print(f"{'Strategy':<15} | {'Final Equity':<15} | {'Return %':<10} | {'Max DD %':<10} | {'Sharpe':<8} | {'Trades':<6}")
        print("-" * 85)
        
        for name, res in results.items():
            print(f"{name:<15} | ${res.final_equity:<14.2f} | {res.total_return_pct:<9.2f}% | {res.max_drawdown_pct:<9.2f}% | {res.sharpe_ratio:<8.2f} | {len(res.trades):<6}")
            
        print("="*85 + "\n")

        # Plot
        chart_filename = build_chart_filename(results, args.symbol, args.timeframe)
        fig = plot_results(results, filename=chart_filename, show=False)
        
    except Exception as e:
        logging.error(f"Backtest failed: {e}")

if __name__ == "__main__":
    main()
