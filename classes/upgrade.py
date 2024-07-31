import inspect
from typing import TYPE_CHECKING, Callable, Optional

import aiosqlite
import discord
import other.utility
from classes.buff_effect import BuffEffect, BuffEffectType
from other.global_constants import NOTE_HITS_REQUIRED_PER_TAIKO_TOKEN

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
        
        # this should be moved to its own separate file in the future
        self.upgrades = {}
        
        def exp_length_bonus_effect(upgrade_level: int, score: "Score", exp_bar_exp_gain: dict[str, int]):
            if score.is_complete_runthrough_of_map():
                drain_time_minutes = score.beatmap.drain_time // 60
                exp_bar_exp_gain['Overall'] += (upgrade_level * drain_time_minutes)
        
        self.upgrades['exp_length_bonus'] = (Upgrade(
            id = "exp_length_bonus",
            name = "EXP Length Bonus", 
            description = "+1 EXP per minute of drain time per level (applies to maps you've fully completed)",
            max_level = 10, 
            cost_currency_unit = "taiko_tokens", 
            cost = lambda level: 50 * pow(level, 2),
            effect = BuffEffect.OVERALL_EXP_GAIN,
            effect_type = BuffEffectType.ADDITIVE,
            effect_impl = exp_length_bonus_effect,
        ))
        
        def overall_exp_gain_multiplier_effect(upgrade_level: int, exp_bar_exp_gain: dict[str, int]):
            exp_bar_exp_gain['Overall'] = int(exp_bar_exp_gain['Overall'] * (1 + 0.01 * upgrade_level))
        
        self.upgrades['overall_exp_gain_multiplier'] = (Upgrade(
            id = "overall_exp_gain_multiplier",
            name = "Overall EXP Gain Multiplier", 
            description = "+1% Overall EXP gain per level (additive)",
            max_level = 50,
            cost_currency_unit = "taiko_tokens", 
            cost = lambda level: 15*level,
            effect = BuffEffect.OVERALL_EXP_GAIN,
            effect_type = BuffEffectType.MULTIPLICATIVE,
            effect_impl = overall_exp_gain_multiplier_effect,
        ))
        
        def nm_exp_gain_multiplier_effect(upgrade_level: int, exp_bar_exp_gain: dict[str, int], user_exp_bars: dict[str, "ExpBar"]):
            exp_bar_exp_gain['NM'] = int (exp_bar_exp_gain['NM'] * (1 + 0.002 * upgrade_level * user_exp_bars['NM'].level))
        
        self.upgrades['nm_exp_gain_multiplier'] = (Upgrade(
            id = "nm_exp_gain_multiplier",
            name = "NM EXP Gain Multiplier", 
            description = "+0.2% NM EXP gain / NM level, per upgrade level (additive)",
            max_level = 5,
            cost_currency_unit = "taiko_tokens", 
            cost = lambda level: 200 * (level ** 2),
            effect = BuffEffect.NM_EXP_GAIN,
            effect_type = BuffEffectType.MULTIPLICATIVE,
            effect_impl = nm_exp_gain_multiplier_effect,
        ))
        
        def hd_exp_gain_multiplier_effect(upgrade_level: int, exp_bar_exp_gain: dict[str, int], user_exp_bars: dict[str, "ExpBar"]):
            exp_bar_exp_gain['HD'] = int (exp_bar_exp_gain['HD'] * (1 + 0.002 * upgrade_level * user_exp_bars['HD'].level))
        
        self.upgrades['hd_exp_gain_multiplier'] = (Upgrade(
            id = "hd_exp_gain_multiplier",
            name = "HD EXP Gain Multiplier", 
            description = "+0.2% HD EXP gain / HD level, per upgrade level (additive)",
            max_level = 5,
            cost_currency_unit = "taiko_tokens", 
            cost = lambda level: 200 * (level ** 2),
            effect = BuffEffect.HD_EXP_GAIN,
            effect_type = BuffEffectType.MULTIPLICATIVE,
            effect_impl = hd_exp_gain_multiplier_effect,
        ))
        
        def hr_exp_gain_multiplier_effect(upgrade_level: int, exp_bar_exp_gain: dict[str, int], user_exp_bars: dict[str, "ExpBar"]):
            exp_bar_exp_gain['HR'] = int (exp_bar_exp_gain['HR'] * (1 + 0.002 * upgrade_level * user_exp_bars['HR'].level))
        
        self.upgrades['hr_exp_gain_multiplier'] = (Upgrade(
            id = "hr_exp_gain_multiplier",
            name = "HR EXP Gain Multiplier", 
            description = "+0.2% HR EXP gain / HR level, per upgrade level (additive)",
            max_level = 5,
            cost_currency_unit = "taiko_tokens", 
            cost = lambda level: 200 * (level ** 2),
            effect = BuffEffect.HR_EXP_GAIN,
            effect_type = BuffEffectType.MULTIPLICATIVE,
            effect_impl = hr_exp_gain_multiplier_effect,
        ))
        
        def dt_exp_gain_multiplier_effect(upgrade_level: int, exp_bar_exp_gain: dict[str, int], user_exp_bars: dict[str, "ExpBar"]):
            exp_bar_exp_gain['DT'] = int (exp_bar_exp_gain['DT'] * (1 + 0.002 * upgrade_level * user_exp_bars['DT'].level))
        
        self.upgrades['dt_exp_gain_multiplier'] = (Upgrade(
            id = "dt_exp_gain_multiplier",
            name = "DT EXP Gain Multiplier", 
            description = "+0.2% DT EXP gain / DT level, per upgrade level (additive)",
            max_level = 5,
            cost_currency_unit = "taiko_tokens", 
            cost = lambda level: 200 * (level ** 2),
            effect = BuffEffect.DT_EXP_GAIN,
            effect_type = BuffEffectType.MULTIPLICATIVE,
            effect_impl = dt_exp_gain_multiplier_effect,
        ))
        
        def ht_exp_gain_multiplier_effect(upgrade_level: int, exp_bar_exp_gain: dict[str, int], user_exp_bars: dict[str, "ExpBar"]):
            exp_bar_exp_gain['HT'] = int (exp_bar_exp_gain['HT'] * (1 + 0.002 * upgrade_level * user_exp_bars['HT'].level))
        
        self.upgrades['ht_exp_gain_multiplier'] = (Upgrade(
            id = "ht_exp_gain_multiplier",
            name = "HT EXP Gain Multiplier", 
            description = "+0.2% HT EXP gain / HT level, per upgrade level (additive)",
            max_level = 5,
            cost_currency_unit = "taiko_tokens", 
            cost = lambda level: 200 * (level ** 2),
            effect = BuffEffect.HT_EXP_GAIN,
            effect_type = BuffEffectType.MULTIPLICATIVE,
            effect_impl = ht_exp_gain_multiplier_effect,
        ))
    
        def tt_gain_efficiency_effect(upgrade_level: int, score: "Score", currency_gain: dict[str, int]):
            currency_gain['taiko_tokens'] = score.note_hits // (NOTE_HITS_REQUIRED_PER_TAIKO_TOKEN - upgrade_level)
    
        self.upgrades['tt_gain_efficiency'] = (Upgrade(
            id = "tt_gain_efficiency",
            name = "Taiko Token Gain Efficiency",
            description = f"-1 note hit needed to gain a Taiko Token. You gain a token every {NOTE_HITS_REQUIRED_PER_TAIKO_TOKEN} hits by default",
            max_level = 20,
            cost_currency_unit = "taiko_tokens", 
            cost = lambda level: int(10 * pow(1.39, level-1)),
            effect = BuffEffect.TAIKO_TOKEN_GAIN,
            effect_type = BuffEffectType.ADDITIVE,
            effect_impl = tt_gain_efficiency_effect,
        ))
        
        def tt_gain_multiplier_effect(upgrade_level: int, currency_gain: dict[str, int]):
            currency_gain['taiko_tokens'] = int(currency_gain['taiko_tokens'] * (1 + 0.02 * upgrade_level))
        
        self.upgrades['tt_gain_multiplier'] = (Upgrade(
            id = "tt_gain_multiplier",
            name = "Taiko Token Gain Multiplier", 
            description = "+2% Taiko Token gain per level (additive)",
            max_level = 50,
            cost_currency_unit = "taiko_tokens", 
            cost = lambda level: int(25 * pow(1.1, level-1)),
            effect = BuffEffect.TAIKO_TOKEN_GAIN,
            effect_type = BuffEffectType.MULTIPLICATIVE,
            effect_impl = tt_gain_multiplier_effect,
        ))
    
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