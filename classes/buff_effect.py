from enum import auto

from classes.extended_enum import ExtendedEnum


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