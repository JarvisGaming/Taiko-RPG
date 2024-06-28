from typing import Any

class Mod:
    """Class representing an osu mod."""
    
    acronym: str
    settings: dict[str, Any]
    
    def __init__(self, mod_info: dict[str, Any]):
        self.acronym = mod_info['acronym']
        self.settings = mod_info.get('settings', None)  # Field is ommitted when fetching from API if the mod doesn't not have any settings changed