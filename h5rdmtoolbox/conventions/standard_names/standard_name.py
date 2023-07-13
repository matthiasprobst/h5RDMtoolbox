import pint
from typing import Union

from h5rdmtoolbox import get_ureg


class StandardName:
    """Standard Name class"""

    def __init__(self, name: str, units: Union[str, pint.Unit], description: str, snt: "StandardNameTable"):
        self.name = name
        if isinstance(units, str):
            self.units = get_ureg()(units)
        elif isinstance(units, pint.Unit):
            self.units = units
        else:
            raise TypeError(f"units must be a str or a pint.Unit, not {type(units)}")
        self.description = description
        self.snt = snt

    def __repr__(self):
        return f'<StandardName: "{self.name}" units={self.units}, description="{self.description}">'

    def equal_unit(self, other_unit: pint):
        """compares the base units of this standard name with another unit provided as a string
        or pint.Unit"""
        from ..utils import equal_base_units
        return equal_base_units(self.units, other_unit)
