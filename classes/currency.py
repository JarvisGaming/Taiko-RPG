import copy
from enum import auto
from typing import TYPE_CHECKING, Optional

import aiosqlite
from classes.buff_effect import BuffEffect, BuffEffectType
from classes.extended_enum import ExtendedEnum
from classes.score import Score
from classes.upgrade import upgrade_manager
from other.global_constants import *

if TYPE_CHECKING:
    from classes.exp import ExpManager
    

class CurrencyID(ExtendedEnum):
    taiko_tokens = auto()


class Currency:
    currency_id: CurrencyID
    discord_emoji: str
    animated_discord_emoji: str
    
    def __init__(self, currency_id: CurrencyID, discord_emoji: str, animated_discord_emoji: str):
        self.currency_id = currency_id
        self.discord_emoji = discord_emoji
        self.animated_discord_emoji = animated_discord_emoji


class CurrencyManager:
    all_currencies: dict[str, Currency]
    initial_user_currency: dict[str, int]  # Before all score submissions
    current_user_currency: dict[str, int]  # Updated after each score submission
    user_upgrade_levels: dict[str, int]
    debug_log: list[str]
    
    def __init__(self, initial_user_currency: dict[str, int], user_upgrade_levels: dict[str, int]):
        from init.currency_init import init_currency
        self.all_currencies = init_currency()
        self.initial_user_currency = initial_user_currency
        self.current_user_currency = copy.deepcopy(self.initial_user_currency)  # Deep copy to prevent the two from pointing to the same dict
        self.user_upgrade_levels = user_upgrade_levels
        self.debug_log = []
    
    async def process_one_score(self, score: Score) -> dict[str, int]:
        """Calculate the currency gained from a score and update database accordingly. Returns the currency gained from the score for display purposes."""
        
        self.debug_log.clear()
        original_currency_gain = self.__calculate_currency_of_score_before_buffs(score)
        self.debug_log.append(f"original_currency_gain: {original_currency_gain}")
        new_currency_gain = self.__calculate_currency_of_score_after_buffs(score, original_currency_gain)
        self.debug_log.append(f"new_currency_gain: {new_currency_gain}")
        
        # Update database based on currency manager attributes
        self.__update_user_currency_locally(new_currency_gain)
        await self.__update_user_currency_in_database(score.user_osu_id)
        
        return new_currency_gain
    
    async def process_levelup_bonus(self, exp_manager: 'ExpManager', osu_id: int) -> Optional[dict[str, int]]:
        """Gives additional currency based on how many overall levels you gain."""
        
        currency_gain = {}
        
        if exp_manager.current_user_exp_bars["Overall"].level > exp_manager.initial_user_exp_bars["Overall"].level:
            currency_gain["taiko_tokens"] = 0
            
            # If you level up from 2 -> 4, then the bonus for level 3 and level 4 will be added
            for level in range(exp_manager.initial_user_exp_bars["Overall"].level + 1, exp_manager.current_user_exp_bars["Overall"].level + 1):
                
                # Currency gain is set at 10% of exp required to reach that level
                currency_gain["taiko_tokens"] += (level - 1) * 50 // 5
            
            self.__update_user_currency_locally(currency_gain)
            await self.__update_user_currency_in_database(osu_id)
            
        if currency_gain:
            return currency_gain
        return None
    
    def __calculate_currency_of_score_before_buffs(self, score: Score) -> dict[str, int]:
        original_currency_gain = {currency_name: 0 for currency_name in self.all_currencies.keys()}
        original_currency_gain['taiko_tokens'] = score.note_hits // NOTE_HITS_REQUIRED_PER_TAIKO_TOKEN
        return original_currency_gain

    def __calculate_currency_of_score_after_buffs(self, score: Score, original_currency_gain: dict[str, int]) -> dict[str, int]:
        new_currency_gain = copy.deepcopy(original_currency_gain)
        self.__apply_buff_effects_to_currency(score, new_currency_gain)
        return new_currency_gain
    
    def __apply_buff_effects_to_currency(self, score: Score, new_currency_gain: dict[str, int]):
        # Apply relevant upgrades in the correct order
        for upgrade in upgrade_manager.upgrades.values():
            for current_upgrade_priority in BuffEffectType.list():
                if upgrade.effect_type == current_upgrade_priority and upgrade.effect in [BuffEffect.TAIKO_TOKEN_GAIN]:
                    upgrade_level = self.user_upgrade_levels[upgrade.id]
                    upgrade_manager.apply_upgrade_effect(upgrade=upgrade, upgrade_level=upgrade_level, score=score, currency_gain=new_currency_gain)
                    self.debug_log.append(f"upgrade applied: {upgrade.name}")
                    self.debug_log.append(f"after upgrade applied: {new_currency_gain}")
    
    def __update_user_currency_locally(self, new_currency_gain: dict[str, int]):
        for currency_name in self.all_currencies.keys():
            self.current_user_currency[currency_name] += new_currency_gain[currency_name]
    
    async def __update_user_currency_in_database(self, osu_id: int):
        async with aiosqlite.connect("./data/database.db") as conn:
            for currency_name, amount_of_currency in self.current_user_currency.items():
                query = f"UPDATE currency SET {currency_name}=? WHERE osu_id=?"
                await conn.execute(query, (amount_of_currency, osu_id))
            await conn.commit()