import copy
import datetime
import math
from typing import Any

import aiosqlite
import dateutil.parser
import other.utility
from classes.beatmap import Beatmap
from classes.beatmapset import Beatmapset
from classes.mod import Mod
from other.global_constants import *


class Score:
    "Class representing an osu score. Contains information about the score itself, exp gained from the score, and beatmap and beatmapset information."
    
    username: str
    user_osu_id: int
    user_discord_id: int
    
    score_id: int
    score_url: str
    
    num_300s: int
    num_100s: int
    num_misses: int
    accuracy: float
    rank: str
    mods: list[Mod]
    mods_human_readable: str
    timestamp: datetime.datetime
    
    total_score: int  # Lazer score_info, so stable scores are scored w/ classic mod (vs legacy_total_score)
    max_combo: int  # In the score, not the map
    pp: float | None
    has_replay: bool
    is_FC: bool
    is_pass: bool
    is_convert: bool
    
    beatmap: Beatmap
    beatmapset: Beatmapset
    
    base_exp_gained: int
    base_currency_gained: dict[str, int]  # Keys: Currency names, Values: Amount of currency gained
    exp_gained_after_upgrades: dict[str, int]  # Keys: EXP bar names, Values: Amount of exp gained
    currency_gained_after_upgrades: dict[str, int]  # Keys: Currency names, Values: Amount of currency gained
    
    @classmethod
    async def create_score_object(cls, score_info: dict[str, Any], user_upgrades: dict[str, int]):
        self = cls()
        self.username = score_info['user']['username']
        self.user_osu_id = score_info['user']['id']
        await self.__init_user_discord_id()
        
        self.score_id = score_info['id']
        self.score_url = f"https://osu.ppy.sh/scores/{self.score_id}"
        
        self.num_300s = score_info['statistics'].get('great', 0)  # Field is ommitted when fetching from API if there are no 300s
        self.num_100s = score_info['statistics'].get('ok', 0)  # Field is ommitted when fetching from API if there are no 100s
        self.num_misses = score_info['statistics'].get('miss', 0)  # Field is ommitted when fetching from API if there are no misses
        self.accuracy = score_info['accuracy'] * 100  # Convert from 0.99 to 99 for example, since it's more intuitive
        self.rank = score_info['rank']
        self.mods = [Mod(mod_info) for mod_info in score_info['mods']]
        self.__init_human_readable_mod_listing()
        self.timestamp = dateutil.parser.parse(score_info['ended_at'])  # Converts ISO 8601 format timestamp to datetime object
        
        self.total_score = score_info['total_score']
        self.max_combo = score_info['max_combo']
        self.pp = score_info['pp']
        self.has_replay = score_info['has_replay']
        self.is_FC = score_info['is_perfect_combo']
        self.is_pass = score_info['passed']
        self.is_convert = score_info['beatmap']['convert']
        
        self.beatmap = Beatmap(score_info['beatmap'], await self.__get_sr_after_mods(score_info), self)
        self.beatmapset = Beatmapset(score_info['beatmapset'])
        
        self.__init_base_exp_gained()
        await self.__init_exp_gained_after_upgrades(user_upgrades)
        self.__init_base_currency_gained()
        await self.__init_currency_gained_after_upgrades(user_upgrades)
        
        return self
    
    async def __init_user_discord_id(self):
        discord_id = await other.utility.get_discord_id(osu_id=self.user_osu_id)
        assert discord_id is not None  # You can't send a score without being verified
        self.user_discord_id = discord_id
    
    def __init_human_readable_mod_listing(self):
        """Create a human-readable listing of the mods used in the score."""
        
        mods_human_readable = ""
        for mod in self.mods:
            mods_human_readable += mod.acronym + " "
        self.mods_human_readable = mods_human_readable.strip()  # Remove trailing whitespace
    
    def __init_base_exp_gained(self):

        total_exp_gained = math.pow(max(3*self.num_300s + 0.75*self.num_100s - 3*self.num_misses, 0), 0.6) * min(self.beatmap.sr+1, 11) * 0.07
        
        # Punish incomplete scores according to how much of the map was played
        if not self.is_complete_runthrough_of_map():
            total_exp_gained *= math.log(self.map_completion_progress()+1, 2)
        
        self.base_exp_gained = int(total_exp_gained)

    async def __init_exp_gained_after_upgrades(self, user_upgrades: dict[str, int]):
        self.exp_gained_after_upgrades = {exp_bar_name: 0 for exp_bar_name in EXP_BAR_NAMES}
        self.exp_gained_after_upgrades['Overall'] = self.base_exp_gained
        
        self.__apply_upgrade_effect_on_exp_gain(user_upgrades)
        
        number_of_exp_bar_mods_activated = self.__count_number_of_exp_bar_mods_activated()
        if number_of_exp_bar_mods_activated == 0:
            self.exp_gained_after_upgrades['NM'] = self.exp_gained_after_upgrades['Overall']
        
        else:
            for mod in self.mods:
                if mod.acronym in EXP_BAR_NAMES + ['NC', 'DC']:
                    
                    # NC and DC aren't exp bar names, but belong under DT and HT respectively
                    if mod.acronym == 'NC': mod_name = 'DT'
                    elif mod.acronym == 'DC': mod_name = 'HT'
                    else: mod_name = mod.acronym
                    
                    self.exp_gained_after_upgrades[mod_name] = self.exp_gained_after_upgrades['Overall'] // number_of_exp_bar_mods_activated
        
        # Lock all values as int
        for exp_bar_name in self.exp_gained_after_upgrades.keys():
            self.exp_gained_after_upgrades[exp_bar_name] = int(self.exp_gained_after_upgrades[exp_bar_name])

    def __apply_upgrade_effect_on_exp_gain(self, user_upgrades):
        if self.is_complete_runthrough_of_map():
            exp_length_bonus_effect = upgrade_manager.upgrades['exp_length_bonus'].effect(user_upgrades['exp_length_bonus'], self.beatmap.drain_time // 60)
            self.exp_gained_after_upgrades['Overall'] += exp_length_bonus_effect
        exp_gain_multiplier_effect = upgrade_manager.upgrades['exp_gain_multiplier'].effect(user_upgrades['exp_gain_multiplier'])
        self.exp_gained_after_upgrades['Overall'] *= exp_gain_multiplier_effect

    def __init_base_currency_gained(self):
        self.base_currency_gained = {}
        self.base_currency_gained['taiko_tokens'] = (self.num_300s + self.num_100s) // NOTE_HITS_REQUIRED_PER_TAIKO_TOKEN

    async def __init_currency_gained_after_upgrades(self, user_upgrades: dict[str, int]):
        # Copy everything over, rewrite if necessary if some upgrades affect how the currency itself is acquired
        self.currency_gained_after_upgrades = copy.deepcopy(self.base_currency_gained)
        
        self.__apply_upgrade_effect_on_currency_gain(user_upgrades)
        
        # Lock all values as int
        for currency_name in self.currency_gained_after_upgrades.keys():
            self.currency_gained_after_upgrades[currency_name] = int(self.currency_gained_after_upgrades[currency_name])

    def __apply_upgrade_effect_on_currency_gain(self, user_upgrades):
        note_hit_reduction_per_taiko_token = upgrade_manager.upgrades['tt_gain_efficiency'].effect(user_upgrades['tt_gain_efficiency'])
        self.currency_gained_after_upgrades['taiko_tokens'] = (self.num_300s + self.num_100s) // (NOTE_HITS_REQUIRED_PER_TAIKO_TOKEN - note_hit_reduction_per_taiko_token)
        self.currency_gained_after_upgrades['taiko_tokens'] *= upgrade_manager.upgrades['tt_gain_multiplier'].effect(user_upgrades['tt_gain_multiplier'])
        
    def __count_number_of_exp_bar_mods_activated(self) -> int:
        number_of_exp_bar_mods_activated = 0
        
        for mod in self.mods:
            
            # There is no mod with the name "Overall" or "NM"
            if mod.acronym in EXP_BAR_NAMES + ['NC', 'DC']:
                number_of_exp_bar_mods_activated += 1
                
        return number_of_exp_bar_mods_activated
    
    async def __get_sr_after_mods(self, score_info: dict[str, Any]) -> float:
        headers = {
            'Accept': "application/json",
            'Content-Type': "application/json",
            'Authorization': f"Bearer {os.getenv('OSU_API_ACCESS_TOKEN')}"
        }
        
        params = {
            'ruleset': "taiko"
        }
        
        for mod in self.mods:
            if mod.acronym in ['DT', 'NC']:
                params['mods'] = "64"  # Why do mod acronyms not work here.
            if mod.acronym in ['HT', 'DC']:
                params['mods'] = "256"
                
        url = f"https://osu.ppy.sh/api/v2/beatmaps/{score_info['beatmap']['id']}/attributes"
        async with http_session.conn.post(url, headers=headers, params=params) as resp:
            parsed_response = await resp.json()
            return parsed_response['attributes']['star_rating']
    
    def is_taiko(self) -> bool:
        return self.beatmap.mode == "taiko"
    
    def has_illegal_mods(self) -> bool:
        for mod in self.mods:
            if mod.acronym not in ALLOWED_MODS:
                return True
        return False
    
    def has_illegal_dt_ht_rates(self) -> bool:
        for mod in self.mods:
            # Default DT and HT do not have a 'speed_change' modifier
            if mod.acronym in ['DT', 'NC', 'HT', 'DC'] and mod.settings is not None:
                if 'speed_change' in mod.settings:
                    return True
        return False
    
    async def is_already_submitted(self) -> bool:
        async with aiosqlite.connect("./data/database.db") as conn:
    
            # See if the score database contains a row with the exact same information as the submitted score
            query = "SELECT * FROM submitted_scores WHERE osu_id=? AND beatmap_id=? AND beatmapset_id=? AND timestamp=?"
            cursor = await conn.execute(query, (self.user_osu_id, self.beatmap.id, self.beatmapset.id, self.timestamp))
            score_in_database = await cursor.fetchone()
            
            # If there is, that means the score has already been submitted
            if score_in_database:
                return True
            return False
    
    def is_complete_runthrough_of_map(self) -> bool:
        return self.map_completion_progress() == 1.0
    
    def map_completion_progress(self) -> float:
        """
        Returns a value between 0 and 1 representing the percentage of the map that has been completed before quitting out.
        1 means that the score is a complete runthrough of the map.
        """
        
        return (self.num_300s + self.num_100s + self.num_misses) / self.beatmap.num_notes
    
    def is_afk(self) -> bool:
        """If the accuracy is below an arbitrary threshold, we can deduce that the player wasn't actually playing the map."""
        if self.accuracy < 50:
            return True
        return False
    
    def mod_is_in_score(self, mods_to_check_for: str | list[str]) -> bool:
        """
        Check if a mod(s) is in a score. Accepts a mod acronym or a list of mod acronyms.
        If a list is passed in, it will return True if any of the mods in the list are in the score.
        """
        
        for mod_used in self.mods:
            if mod_used.acronym in mods_to_check_for:
                return True
        return False