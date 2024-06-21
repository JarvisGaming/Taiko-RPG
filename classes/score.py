import datetime
import math
from typing import Any

import aiosqlite
import dateutil.parser
from classes.beatmap import Beatmap
from classes.beatmapset import Beatmapset
from classes.mod import Mod
from other.global_constants import *


class Score:
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
    
    total_score: int  # Lazer score_info, so stable replays are scored w/ classic mod (vs legacy_total_score)
    max_combo: int  # In the replay, not the map
    pp: float | None
    ruleset_id: int  # I don't know what this does
    has_replay: bool
    is_FC: bool
    is_pass: bool
    is_convert: bool
    
    beatmap: Beatmap
    beatmapset: Beatmapset
    
    exp_gained: dict[str, int]  # Exp bar names are the keys, amount of exp gained are the values
    
    def __init__(self, score_info: dict[str, Any], discord_id: int):
        self.username = score_info['user']['username']
        self.user_osu_id = score_info['user']['id']
        self.user_discord_id = discord_id
        
        self.score_id = score_info['id']
        self.score_url = f"https://osu.ppy.sh/scores/{self.score_id}"
        
        self.num_300s = score_info['statistics'].get('great', 0)  # Field is ommitted when fetching from API if there are no 300s
        self.num_100s = score_info['statistics'].get('ok', 0)  # Field is ommitted when fetching from API if there are no 100s
        self.num_misses = score_info['statistics'].get('miss', 0)  # Field is ommitted when fetching from API if there are no misses
        self.accuracy = score_info['accuracy'] * 100  # Convert from 0.99 to 99 for example, since it's more intuitive
        self.rank = score_info['rank']
        self.mods = [Mod(mod_info) for mod_info in score_info['mods']]
        self.mods_human_readable = self.__create_human_readable_mod_listing()
        self.timestamp = dateutil.parser.parse(score_info['ended_at'])  # Converts ISO 8601 format timestamp to datetime object
        
        self.total_score = score_info['total_score']
        self.max_combo = score_info['max_combo']
        self.pp = score_info['pp']
        self.ruleset_id = score_info['ruleset_id']
        self.has_replay = score_info['has_replay']
        self.is_FC = score_info['is_perfect_combo']
        self.is_pass = score_info['passed']
        self.is_convert = score_info['beatmap']['convert']
        
        self.beatmap = Beatmap(score_info['beatmap'])
        self.beatmapset = Beatmapset(score_info['beatmapset'])
        
        self.__init_exp_gained()
    
    def __create_human_readable_mod_listing(self) -> str:
        """Create a human-readable listing of the mods used."""
        
        mods_human_readable = ""
        for mod in self.mods:
            mods_human_readable += mod.acronym + " "
        return mods_human_readable.strip()  # Remove trailing whitespace
    
    def __init_exp_gained(self):
        self.exp_gained = {exp_bar_name: 0 for exp_bar_name in EXP_BAR_NAMES}
        self.__set_exp_gained()
        
    def __set_exp_gained(self):
        """
        Set the exp gained for each mod. If there are no mods, only NoMod exp will be given.
        Otherwise, split exp amongst activated exp bar mods.
        """
        self.exp_gained['Overall'] = self.__calculate_total_exp_gained()
        number_of_exp_bar_mods_activated = self.__count_number_of_exp_bar_mods_activated()
        
        if number_of_exp_bar_mods_activated == 0:
            self.exp_gained['NM'] = self.exp_gained['Overall']
            return
        
        for mod in self.mods:
            if mod.acronym in EXP_BAR_NAMES:
                self.exp_gained[mod.acronym] = self.exp_gained['Overall'] // number_of_exp_bar_mods_activated

    def __calculate_total_exp_gained(self) -> int:
        """Calculate the TOTAL exp gained from submitting a score based on a formula."""
        
        total_exp_gained = math.pow(max(3*self.num_300s + 0.75*self.num_100s - 3*self.num_misses, 0), 0.6) * math.pow(min(self.beatmap.sr+1, 11), 1.2) * 0.05
        total_exp_gained = int(total_exp_gained)
        return total_exp_gained

    def __count_number_of_exp_bar_mods_activated(self) -> int:
        number_of_exp_bar_mods_activated = 0
        
        for mod in self.mods:
            if mod.acronym in EXP_BAR_NAMES:
                number_of_exp_bar_mods_activated += 1
                
        return number_of_exp_bar_mods_activated
    
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
            if mod.acronym in ["DT", "HT"] and 'speed_change' in mod.settings:
                return True
        return False
    
    async def is_already_submitted(self) -> bool:
        async with aiosqlite.connect("./data/database.db") as conn:
            
            cursor = await conn.cursor()
    
            # See if the replay database contains a row with the exact same information as the submitted replay
            query = "SELECT * FROM submitted_replays WHERE osu_id=? AND beatmap_id=? AND beatmapset_id=? AND timestamp=?"
            await cursor.execute(query, (self.user_osu_id, self.beatmap.id, self.beatmapset.id, self.timestamp))
            replay_in_database = await cursor.fetchone()
            
            # If there is, that means the replay has already been submitted
            if replay_in_database:
                return True
            return False