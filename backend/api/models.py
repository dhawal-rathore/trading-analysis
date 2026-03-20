from dataclasses import dataclass
from typing import Any, List

@dataclass
class StrategyParamInfo:
    name: str
    type: str        # e.g. "int", "float"
    default: Any     # None if required
    required: bool

@dataclass
class StrategyInfo:
    name: str
    params: List[StrategyParamInfo]
    docstring: str
