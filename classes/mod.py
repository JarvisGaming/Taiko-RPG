from enum import auto
from typing import Any, Optional

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
    
def mod_to_int(mod_acronym: str) -> Optional[int]:
    """Returns the bitwise enum of a specific mod. Only supports classic mods."""

    match(mod_acronym):
        case "NM": return 0
        case "NF": return 1 << 0
        case "EZ": return 1 << 1
        case "TD": return 1 << 2
        case "HD": return 1 << 3
        case "HR": return 1 << 4
        case "SD": return 1 << 5
        case "DT": return 1 << 6
        case "RX": return 1 << 7
        case "HT": return 1 << 8
        case "NC": return 1 << 9
        case "FL": return 1 << 10
        case "AT": return 1 << 11
        case "SO": return 1 << 12
        case "AP": return 1 << 13
        case "PF": return 1 << 14
        case "4K": return 1 << 15
        case "5K": return 1 << 16
        case "6K": return 1 << 17
        case "7K": return 1 << 18
        case "8K": return 1 << 19
        case "FI": return 1 << 20
        case "RD": return 1 << 21
        case "CN": return 1 << 22
        case "TP": return 1 << 23
        case "9K": return 1 << 24
        case "CO": return 1 << 25
        case "1K": return 1 << 26
        case "3K": return 1 << 27
        case "2K": return 1 << 28
        case "V2": return 1 << 29
        case "MR": return 1 << 30