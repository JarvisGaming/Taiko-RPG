from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from classes.buff_effect import BuffEffect, BuffEffectType


class Upgrade:
    id: str
    name: str
    description: str
    max_level: int
    cost_currency_unit: str
    cost: Callable[[int], int]  # lambda function that takes in a level, and returns the corresponding upgrade cost
    effect: "BuffEffect"  # What aspect the upgrade affects (eg Overall EXP, Taiko Token gain)
    effect_type: "BuffEffectType"  # Determines what order the upgrade should be applied in (eg additive -> mulplicative)
    effect_impl: Callable[..., None]  # Changes rewards according to the upgrade effect and description
    
    def __init__(self, id: str, name: str, description: str, max_level: int, cost_currency_unit: str, cost: Callable[[int], int], 
                 effect: "BuffEffect", effect_type: "BuffEffectType", effect_impl: Callable[..., None]):
        self.id = id
        self.name = name
        self.description = description
        self.max_level = max_level
        self.cost_currency_unit = cost_currency_unit
        self.cost = cost
        self.effect = effect
        self.effect_type = effect_type
        self.effect_impl = effect_impl