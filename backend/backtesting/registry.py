import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Dict, List, Type

from backtesting.strategy import Strategy


class StrategyRegistry:
    """
    Auto-discovers and stores all available strategy classes from the backtesting.strategies package.
    """
    _registry: Dict[str, Type[Strategy]] = {}
    _is_loaded: bool = False

    @classmethod
    def load_all(cls, strategies_package="backtesting.strategies"):
        """
        Scans the given package and registers all subclasses of Strategy.
        """
        if cls._is_loaded:
            return

        # Find the absolute path to the strategies directory
        # Since this file (registry.py) is in backtesting/, the strategies package is in backtesting/strategies/
        package_path = Path(__file__).parent / "strategies"
        
        for finder, name, _ in pkgutil.iter_modules([str(package_path)]):
            module = importlib.import_module(f"{strategies_package}.{name}")
            
            # Inspect the module for classes that inherit from Strategy
            for attr_name, obj in inspect.getmembers(module, inspect.isclass):
                # Ensure it's a subclass of Strategy, but NOT the Strategy base class itself
                if issubclass(obj, Strategy) and obj is not Strategy:
                    # Also avoid registering Strategy subclasses from other modules that might just be imported
                    if obj.__module__.startswith(strategies_package):
                        cls._registry[attr_name] = obj
        
        cls._is_loaded = True

    @classmethod
    def get(cls, name: str) -> Type[Strategy]:
        """
        Returns the strategy class by name.
        """
        if not cls._is_loaded:
            cls.load_all()
            
        if name not in cls._registry:
            raise ValueError(f"Strategy '{name}' not found. Available strategies: {list(cls._registry.keys())}")
            
        return cls._registry[name]

    @classmethod
    def list_available(cls) -> List[str]:
        """
        Returns a list of all registered strategy names.
        """
        if not cls._is_loaded:
            cls.load_all()
            
        return list(cls._registry.keys())

    @classmethod
    def get_strategy_params(cls, name: str) -> dict:
        """
        Returns the constructor parameters for a strategy (excluding self, *args, **kwargs).
        Returns a dict of {param_name: inspect.Parameter}.
        """
        strategy_class = cls.get(name)
        sig = inspect.signature(strategy_class.__init__)
        
        params = {}
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue
            params[param_name] = param
            
        return params
