"""Transformation module"""
import re

from .name import StandardName
from .. import errors


class Transformation:

    def __init__(self, pattern, func):
        self.pattern = pattern
        self.func = func

    def __repr__(self):
        return f"{self.__class__.__name__}({self.pattern}, {self.func.__name__})"

    def match(self, standard_name):
        """Check if the transformation is applicable to the standard name"""
        return re.match(self.pattern, standard_name)


def evaluate(transformation: Transformation, match, snt) -> StandardName:
    """Evaluate the transformation. Raises an error if the transformation is not applicable."""
    return transformation.func(match, snt)


def _magnitude_of(match, snt) -> StandardName:
    groups = match.groups()
    assert len(groups) == 1
    sn = snt[groups[0]]
    new_description = f"Magnitude of {sn.name}"
    return StandardName(match.string, sn.units, new_description)


magnitude_of = Transformation(r"^magnitude_of_(.*)$", _magnitude_of)


def _arithmetic_mean_of(match, snt) -> StandardName:
    """Arithmetic mean"""
    groups = match.groups()
    assert len(groups) == 1
    sn = snt[groups[0]]
    new_description = f"Arithmetic mean of {sn.name}"
    return StandardName(match.string, sn.units, new_description)


arithemtic_mean_of = Transformation(r"^arithmetic_mean_of_(.*)$", _arithmetic_mean_of)


def _standard_deviation_of(match, snt) -> StandardName:
    groups = match.groups()
    assert len(groups) == 1
    sn = snt[groups[0]]
    new_description = f"Standard deviation of {sn.name}"
    return StandardName(match.string, sn.units, new_description)


standard_deviation_of = Transformation(r"^standard_deviation_of_(.*)$", _standard_deviation_of)


def _square_of(match, snt) -> StandardName:
    groups = match.groups()
    assert len(groups) == 1
    sn = snt[groups[0]]
    new_description = f"Square of {sn.name}"
    new_units = (1 * sn.units * sn.units).units
    return StandardName(match.string, new_units, new_description)


square_of = Transformation(r"^square_of_(.*)$", _square_of)


def _derivative_of_X_wrt_to_Y(match, snt) -> StandardName:
    """Check if a standard name is a derivative of X wrt to Y"""

    groups = match.groups()
    assert len(groups) == 2
    if all([snt.check(n) for n in groups]):
        sn1 = snt[groups[0]]
        sn2 = snt[groups[1]]
        new_units = (1 * sn1.units / 1 * sn2.units).units
        new_description = f"Derivative of {sn1.name} with respect to {sn2.name}"
        return StandardName(match.string, new_units, new_description)
    raise errors.StandardNameError(f'One or multiple standard names in "{match.string}" are not valid.')


derivative_of_X_wrt_to_Y = Transformation(r"^derivative_of_(.*)_wrt_(.*)$",
                                          _derivative_of_X_wrt_to_Y)


def _product_of_X_and_Y(match, snt) -> StandardName:
    """Check if a standard name is a derivative of X wrt to Y"""
    groups = match.groups()
    assert len(groups) == 2
    if all([snt.check(n) for n in groups]):
        sn1 = snt[groups[0]]
        sn2 = snt[groups[1]]
        new_units = (1 * sn1.units * sn2.units).units
        new_description = f"Product of {sn1.name} and {sn2.name}"
        return StandardName(match.string, new_units, new_description)
    raise errors.StandardNameError(f'One or multiple standard names in "{match.string}" are not valid.')


product_of_X_and_Y = Transformation(r"^product_of_(.*)_and_(.*)$",
                                    _product_of_X_and_Y)


def _ratio_of_X_and_Y(match, snt) -> StandardName:
    """Check if a standard name is a derivative of X wrt to Y"""
    groups = match.groups()
    assert len(groups) == 2
    if all([snt.check(n) for n in groups]):
        sn1 = snt[groups[0]]
        sn2 = snt[groups[1]]
        new_units = (1 * sn1.units / sn2.units).units
        new_description = f"Ratio of {sn1.name} and {sn2.name}"
        return StandardName(match.string, new_units, new_description)
    raise errors.StandardNameError(f'One or multiple standard names in "{match.string}" are not valid.')


ratio_of_X_and_Y = Transformation(r"^ratio_of_(.*)_and_(.*)$",
                                  _ratio_of_X_and_Y)
