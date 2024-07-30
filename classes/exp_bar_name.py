from enum import auto

from classes.extended_enum import ExtendedEnum


class ExpBarName(ExtendedEnum):
    """A class representing the names of all available exp bars. Does not include NC, DC."""
    
    Overall = auto()
    NM = auto()
    HD = auto()
    HR = auto()
    DT = auto()
    HT = auto()