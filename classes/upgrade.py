import inspect
from typing import TYPE_CHECKING, Callable, Optional

import aiosqlite
import discord
import other.utility

if TYPE_CHECKING:
    from classes.buff_effect import BuffEffect, BuffEffectType
    from classes.exp import ExpBar
    from classes.score import Score
    

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
        

class UpgradeManager:

    upgrades: dict[str, Upgrade]  # upgrade_id: upgrade
    # and then in the future we can have other buff related stuff here

    def __init__(self):
        from init.upgrade_init import init_upgrades
        self.upgrades = init_upgrades()
    
    def get_upgrade(self, upgrade_id: str) -> Optional[Upgrade]:
        return self.upgrades.get(upgrade_id, None)
    
    def apply_upgrade_effect(self, upgrade: Upgrade, upgrade_level: int, score: "Score", user_exp_bars: Optional[dict[str, "ExpBar"]] = None, 
                             exp_bar_exp_gain: Optional[dict[str, int]] = None, currency_gain: Optional[dict[str, int]] = None):
        """Applies an upgrade effect given some upgrade, its level, and the things that it affects."""
        
        # Determine the parameters needed to be passed as a tuple
        parameters_needed = inspect.getfullargspec(upgrade.effect_impl).args

        # Add the necessary parameters as a dict
        parameters_to_be_passed = {}
        
        for parameter in parameters_needed:
            
            # self is not a parameter you need to pass in
            if parameter == 'self':
                continue
            
            elif parameter == 'upgrade_level':
                parameters_to_be_passed[parameter] = upgrade_level
            
            elif parameter =='score':
                parameters_to_be_passed[parameter] = score
            
            elif parameter == 'user_exp_bars':
                parameters_to_be_passed[parameter] = user_exp_bars
                
            elif parameter == 'exp_bar_exp_gain':
                parameters_to_be_passed[parameter] = exp_bar_exp_gain
                
            elif parameter == 'currency_gain':
                parameters_to_be_passed[parameter] = currency_gain
                
        # Unpack dict and pass it in
        upgrade.effect_impl(**parameters_to_be_passed)

    async def process_upgrade_purchase(self, interaction: discord.Interaction, upgrade_id: str, times_to_purchase: int):
        await interaction.response.send_message(f"Processing upgrade purchase...")
        
        upgrade = self.get_upgrade(upgrade_id)
        assert upgrade is not None
        upgrade_levels_purchased = 0
        
        for _ in range(times_to_purchase):
            user_currency = await other.utility.get_user_currency(discord_id=interaction.user.id)
            user_upgrade_levels = await other.utility.get_user_upgrade_levels(discord_id=interaction.user.id)
            
            current_upgrade_level = user_upgrade_levels[upgrade_id]
            upgrade_cost = upgrade.cost(user_upgrade_levels[upgrade_id]+1)
            
            if current_upgrade_level >= upgrade.max_level:
                if upgrade_levels_purchased == 0:
                    await interaction.followup.send(f"You already maxed out {upgrade.name}!")
                break
            
            if not await self.__user_has_enough_currency(upgrade, user_currency, upgrade_cost):
                if upgrade_levels_purchased == 0:
                    await interaction.followup.send(f"You don't have enough currency to purchase {upgrade.name} (Level {current_upgrade_level+1})!")
                break
            
            await self.__update_database_from_purchase(interaction, upgrade_id, upgrade, user_currency, current_upgrade_level, upgrade_cost)
            upgrade_levels_purchased += 1
            
        if upgrade_levels_purchased != 0:
            await interaction.followup.send(f"Purchased {upgrade_levels_purchased} level(s) of {upgrade.name}!")

    async def __update_database_from_purchase(self, interaction: discord.Interaction, upgrade_id: str, upgrade: Upgrade, 
                                            user_currency: dict[str, int], current_upgrade_level: int, upgrade_cost: int):
        osu_id = await other.utility.get_osu_id(discord_id=interaction.user.id)
        async with aiosqlite.connect("./data/database.db") as conn:
            # deduct currency
            new_currency_amount = user_currency[upgrade.cost_currency_unit] - upgrade_cost
            await conn.execute(F"UPDATE currency SET {upgrade.cost_currency_unit}=? WHERE osu_id=?", (new_currency_amount, osu_id))
                
            # add level
            new_level = current_upgrade_level + 1
            await conn.execute(F"UPDATE upgrades SET {upgrade_id}=? WHERE osu_id=?", (new_level, osu_id))
                
            await conn.commit()
        
    async def __user_has_enough_currency(self, upgrade: Upgrade, user_currency: dict[str, int], upgrade_cost: int):
        if upgrade_cost > user_currency[upgrade.cost_currency_unit]:
            return False
        return True

upgrade_manager = UpgradeManager()