import copy

import aiosqlite
from classes.buff_effect import BuffEffect, BuffEffectType
from classes.currency import Currency, get_all_currencies
from classes.score import Score
from other.global_constants import *

NOTE_HITS_REQUIRED_PER_TAIKO_TOKEN: int = 50  # fix later

class CurrencyManager:
    initial_user_currency: dict[str, int]  # Before all score submissions
    current_user_currency: dict[str, int]  # Updated after each score submission
    user_upgrade_levels: dict[str, int]
    debug_log: list[str]
    
    def __init__(self, initial_user_currency: dict[str, int], user_upgrade_levels: dict[str, int]):
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
        await self.__update_user_currency_in_database(score)
        
        return new_currency_gain
    
    def __calculate_currency_of_score_before_buffs(self, score: Score) -> dict[str, int]:
        original_currency_gain = {currency_name: 0 for currency_name in ALL_CURRENCIES.keys()}
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
        for currency_name in ALL_CURRENCIES.keys():
            self.current_user_currency[currency_name] += new_currency_gain[currency_name]
    
    async def __update_user_currency_in_database(self, score: Score):
        async with aiosqlite.connect("./data/database.db") as conn:
            for currency_name, amount_of_currency in self.current_user_currency.items():
                query = f"UPDATE currency SET {currency_name}=? WHERE osu_id=?"
                await conn.execute(query, (amount_of_currency, score.user_osu_id))
            await conn.commit()