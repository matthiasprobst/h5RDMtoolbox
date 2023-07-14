"""Transformation for standard names"""
import re
from typing import Callable

from .standard_name import StandardName


class Transformation:
    """Transformation for standard names"""

    def __init__(self, snt, func: Callable):
        self.snt = snt
        self.func = func

    def __call__(self, standard_name):
        return self.func(standard_name, self.snt)


def derivative_of_X_wrt_to_Y(standard_name, snt) -> StandardName:
    """Check if a standard name is a derivative of X wrt to Y"""
    match = re.match(r"^derivative_of_(.*)_wrt_to_(.*)$",
                     standard_name)
    if match:
        groups = match.groups()
        assert len(groups) == 2
        if all([snt.check(n) for n in groups]):
            sn1 = snt[groups[0]]
            sn2 = snt[groups[1]]
            new_units = (1*sn1.units / 1*sn2.units).units
            new_description = f"Derivative of {sn1.name} wrt to {sn2.name}"
            return StandardName(standard_name, new_units, new_description)
    return False
    # raise ValueError(f"Standard name '{standard_name}' is not a derivative of X wrt to Y")
