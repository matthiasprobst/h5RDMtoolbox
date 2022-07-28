"""Name identifier classes

A name identifier class controls the usage of the HDF5 attribute "standard_name".
The attribute "standard_name" is used in the HDF5 files for all name identifier classes although, for example,
CGNS uses "name" in its convention.
The attribute "standard_name" describes a dataset which can have any dataset name. Example: The dataset "u" (name "u")
has the attribute standard_name="x_velocity". In this case the CF-convention is used, thus, "x_velocity" can be looked-
up in the standard_name_table to get further information about the dataset. It is further linked to a specific units,
here "m/s", which is also checked if the user creates the dataset "u".
Examples for naming tables:
    - standard name table (http://cfconventions.org/Data/cf-standard-names/current/build/cf-standard-name-table.html)
    - CGNS data name convention (https://cgns.github.io/CGNS_docs_current/sids/dataname.html)
"""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from re import sub as re_sub
from typing import Union, Dict

import pandas as pd
from IPython.display import display, HTML
from pint_xarray import unit_registry as ureg
from tabulate import tabulate

from .utils import is_valid_email_address, dict2xml

STRICT = True

CF_DATETIME_STR = '%Y-%m-%dT%H:%M:%SZ%z'


def equal_base_units(unit1, unit2):
    """returns if two units are equivalent"""
    base_unit1 = ureg(unit1).to_base_units().units.__format__(ureg.default_format)
    base_unit2 = ureg(unit2).to_base_units().units.__format__(ureg.default_format)
    return base_unit1 == base_unit2


class StandardizedNameError(Exception):
    """Exception class for error associated with standard name usage"""
    pass


@dataclass
class _NameIdentifierConvention:
    """Basic name identifier convention class
    needed for typing hint
    """
    pass


@dataclass
class StandardizedName:
    """basic stndardized name class"""
    name: str
    description: str
    canonical_units: str
    convention: _NameIdentifierConvention

    def __str__(self):
        return self.name


class _StandardizedNameTable:
    pass


class EmailError(ValueError):
    pass


