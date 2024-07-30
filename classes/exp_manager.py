import copy
import math
from typing import TYPE_CHECKING

import aiosqlite
from classes.buff_effect import BuffEffect, BuffEffectType
from classes.exp_bar_name import ExpBarName
from classes.score import Score
from classes.upgrade_manager import upgrade_manager
from other.global_constants import *

if TYPE_CHECKING:
    from classes.exp_bar import ExpBar
    

class ExpManager:
    initial_user_exp_bars: dict[str, "ExpBar"]  # Before all score submissions
    current_user_exp_bars: dict[str, "ExpBar"]  # Updated after each score submission
    user_upgrade_levels: dict[str, int]
    debug_log: list[str]
    
    def __init__(self, initial_user_exp_bars: dict[str, "ExpBar"], user_upgrade_levels: dict[str, int]):
        self.initial_user_exp_bars = initial_user_exp_bars
        self.current_user_exp_bars = copy.deepcopy(self.initial_user_exp_bars)  # Deep copy to prevent the two from pointing to the same dict
        self.user_upgrade_levels = user_upgrade_levels
        self.debug_log = []
    
    async def process_one_score(self, score: Score) -> dict[str, int]:
        """Calculate the exp gained from a score and update database accordingly. Returns the exp gained from the score for display purposes."""
        
        self.debug_log = []
        original_exp_bar_exp_gain = self.__calculate_exp_bar_exp_of_score_before_buffs(score)
        self.debug_log.append(f"original_exp_bar_exp_gain: {original_exp_bar_exp_gain}")
        new_exp_bar_exp_gain = self.__calculate_exp_bar_exp_of_score_after_buffs(score, original_exp_bar_exp_gain)
        self.debug_log.append(f"new_exp_bar_exp_gain: {new_exp_bar_exp_gain}")
        
        # Update database based on exp manager attributes
        self.__update_user_exp_bars_locally(new_exp_bar_exp_gain)
        await self.__update_user_exp_in_database(score)
        
        return new_exp_bar_exp_gain
    
    def __calculate_overall_exp_of_score_before_buffs(self, score: Score) -> int:
        """Calculates the overall exp that a score gives based on a formula."""
        
        original_overall_exp = math.pow(max(3*score.num_300s + 0.75*score.num_100s - 3*score.num_misses, 0), 0.6) * min(score.beatmap.sr+1, 11) * 0.07
        
        # Punish incomplete scores according to how much of the map was played
        if not score.is_complete_runthrough_of_map():
            original_overall_exp *= math.log(score.map_completion_progress()+1, 2)
        
        return int(original_overall_exp)
    
    def __calculate_exp_bar_exp_of_score_before_buffs(self, score: Score) -> dict[str, int]:
        original_exp_bar_exp = {exp_bar_name: 0 for exp_bar_name in ExpBarName.list_as_str()}
        original_exp_bar_exp['Overall'] = self.__calculate_overall_exp_of_score_before_buffs(score)
        
        self.split_overall_exp_among_exp_bars(score, original_exp_bar_exp)
        
        return original_exp_bar_exp

    def split_overall_exp_among_exp_bars(self, score: Score, exp_bar_exp_gain: dict[str, int]):
        number_of_exp_bar_mods_activated = score.count_number_of_exp_bar_mods_activated()
        
        # Allocate all EXP to NM if there are no exp bar mods activated
        if number_of_exp_bar_mods_activated == 0:
            exp_bar_exp_gain['NM'] = exp_bar_exp_gain['Overall']
        
        # Split the EXP evenly among activated exp bar mods otherwise
        else:
            for mod in score.mods:
                if mod.acronym in ExpBarName.list_as_str() + ['NC', 'DC']:
                    # NC and DC aren't exp bar names, but belong under DT and HT respectively
                    if mod.acronym == 'NC': mod_name = 'DT'
                    elif mod.acronym == 'DC': mod_name = 'HT'
                    else: mod_name = mod.acronym
                    
                    exp_bar_exp_gain[mod_name] = exp_bar_exp_gain['Overall'] // number_of_exp_bar_mods_activated
        
        # Lock all values as int
        for exp_bar_name in exp_bar_exp_gain.keys():
            exp_bar_exp_gain[exp_bar_name] = int(exp_bar_exp_gain[exp_bar_name])
    
    def __calculate_exp_bar_exp_of_score_after_buffs(self, score: Score, original_exp_bar_exp_gain: dict[str, int]) -> dict[str, int]:
        
        # Get overall exp after buffs
        new_exp_bar_exp_gain = {exp_bar_name: 0 for exp_bar_name in ExpBarName.list_as_str()}
        new_exp_bar_exp_gain['Overall'] = copy.deepcopy(original_exp_bar_exp_gain['Overall'])
        
        self.__apply_buff_effects_to_overall_exp(score, new_exp_bar_exp_gain)
        
        # Split it
        self.split_overall_exp_among_exp_bars(score, new_exp_bar_exp_gain)
        
        # get exp for each bar after upgrades
        self.__apply_upgrade_effects_to_exp_bar_exp(score, new_exp_bar_exp_gain)
        
        # Recalculate overall exp based on the sum of mod exp, since there are buffs that affect specific exp bars
        self.recaulcate_overall_exp_based_on_exp_bar_exp(new_exp_bar_exp_gain)
        
        return new_exp_bar_exp_gain
    
    def __apply_buff_effects_to_overall_exp(self, score: Score, new_exp_bar_exp_gain: dict[str, int]):
         
        # Apply relevant upgrades in the correct order
        for upgrade in upgrade_manager.upgrades.values():
            for current_upgrade_priority in BuffEffectType.list():
                if upgrade.effect_type == current_upgrade_priority and upgrade.effect == BuffEffect.OVERALL_EXP_GAIN:
                    upgrade_level = self.user_upgrade_levels[upgrade.id]
                    upgrade_manager.apply_upgrade_effect(upgrade=upgrade, upgrade_level=upgrade_level, score=score, exp_bar_exp_gain=new_exp_bar_exp_gain, user_exp_bars=self.current_user_exp_bars)
                    self.debug_log.append(f"upgrade applied: {upgrade.name}")
                    self.debug_log.append(f"after upgrade applied: {new_exp_bar_exp_gain}")

    def __apply_upgrade_effects_to_exp_bar_exp(self, score: Score, new_exp_bar_exp_gain: dict[str, int]):
        
        # Apply relevant upgrades in the correct order
        for upgrade in upgrade_manager.upgrades.values():
            for current_upgrade_priority in BuffEffectType.list():
                if upgrade.effect_type == current_upgrade_priority and upgrade.effect in [BuffEffect.NM_EXP_GAIN, BuffEffect.HD_EXP_GAIN, BuffEffect.HR_EXP_GAIN, BuffEffect.HR_EXP_GAIN, BuffEffect.DT_EXP_GAIN, BuffEffect.HT_EXP_GAIN]:
                    upgrade_level = self.user_upgrade_levels[upgrade.id]
                    upgrade_manager.apply_upgrade_effect(upgrade=upgrade, upgrade_level=upgrade_level, score=score, exp_bar_exp_gain=new_exp_bar_exp_gain, user_exp_bars=self.current_user_exp_bars)
                    self.debug_log.append(f"upgrade applied: {upgrade.name}")
                    self.debug_log.append(f"after upgrade applied: {new_exp_bar_exp_gain}")
    
    def recaulcate_overall_exp_based_on_exp_bar_exp(self, new_exp_bar_exp_gain: dict[str, int]):
        recalculated_overall_exp = 0
        for exp_bar_name, exp_bar_value in new_exp_bar_exp_gain.items():
            if exp_bar_name == 'Overall': 
                continue
            else:
                recalculated_overall_exp += exp_bar_value
        
        new_exp_bar_exp_gain['Overall'] = recalculated_overall_exp
    
    def __update_user_exp_bars_locally(self, new_exp_bar_exp_gain: dict[str, int]):
        for exp_bar_name, exp_gain in new_exp_bar_exp_gain.items():
            self.current_user_exp_bars[exp_bar_name].add_exp(exp_gain)
        
    async def __update_user_exp_in_database(self, score: Score):
        async with aiosqlite.connect("./data/database.db") as conn:
            for exp_bar_name, exp_bar in self.current_user_exp_bars.items():
                query = f"UPDATE exp_table SET {exp_bar_name.lower()}_exp=?, {exp_bar_name.lower()}_level=? WHERE osu_id=?"
                await conn.execute(query, (exp_bar.total_exp, exp_bar.level, score.user_osu_id))
            await conn.commit()