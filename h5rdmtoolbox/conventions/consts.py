import enum


class DefaultValue(enum.Enum):
    EMPTY = 1
    NONE = 2  # will show None in the signature but will not set None to the attribute. If the user passes None, then None will be written