class StandardizedNameTable(_StandardizedNameTable):
    """Base class of Standardized Name Tables"""

    def __init__(self, name: str, table_dict: Union[Dict, None], version_number: int,
                 institution: str, contact: str,
                 last_modified: Union[str, None] = None,
                 valid_characters: str = ''):
        self._name = name
        self._version_number = version_number
        self._valid_characters = valid_characters
        self._institution = institution
        self.contact = contact
        if last_modified is None:
            now = datetime.now()
            self._last_modified = now.strftime(CF_DATETIME_STR)
        else:
            self._last_modified = last_modified
        if table_dict is None:
            self._dict = {}
        elif isinstance(table_dict, dict):
            self._dict = table_dict
        else:
            raise TypeError(f'Unexpected input type: {type(table_dict)}. Expecting '
                            f'StandardizedNameTable or dict.')
        if not self.has_valid_structure():
            raise KeyError(f'Invalid dictionary structure. Each entry must contain "desciption" and '
                           '"canonical units"')

    @property
    def names(self):
        return list(self._dict.keys())

    @property
    def contact(self):
        return self._contact

    @property
    def name(self):
        return self._name

    @property
    def valid_characters(self):
        return self._valid_characters

    @property
    def laset_modified(self):
        return self._laset_modified

    @property
    def institution(self):
        return self._institution

    @property
    def version_number(self):
        return self._version_number

    @contact.setter
    def contact(self, contact):
        if not is_valid_email_address(contact):
            raise EmailError(f'Invalid email address: {contact}')
        self._contact = contact

    def __repr__(self) -> str:
        if self._name is None:
            name = self.__class__.__name__
        else:
            name = self._name
        if self._version_number:
            version = 'None'
        else:
            version = self._version_number
        return f"{name} (version number: {version})"

    def __str__(self):
        return self.__repr__()

    def __getitem__(self, item) -> StandardizedName:
        return StandardizedName(item, self._dict[item]['description'],
                                self._dict[item]['canonical_units'],
                                convention=self)

    def __contains__(self, item):
        return item in self._dict

    def set(self, name: str, description: str, canonical_units: str):
        if name in self._dict:
            raise StandardizedNameError(f'name "{name}" already exists in table. Use modify() '
                                        f'to change the content')
        self._dict[name] = dict(description=description, canonical_units=canonical_units)

    def modify(self, name: str, description: str, canonical_units: str):
        """modifies a standard name or creates one if non-existing"""
        if name not in self._dict:
            if not description or not canonical_units:
                raise ValueError(f'Name {name} does not exist yet. You must provide string values '
                                 f'for both description and canoncical_units')
            self._dict[name] = dict(description=description, canonical_units=canonical_units)
        else:
            if description:
                self._dict[name]['description'] = description
            if canonical_units:
                self._dict[name]['canonical_units'] = canonical_units

    def get_table(self, sort_by: str = 'name') -> str:
        """string representation of the convention in form of a table"""
        if self._name is None:
            name = self.__class__.__name__
        else:
            name = self._name
        if self._version:
            version = self._version
        else:
            version = 'None'
        df = pd.DataFrame(self._dict).T
        if sort_by.lower() in ('name', 'names', 'standard_name', 'standard_names'):
            sorted_df = df.sort_index()
        elif sort_by.lower() in ('units', 'unit', 'canoncial_units'):
            sorted_df = df.sort_values('canonical_units')
        else:
            sorted_df = df
        return f"{name} (version: {version})\n{tabulate(sorted_df, headers='keys', tablefmt='psql')}"

    def sdump(self, sort_by: str = 'name') -> None:
        print(self.get_table(sort_by=sort_by))

    def dump(self, sort_by: str = 'name'):
        """pretty representation of the table for jupyter notebooks"""
        df = pd.DataFrame(self._dict).T
        if sort_by.lower() in ('name', 'names', 'standard_name', 'standard_names'):
            display(HTML(df.sort_index().to_html()))
        elif sort_by.lower() in ('units', 'unit', 'canoncial_units'):
            display(HTML(df.sort_values('canonical_units').to_html()))
        else:
            raise ValueError(f'Invalid value for sortby: {sort_by}')

    def has_valid_structure(self) -> bool:
        """verifies the structure of the standard name dictionary"""
        if self._dict:
            for v in self._dict.values():
                if isinstance(v, str):
                    return False
                if 'description' not in v.keys() and 'canonical_units' not in v.keys():
                    return False
        return True

    def copy(self):
        return StandardizedNameTable(self._dict)

    def update(self, data: Union[Dict, _StandardizedNameTable]):
        if isinstance(data, StandardizedNameTable):
            self._dict.update(data)
        elif isinstance(data, dict):
            self._dict.update(data)

    @staticmethod
    def from_xml(xml_filename):
        """reads the table from an xml file"""
        from .utils import xml2dict
        _dict, meta = xml2dict(xml_filename)
        meta.update(dict(table_dict=_dict))
        return StandardizedNameTable(**meta)

    # def from_xml(self, xml_filename):
    #     """reads the table from an xml file"""
    #     from .utils import xml2dict
    #     _dict, meta = xml2dict(xml_filename)
    #     self._dict = _dict
    #     self.version_number = meta['version_number']
    #     self.contact = meta['contact']
    #     self.institution = meta['institution']

    def to_xml(self, xml_filename: Path, datetime_str=None, parents=True) -> Path:
        """saves the convention in a XML file"""
        if not xml_filename.parent.exists() and parents:
            xml_filename.parent.mkdir(parents=parents)
        return dict2xml(self._dict, name=self.name, filename=xml_filename, version_number=self.version_number,
                        contact=self.contact, institution=self.institution,
                        datetime_str=datetime_str)

    def check_name(self, name, strict=False) -> bool:
        """Verifies general requirements like lower-case writing and no
        invalid character exist in the name.
        If strict is True, it is further checked whether the name exists
        in the standard name table. This is a global setting which can be changed
        in `conventions.identifier.STRICT`"""

        if re_sub(self.valid_characters, '', name) != name:
            raise StandardizedNameError(f'Invalid characters in name "{name}": Only "_" is allowed.')

        if strict:
            if self._dict:
                if name not in self._dict:
                    raise StandardizedNameError(f'Standardized name "{name}" not in '
                                                'name table')
        return True

    def check_units(self, name, units) -> bool:
        """Raises an error if units is wrong"""
        self.check_name(name, strict=True)  # will raise an error if name not in self._dict
        if self._dict:
            if not equal_base_units(self._dict[name]['canonical_units'], units):
                raise StandardizedNameError(f'Unit of standard name "{name}" not as expected: '
                                            f'"{units}" != "{self[name].canonical_units}"')
        return True


empty_standardized_name_table = StandardizedNameTable(name='EmptyStandardizedNameTable',
                                                      table_dict={},
                                                      version_number=-1,
                                                      institution=None,
                                                      contact='none@none.none',
                                                      last_modified=None,
                                                      valid_characters='')


class CFStandardNameTable(StandardizedNameTable):
    """CF Standard Name Table"""

    def __init__(self, table_dict: Union[Dict, None], version_number: int,
                 institution: str, contact: str,
                 last_modified: Union[str, None] = None,
                 valid_characters: str = '[^a-zA-Z0-9_]'):
        name = 'CF-convention'
        super().__init__(name, table_dict, version_number, institution, contact, last_modified, valid_characters)

    def check_name(self, name, strict=False) -> bool:
        """In addtion to check of base class, lowercase is checked first"""
        if not name.islower():
            raise StandardizedNameError(f'Standard name must be lowercase!')
        return super().check_name(name, strict)


class CGNSStandardNameTable(StandardizedNameTable):
    """CGNS Standard Name Table"""

    def __init__(self, table_dict: Union[Dict, None], version_number: int,
                 institution: str, contact: str,
                 last_modified: Union[str, None] = None,
                 valid_characters: str = '[^a-zA-Z0-9_]'):
        name = 'CGNS-convention'
        super().__init__(name, table_dict, version_number, institution, contact, last_modified, valid_characters)
