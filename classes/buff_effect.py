from enum import Enum, auto


class ExtendedEnum(Enum):
    @classmethod
    def list(cls):
        """Returns a list of all members of the enum as enum values."""
        return [x for x in cls.__members__.values()]
    
    @classmethod
    def list_as_str(cls):
        """Returns a list of all members of the enum as strings."""
        return [x.name for x in cls]

class BuffEffect(ExtendedEnum):
    OVERALL_EXP_GAIN = auto()
    NM_EXP_GAIN = auto()
    HD_EXP_GAIN = auto()
    HR_EXP_GAIN = auto()
    DT_EXP_GAIN = auto()
    HT_EXP_GAIN = auto()
    TAIKO_TOKEN_GAIN = auto()

class BuffEffectType(ExtendedEnum):
    DIRECT_MODIFICATION = auto()  # eg directly changes gain formula
    ADDITIVE = auto()  # Includes subtraction
    MULTIPLICATIVE = auto()  # Includes division
    EXPONENTIAL = auto()  # Includes logarithmic