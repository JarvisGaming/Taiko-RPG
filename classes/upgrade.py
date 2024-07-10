from typing import Any, Callable


class Upgrade:
    name: str
    description: str
    max_level: int
    cost_currency_unit: str
    cost: Callable[[int], int]  # lambda function that takes in a level, and returns the corresponding upgrade cost
    effect: Callable[..., Any]
    
    def __init__(self, name: str, description: str, max_level: int, cost_currency_unit: str, cost: Callable[[int], int], effect: Callable[..., Any]):
        self.name = name
        self.description = description
        self.max_level = max_level
        self.cost_currency_unit = cost_currency_unit
        self.cost = cost
        self.effect = effect