from typing import Any


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