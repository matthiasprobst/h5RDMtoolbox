"""Transformation module"""
import re
from typing import Union

from .name import StandardName
from .. import errors


def magnitude_of(standard_name, snt) -> StandardName:
    match = re.match(r"^magnitude_of_(.*)$",
                     standard_name)
    if match:
        groups = match.groups()
        assert len(groups) == 1
        sn = snt[groups[0]]
        new_description = f"Magnitude of {sn.name}"
        return StandardName(standard_name, sn.units, new_description)
    return False


def arithmetic_mean_of(standard_name, snt) -> StandardName:
    """Arithmetic mean"""
    match = re.match(r"^arithmetic_mean_of_(.*)$",
                     standard_name)
    if match:
        groups = match.groups()
        assert len(groups) == 1
        sn = snt[groups[0]]
        new_description = f"Arithmetic mean of {sn.name}"
        return StandardName(standard_name, sn.units, new_description)
    return False


def standard_deviation_of(standard_name, snt) -> StandardName:
    match = re.match(r"^standard_deviation_of_(.*)$",
                     standard_name)
    if match:
        groups = match.groups()
        assert len(groups) == 1
        sn = snt[groups[0]]
        new_description = f"Standard deviation of {sn.name}"
        return StandardName(standard_name, sn.units, new_description)
    return False


def square_of(standard_name, snt) -> StandardName:
    match = re.match(r"^square_of_(.*)$",
                     standard_name)
    if match:
        groups = match.groups()
        assert len(groups) == 1
        sn = snt[groups[0]]
        new_description = f"Square of {sn.name}"
        new_units = (1 * sn.units * sn.units).units
        return StandardName(standard_name, new_units, new_description)
    return False


def difference_of_X_across_device(standard_name, snt) -> Union[StandardName, bool]:
    """Difference of X across device"""
    match = re.match(r"^difference_of_(.*)_across_(.*)$",
                     standard_name)

    if not match:
        return False
    groups = match.groups()
    assert len(groups) == 2
    if groups[1] not in snt.devices:
        raise KeyError(f'Device {groups[1]} not found in registry of the standard name table. '
                       f'Available devices are: {snt.devices}.')
    try:
        sn = snt[groups[0]]
    except errors.StandardNameError:
        return False
    new_description = f"Difference of {sn.name} across {groups[1]}"
    return StandardName(standard_name, sn.units, new_description)


def difference_of_X_and_Y_across_device(standard_name, snt) -> StandardName:
    """Difference of X and Y across device"""
    match = re.match(r"^difference_of_(.*)_and_(.*)_across_(.*)$",
                     standard_name)
    if match:
        groups = match.groups()
        assert len(groups) == 3
        if groups[2] not in snt.devices:
            raise KeyError(f'Device {groups[2]} not found in registry of the standard name table. '
                           f'Available devices are: {snt.devices}')
        sn1 = snt[groups[0]]
        sn2 = snt[groups[1]]
        if sn1.units != sn2.units:
            raise ValueError(f'Units of "{sn1.name}" and "{sn2.name}" are not compatible: "{sn1.units}" and '
                             f'"{sn2.units}".')
        new_description = f"Difference of {sn1.name} and {sn2.name} across {groups[2]}"
        return StandardName(standard_name, sn1.units, new_description)
    return False


def difference_of_X_and_Y_between_LOC1_and_LOC2(standard_name, snt) -> StandardName:
    """Difference of X and Y across device"""
    match = re.match(r"^difference_of_(.*)_and_(.*)_between_(.*)_and_(.*)$",
                     standard_name)
    if match:
        groups = match.groups()
        assert len(groups) == 4
        if groups[2] not in snt.locations:
            raise KeyError(f'StandardLocation "{groups[2]}" not found in registry of the standard name table. '
                           f'Available locations are: {snt.locations}')
        if groups[3] not in snt.locations:
            raise KeyError(f'StandardLocation "{groups[3]}" not found in registry of the standard name table. '
                           f'Available locations are: {snt.locations}')
        sn1 = snt[groups[0]]
        sn2 = snt[groups[1]]
        if sn1.units != sn2.units:
            raise ValueError(f'Units of "{sn1.name}" and "{sn2.name}" are not compatible: "{sn1.units}" and '
                             f'"{sn2.units}".')
        new_description = f"Difference of {sn1.name} and {sn2.name} between {groups[2]} and {groups[3]}"
        return StandardName(standard_name, sn1.units, new_description)
    return False


