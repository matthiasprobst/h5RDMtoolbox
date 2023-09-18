import pint
import re
import warnings
from typing import Dict, Union

from h5rdmtoolbox import get_ureg
from . import consts
from .utils import _units_power_fix
from ..utils import equal_base_units
from ... import errors


class StandardName:
    """Standard Name class"""

    def __init__(self, name: str,
                 units: Union[str, pint.Unit] = None,
                 description: str = None,
                 canonical_units: str = None,
                 isvector: bool = False,
                 alias: str = None):
        StandardName.check_syntax(name)
        self._is_vector = isvector
        self.name = name
        if canonical_units is not None:
            warnings.warn('Parameter "canonical_units" is depreciated. Use "units" instead.', DeprecationWarning)
            units = canonical_units
        if description is None:
            # TODO if canonical_units is removed, then default value None must be removed for description, too
            raise ValueError('A description must be provided')
        if isinstance(units, str):
            self.units = get_ureg().Unit(_units_power_fix(units))
        elif isinstance(units, pint.Unit):
            self.units = units
        else:
            raise TypeError(f"units must be a str or a pint.Unit, not {type(units)}")
        # convert units to base units:
        q = 1 * self.units
        self.unit = q.to_base_units().units
        if description[-1] != '.':
            description += '.'  # add a dot at the end of the description
        self.description = description
        if alias is not None:
            self.check_syntax(alias)
        self.alias = alias

    def __to_h5attr__(self) -> str:
        return self.name

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'<StandardName: "{self.name}" [{self.units}] {self.description}>'

    def __eq__(self, other):
        if isinstance(other, StandardName):
            return self.name == other.name and self.units == other.units and self.description == other.description
        elif isinstance(other, str):
            return self.name == other
        raise TypeError(f'Cannot compare StandardName with {type(other)}')

    def _repr_html_(self, checkbox_state='checked'):
        # collapsable html representation
        if self.is_vector():
            sn_name = f'{self.name} (vector quantity)'
        else:
            sn_name = self.name
        from time import perf_counter_ns
        _id = self.name + perf_counter_ns().__str__()
        out = f"""<ul style="list-style-type: none;" class="h5grp-sections">
    <li>
        <input id="group-{_id}" type="checkbox" {checkbox_state}>
        <label style="font-weight: bold" for="group-{_id}">
        {sn_name}</label>
        <ul class="h5tb-attr-list">
"""
        out += f'           <li style="list-style-type: none; font-style: italic">units : {self.units}</li>'
        out += f'           <li style="list-style-type: none; font-style: italic">description : {self.description}</li>'
        out += """      </il>
    </ul>
</ul>"""
        return out

    def equal_unit(self, other_unit: pint):
        """compares the base units of this standard name with another unit provided as a string
        or pint.Unit"""
        return equal_base_units(self.units, other_unit)

    @staticmethod
    def check_syntax(standard_name: str):
        """formal check of the syntax"""
        if not isinstance(standard_name, str):
            raise TypeError(f'Standard name must be type string but is {type(standard_name)}')
        if len(standard_name) == 0:
            raise errors.StandardNameError('Name too short!')
        if re.sub(consts.VALID_CHARACTERS, '', standard_name) != standard_name:
            raise errors.StandardNameError('Invalid special characters in name '
                                           f'"{standard_name}": Only "{consts.VALID_CHARACTERS}" '
                                           'is allowed.')

        if consts.PATTERN != '' and consts.PATTERN is not None:
            if re.match(consts.PATTERN, standard_name):
                raise errors.StandardNameError(
                    f'Standard name "{standard_name}" does not match pattern "{consts.PATTERN}"')

    def to_dict(self) -> Dict:
        """Return dictionary representation of StandardName"""
        return dict(name=self.name, units=str(self.units), description=self.description)

    def check(self, snt: "StandardNameTable"):
        """check if is a valid standard name of the provided table"""
        return snt.check(self.name)

    def is_vector(self) -> bool:
        """check if is a vector"""
        return self._is_vector
