from typing import Any

class Beatmap:
    id: int
    url: str
    mode: str
    checksum: str
    difficulty_name: str
    sr: float
    od: float
    hp: float
    num_notes: int
    num_sliders: int
    num_spinners: int
    drain_time: int
    status: str
    
    def __init__(self, beatmap_info: dict[str, Any]):
        self.id = beatmap_info['id']
        self.url = beatmap_info['url']
        self.mode = beatmap_info['mode']
        self.checksum = beatmap_info['checksum']
        self.difficulty_name = beatmap_info['version']
        self.sr = beatmap_info['difficulty_rating']
        self.od = beatmap_info['accuracy']
        self.hp = beatmap_info['drain']
        self.num_notes = beatmap_info['count_circles']
        self.num_sliders = beatmap_info['count_sliders']
        self.num_spinners = beatmap_info['count_spinners']
        self.drain_time = beatmap_info['hit_length']
        self.status = beatmap_info['status']