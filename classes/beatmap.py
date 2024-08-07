from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from classes.score import Score


class Beatmap:
    """Class representing a beatmap, which is a singular difficulty. Not to be confused with beatmapset."""
    
    id: int
    url: str
    mode: str
    difficulty_name: str
    sr: float
    od: float
    hp: float
    num_notes: int
    num_sliders: int
    num_spinners: int
    drain_time: int
    status: str
    
    def __init__(self, beatmap_info: dict[str, Any], beatmap_attributes: dict[str, Any], score: 'Score'):
        
        self.id = beatmap_info['id']
        self.url = beatmap_info['url']
        self.mode = beatmap_info['mode']
        self.difficulty_name = beatmap_info['version']
        self.sr = beatmap_attributes['star_rating']
        self.__init_od(beatmap_info, score)
        self.__init_hp(beatmap_info, score)
        self.num_notes = beatmap_info['count_circles']  # Inaccurate for converts
        self.num_sliders = beatmap_info['count_sliders']  # Inaccurate for converts
        self.num_spinners = beatmap_info['count_spinners']
        self.__init_drain_time(beatmap_info, score)
        self.status = beatmap_info['status']
    
    def __init_od(self, beatmap_info: dict[str, Any], score: 'Score'):
        self.od = beatmap_info['accuracy']
        if score.mod_is_in_score("HR"):
            self.od *= 1.4
        elif score.mod_is_in_score("EZ"):
            self.od *= 0.5
        self.od = min(self.od, 10)
    
    def __init_hp(self, beatmap_info: dict[str, Any], score: 'Score'):
        self.hp = beatmap_info['drain']
        if score.mod_is_in_score("HR"):
            self.hp *= 1.4
        elif score.mod_is_in_score("EZ"):
            self.hp *= 0.5
        self.hp = min(self.hp, 10)
    
    def __init_drain_time(self, beatmap_info: dict[str, Any], score: 'Score'):
        self.drain_time = beatmap_info['hit_length']
        if score.mod_is_in_score("DT"):
            self.drain_time = int(self.drain_time / 1.5)
        elif score.mod_is_in_score("HT"):
            self.drain_time = int(self.drain_time / 0.75)


class Beatmapset:
    """Class representing a beatmapset (known as "set"), which is a collection of difficulties. Not to be confused with beatmap."""
    
    id: int
    artist: str
    artist_unicode: str
    title: str
    title_unicode: str
    creator: str
    
    def __init__(self, beatmapset_info: dict[str, Any]):
        self.id = beatmapset_info['id']
        self.artist = beatmapset_info['artist']
        self.artist_unicode = beatmapset_info['artist_unicode']
        self.title = beatmapset_info['title']
        self.title_unicode = beatmapset_info['title_unicode']
        self.creator = beatmapset_info['creator']