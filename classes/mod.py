from enum import auto
from typing import Any

from classes.extended_enum import ExtendedEnum


class Mod:
    """Class representing an osu mod."""
    
    acronym: str
    settings: dict[str, Any]
    
    def __init__(self, mod_info: dict[str, Any]):
        self.acronym = mod_info['acronym']
        self.settings = mod_info.get('settings', None)  # Field is ommitted when fetching from API if the mod doesn't not have any settings changed

        
class AllowedMods(ExtendedEnum):
    """Mods allowed in a submitted score."""
    
    NF = auto()
    EZ = auto()
    HD = auto()
    HR = auto()
    FL = auto()
    DT = auto()
    NC = auto()
    HT = auto()
    DC = auto()
    SD = auto()
    PF = auto()
    CL = auto()
    AC = auto()
    SG = auto()
    MU = auto()