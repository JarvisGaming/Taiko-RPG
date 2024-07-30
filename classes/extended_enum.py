from enum import Enum


class ExtendedEnum(Enum):
    @classmethod
    def list(cls):
        """Returns a list of all members of the enum as enum values."""
        return [x for x in cls.__members__.values()]
    
    @classmethod
    def list_as_str(cls):
        """Returns a list of all members of the enum as strings."""
        return [x.name for x in cls]
