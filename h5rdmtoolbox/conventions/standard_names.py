from dataclasses import dataclass
from pathlib import Path
from re import sub as re_sub

import appdirs
import pandas as pd
from IPython.display import display, HTML
from pint_xarray import unit_registry as ureg
from tabulate import tabulate

from .utils import xml2dict, dict2xml, is_valid_email_address

# storage directory of user defined standard names:
sn_user_dir = Path(appdirs.user_data_dir('standard_names'))


class CustomException(Exception):
    """Custom Exception"""
    message: str
    reason: str

    def __str__(self) -> str:
        return f'{self.message} -> {self.reason}'

    def reason(self) -> str:
        """returns the reason for the exception"""
        return ''


def equal_base_units(unit1, unit2):
    """returns if two units are equivalent"""
    base_unit1 = ureg(unit1).to_base_units().units.__format__(ureg.default_format)
    base_unit2 = ureg(unit2).to_base_units().units.__format__(ureg.default_format)
    return base_unit1 == base_unit2


class WrongStandardNameUnit(CustomException):
    """Exception class for inconsistent units of two standard names"""

    def __init__(self, standard_name, dataset_unit, standard_name_unit):
        self.standard_name = standard_name
        self.dataset_unit = dataset_unit
        self.standard_name_unit = standard_name_unit
        self.message = f'Unit mismatch"'
        super().__init__(self.message)

    def __str__(self) -> str:
        return f'{self.message} -> {self.reason()}'

    def reason(self) -> str:
        """returns the reason as string"""
        return f'Unit of standard name "{self.standard_name}" not as expected: ' \
               f'"{self.dataset_unit}" != "{self.standard_name_unit}"'


class StandardNameError(Exception):
    """Exception class for error associated with standard name usage"""
    pass


class StandardNameConvention:
    """Standard name interface. Can read standard name dictionaries
    from various sources. Intended to be used with HDF wrapper classes.
    TODO: can read various sources(xml, web source, ...)"""

    VALID_CHAR = '[^a-zA-Z0-9_]'

    def __init__(self, standard_name_dict: dict,
                 name: str, version: int, contact: str, institution: str):
        if standard_name_dict is None:
            self._dict = {}
        else:
            self._dict = standard_name_dict
            if not self._verify_dict():
                raise ValueError(f'Invalid dictionary structure. Each entry must contain "desciption" and '
                                 '"canonical units"')
        self._version = version

        if len(name.split(' ')) > 1:
            raise ValueError('No spaces allowed in the name')

        self._name = name
        if contact is None:
            self._contact = contact
        else:
            if is_valid_email_address(contact):
                self._contact = contact
            else:
                raise ValueError(f'Invalid email address: {contact}')
        self._institution = institution

    def __getitem__(self, item):
        return StandardName(item,
                            self._dict.__getitem__(item)['description'],
                            self._dict.__getitem__(item)['canonical_units'],
                            convention=self)

    def __contains__(self, item):
        return item in self._dict

    def __repr__(self) -> str:
        if self._name is None:
            name = self.__class__.__name__
        else:
            name = self._name
        if self._version:
            version = 'None'
        else:
            version = self._version
        return f"{name} (version: {version})"

    def __str__(self):
        return self.__repr__()

    def _verify_dict(self) -> bool:
        """verifies the structure of the standard name dictionary"""
        if self._dict:
            for v in self._dict.values():
                if isinstance(v, str):
                    return False
                if 'description' not in v.keys() and 'canonical_units' not in v.keys():
                    return False
        return True

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

    @property
    def name(self):
        """Name of convention"""
        return self._name

    @property
    def institution(self):
        """Name of convention"""
        return self._institution

    @property
    def contact(self):
        """Name of convention"""
        return self._contact

    @property
    def version(self) -> int:
        """Version of standard name convention"""
        return self._version

    @property
    def names(self):
        """returns all registered stndard names of the convention"""
        return list(self._dict.keys())

    def get(self, item):
        """returns the item"""
        if self._dict:
            if item in self._dict:
                return self.__getitem__(item)
        return StandardName(item, None, None, self)

    def set(self, name: str, canonical_units: str, description: str):
        """add or modifies a standard name in the convention"""
        self.verify_name(name)
        self._dict[name] = {'canonical_units': canonical_units, 'description': description}

    def is_valid(self, name) -> bool:
        """checks if names exists and is compliant with standard name rules"""
        if self._dict:
            if not self.name_exists(name):
                return False
            return self.verify_name(name)
        return True

    def validate(self, name, units):
        """Raises an error if name is not compliant with standard name rules"""
        if self._dict:
            if units is None:
                units = ''
            if not self.is_valid(name):
                if not self.name_exists(name):
                    reason = 'Name does not exist.'
                else:
                    reason = 'Name does not comply with naming rules'

                raise StandardNameError(
                    f'Standard name "{name}" is not valid standard name of convention "{self.name}". '
                    f'Reason: {reason}')
            self.validate_units(name, units)

    def verify_name(self, name) -> bool:
        """Raises an error if name is not in convention class"""
        if not name.islower():
            raise ValueError(f'Standard name must be lowercase!')
        if re_sub(self.VALID_CHAR, '', name) != name:
            raise ValueError(f'Invalid characters in name. Only "_" is allowed.')
        return True

    def name_exists(self, name):
        """Returns if name exists in convention"""
        return name in self._dict

    @staticmethod
    def from_xml(xml_filename: Path):
        """Reads convention from q XML file"""
        if not Path(xml_filename).exists():
            raise FileExistsError(f'XML file not found: {xml_filename}')
        _dict, _meta = xml2dict(xml_filename)
        return StandardNameConvention(_dict, name=_meta['name'],
                                      version=_meta['version'],
                                      contact=_meta['contact'],
                                      institution=_meta['institution'])

    def to_xml(self, xml_filename: Path, datetime_str=None) -> str:
        """saves the convention in a XML file"""
        return dict2xml(self._dict, name=self._name, filename=xml_filename, version=self.version,
                        contact=self._contact, institution=self._institution,
                        datetime_str=datetime_str)

    def validate_units(self, name, units) -> bool:
        """Raises an error if units is wrong"""
        if self._dict:
            if not equal_base_units(self[name].canonical_units, units):
                raise StandardNameError(f'Unit of standard name "{name}" not as expected: '
                                        f'"{units}" != "{self[name].canonical_units}"')
            return True
        return True


@dataclass
class StandardName:
    """basic standard name class"""
    name: str
    description: str
    canonical_units: str
    convention: StandardNameConvention

    def __str__(self):
        return self.name


def as_dataframe(snc: StandardNameConvention):
    """returns standard name dict as pandas frame"""
    from pandas import DataFrame
    return DataFrame.from_dict(snc, orient='index')


EmptyStandardNameConvention = StandardNameConvention(standard_name_dict={}, name='EmptyStandardNameConvention',
                                                     version=0, contact='dummy@dummy.com',
                                                     institution='dummy_institution')

FluidConvention = StandardNameConvention.from_xml(sn_user_dir.joinpath('fluid-v1.0.xml'))
PIVConvention = StandardNameConvention.from_xml(sn_user_dir.joinpath('piv-v1.0.xml'))