def X_at_LOC(standard_name, snt) -> StandardName:
    match = re.match(r"^(.*)_at_(.*)$", standard_name)
    if match:
        groups = match.groups()
        assert len(groups) == 2
        sn = snt[groups[0]]
        loc = groups[1]
        if loc not in snt.locations:
            raise KeyError(f'StandardLocation "{loc}" not found in registry of the standard name table. '
                           f'Available locations are: {snt.locations}')
        new_description = f"{sn} at {loc}"
        return StandardName(standard_name, sn.units, new_description)
    return False


def in_reference_frame(standard_name, snt) -> StandardName:
    """A standard name in a standard reference frame"""
    if not snt.standard_reference_frames:
        return False
    match = re.match(r"^(.*)_in_(.*)$", standard_name)
    if match:
        groups = match.groups()
        assert len(groups) == 2
        sn = snt[groups[0]]
        frame = groups[1]
        if frame not in snt.standard_reference_frames:
            raise KeyError(f'Reference Frame "{frame}" not found in registry of the standard name table. '
                           f'Available reference frames are: {snt.standard_reference_frames.names}')
        new_description = f'{sn.description}. The quantity is relative to the reference frame "{frame}"'
        return StandardName(standard_name, sn.units, new_description)
    return False


def component_of(standard_name, snt) -> StandardName:
    """Component of a standard name, e.g. x_velocity where velocity is the
    existing standard name and x is a registered component"""
    if not snt.components:
        return False
    match = re.match(r"^(.*)_(.*)$", standard_name)
    if match:
        groups = match.groups()
        assert len(groups) == 2
        component = groups[0]
        if component not in snt.components:
            return False
        sn = snt[groups[1]]
        if not sn.is_vector():
            raise errors.StandardNameError(f'"{sn.name}" is not a vector quantity.')
        new_description = f'{sn.description} {snt.components[component].description}'
        return StandardName(standard_name, sn.units, new_description)

    return False


def surface_(standard_name, snt) -> StandardName:
    match = re.match(r"^(.*)_(.*)$", standard_name)
    if match:
        groups = match.groups()
        assert len(groups) == 2
        surface = groups[0]
        if surface not in snt.surfaces:
            return False
        sn = snt[groups[1]]
        new_description = f'{sn.description} {snt.surfaces[surface].description}'
        return StandardName(standard_name, sn.units, new_description)
    return False


def derivative_of_X_wrt_to_Y(standard_name, snt) -> StandardName:
    """Check if a standard name is a derivative of X wrt to Y"""
    match = re.match(r"^derivative_of_(.*)_wrt_(.*)$",
                     standard_name)
    if match:
        groups = match.groups()
        assert len(groups) == 2
        if all([snt.check(n) for n in groups]):
            sn1 = snt[groups[0]]
            sn2 = snt[groups[1]]
            new_units = (1 * sn1.units / 1 * sn2.units).units
            new_description = f"Derivative of {sn1.name} with respect to {sn2.name}"
            return StandardName(standard_name, new_units, new_description)
    return False
    # raise ValueError(f"Standard name '{standard_name}' is not a derivative of X wrt to Y")


def product_of_X_and_Y(standard_name, snt) -> StandardName:
    """Check if a standard name is a derivative of X wrt to Y"""
    match = re.match(r"^product_of_(.*)_and_(.*)$",
                     standard_name)
    if match:
        groups = match.groups()
        assert len(groups) == 2
        if all([snt.check(n) for n in groups]):
            sn1 = snt[groups[0]]
            sn2 = snt[groups[1]]
            new_units = (1 * sn1.units * sn2.units).units
            new_description = f"Product of {sn1.name} and {sn2.name}"
            return StandardName(standard_name, new_units, new_description)
    return False
    # raise ValueError(f"Standard name '{standard_name}' is not a derivative of X wrt to Y")


def ratio_of_X_and_Y(standard_name, snt) -> StandardName:
    """Check if a standard name is a derivative of X wrt to Y"""
    match = re.match(r"^ratio_of_(.*)_and_(.*)$",
                     standard_name)
    if match:
        groups = match.groups()
        assert len(groups) == 2
        if all([snt.check(n) for n in groups]):
            sn1 = snt[groups[0]]
            sn2 = snt[groups[1]]
            new_units = (1 * sn1.units / sn2.units).units
            new_description = f"Ratio of {sn1.name} and {sn2.name}"
            return StandardName(standard_name, new_units, new_description)
    return False
