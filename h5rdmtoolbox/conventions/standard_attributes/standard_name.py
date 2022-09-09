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
import pathlib
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Union, List
from typing import Tuple

import h5py
import pandas as pd
import yaml
from IPython.display import display, HTML
from pint.errors import UndefinedUnitError
from pint_xarray import unit_registry as ureg
from tabulate import tabulate

from . import register_standard_attribute
from ..utils import equal_base_units
from ..utils import is_valid_email_address, dict2xml
from ... import config
from ..._user import user_dirs
from ...errors import StandardNameError, EmailError, StandardNameTableError
from ...h5wrapper.h5file import H5Dataset, H5Group

STRICT = True

CF_DATETIME_STR = '%Y-%m-%dT%H:%M:%SZ%z'
_SNT_CACHE = {}


def read_yaml(yml_filename: str) -> Dict:
    """Read yaml file and return dictionary"""
    with open(yml_filename, 'r') as f:
        ymldict = yaml.safe_load(f)
    return ymldict


def verify_unit_object(_units):
    """Raise error if _units is not processable by pint package"""
    try:
        ureg.Unit(_units)
    except UndefinedUnitError as e:
        raise UndefinedUnitError(f'Units cannot be understood using pint_xarray package: {_units}. --> {e}')


def xmlconvention2dict(xml_filename: Path) -> Tuple[dict, dict]:
    """reads an xml convention xml file and returns data and meta dictionaries"""
    tree = ET.parse(xml_filename)
    root = tree.getroot()
    standard_names = {}
    meta = {'name': root.tag}
    for r in root:
        if r.tag != 'entry':
            meta.update({r.tag: r.text})

    for child in root.iter('entry'):
        standard_names[child.attrib['id']] = {}
        for c in child:
            standard_names[child.attrib['id']][c.tag] = c.text
    return standard_names, meta


def meta_from_xml(xml_filename):
    _dict, meta = xmlconvention2dict(xml_filename)
    meta.update(dict(table_dict=_dict))
    return meta


def _units_power_fix(_str: str):
    """Fixes strings like 'm s-1' to 'm s^-1'"""
    s = re.search('[a-zA-Z][+|-]', _str)
    if s:
        return _str[0:s.span()[0] + 1] + '^' + _str[s.span()[1] - 1:]
    return _str


@register_standard_attribute(H5Group, name='standard_name')
class StandardNameGroupAttribute:
    def set(self, new_standard_name):
        raise RuntimeError('A standard name attribute is used for datasets only')


@register_standard_attribute(H5Dataset, name='standard_name')
class StandardNameDatasetAttribute:
    """Standard Name attribute"""

    def set(self, new_standard_name):
        """Writes attribute standard_name if passed string is not None.
        The rules for the standard_name is checked before writing to file."""
        if new_standard_name:
            if self.standard_name_table.check_name(new_standard_name):
                if STRICT:
                    if 'units' in self.attrs:
                        self.standard_name_table.check_units(new_standard_name,
                                                             self.attrs['units'])
                self.attrs.create('standard_name', new_standard_name)

    def get(self):
        """Return the standardized name of the dataset. The attribute name is `standard_name`.
        Returns `None` if it does not exist."""
        val = self.attrs.get('standard_name', None)
        if val is None:
            return None
        return self.standard_name_table[val]

    def delete(self):
        """Delete attribute"""
        self.attrs.__delitem__('standard_name')


@dataclass
class StandardName:
    """basic stndardized name class"""
    name: str
    description: Union[str, None]
    canonical_units: Union[str, None]
    convention: "StandardNameTable"

    def __post_init__(self):
        if self.canonical_units:
            self.canonical_units = ureg.Unit(_units_power_fix(self.canonical_units))

    def __format__(self, spec):
        return self.name.__format__(spec)

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other
        else:
            return any([self.name != other.name,
                        self.description != other.description,
                        self.canonical_units != other.canonical_units,
                        self.convention != other.convention])

    def check(self):
        """Run the name check of the convention."""
        self.convention.check_name(self.name)


class StandardNameTable:
    """Base class of Standardized Name Tables"""

    def __init__(self, name: str, table_dict: Union[Dict, None], version_number: int,
                 institution: str, contact: str,
                 last_modified: Union[str, None] = None,
                 valid_characters: str = '', pattern: str = ''):
        self._name = name
        self._version_number = version_number
        self._valid_characters = valid_characters
        self._pattern = pattern
        self._institution = institution
        self.contact = contact
        self._xml_filename = None
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
                            f'StandardNameTable or dict.')
        if not self.has_valid_structure():
            raise KeyError(f'Invalid dictionary structure. Each entry must contain "description" and '
                           '"canonical units"')

    @property
    def names(self):
        return list(self._dict.keys())

    @property
    def versionname(self):
        return f'{self._name}-v{self._version_number}'

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
    def pattern(self):
        return self._pattern

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
        if not isinstance(contact, str):
            raise ValueError(f'Invalid type for contact Expcting str but got {type(contact)}')
        if not is_valid_email_address(contact):
            raise EmailError(f'Invalid email address: {contact}')
        self._contact = contact

    def __repr__(self) -> str:
        if self._name is None:
            name = self.__class__.__name__
        else:
            name = self._name
        if self._version_number is None:
            version = 'None'
        else:
            version = self._version_number
        return f"{name} (version number: {version})"

    def __str__(self):
        return self.name

    def __getitem__(self, item) -> StandardName:
        if item in self._dict:
            return StandardName(item, self._dict[item]['description'], self._dict[item]['canonical_units'],
                                convention=self)
        else:
            # return a standard name that is not in the table
            return StandardName(item, None, None, convention=self)

    def __contains__(self, item):
        return item in self._dict

    def __eq__(self, other):
        eq1 = self._dict == other._dict
        eq2 = self.versionname == other.versionname
        return eq1 and eq2

    def __neg__(self, other):
        return not self.__eq__(other)

    def compare_versionname(self, other):
        """Compare versionname"""
        return self.versionname == other.versionname

    def set(self, name: str, description: str, canonical_units: str):
        """Sets the value of a standardized name"""
        if name in self._dict:
            raise StandardNameError(f'name "{name}" already exists in table. Use modify() '
                                    f'to change the content')
        verify_unit_object(canonical_units)
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

    def get_table(self, sort_by: str = 'name', maxcolwidths=None) -> str:
        """string representation of the convention in form of a table"""
        if self._name is None:
            name = self.__class__.__name__
        else:
            name = self._name
        if self._version_number:
            version = self._version_number
        else:
            version = 'None'
        df = pd.DataFrame(self._dict).T
        if sort_by.lower() in ('name', 'names', 'standard_name', 'standard_names'):
            sorted_df = df.sort_index()
        elif sort_by.lower() in ('units', 'unit', 'canoncial_units'):
            sorted_df = df.sort_values('canonical_units')
        else:
            sorted_df = df
        _table = tabulate(sorted_df, headers='keys', tablefmt='psql', maxcolwidths=maxcolwidths)
        return f"{name} (version: {version})\n{_table}"

    def sdump(self, sort_by: str = 'name', maxcolwidths=None) -> None:
        """Dumps (prints) the content as string"""
        print(self.get_table(sort_by=sort_by, maxcolwidths=maxcolwidths))

    def dump(self, sort_by: str = 'name', **kwargs):
        """pretty representation of the table for jupyter notebooks"""
        df = pd.DataFrame(self._dict).T
        if sort_by.lower() in ('name', 'names', 'standard_name', 'standard_names'):
            display(HTML(df.sort_index().to_html(**kwargs)))
        elif sort_by.lower() in ('units', 'unit', 'canoncial_units'):
            display(HTML(df.sort_values('canonical_units').to_html(**kwargs)))
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
        """Return a copy of the object"""
        return StandardNameTable(self._dict)

    def update(self, data: Union[Dict, "StandardNameTable"]):
        if isinstance(data, StandardNameTable):
            self._dict.update(data)
        elif isinstance(data, dict):
            self._dict.update(data)

    @staticmethod
    def from_xml(xml_filename) -> "StandardNameTable":
        """read from xml file"""
        meta = meta_from_xml(xml_filename)
        snt = StandardNameTable(**meta)
        snt._xml_filename = xml_filename
        return snt

    @staticmethod
    def from_yaml(yml_filename) -> "StandardNameTable":
        """alias method of from_yml"""
        return StandardNameTable.from_yml(yml_filename)

    @staticmethod
    def from_yml(yml_filename) -> "StandardNameTable":
        """read from yaml file"""
        ymldict = read_yaml(yml_filename)
        return StandardNameTable(**ymldict)

    @staticmethod
    def from_web(url: str, known_hash: str = None,
                 valid_characters: str = '[^a-zA-Z0-9_]',
                 pattern: str = '^[0-9 ].*'):
        """Init from an online resource. Provide a hash is recommended. For more info
        see documentation of pooch.retrieve()"""
        try:
            import pooch
        except ImportError:
            raise ImportError(f'Package "pooch" is needed to download the file cf-standard-name-table.xml')
        file_path = pooch.retrieve(
            url=url,
            known_hash=known_hash,
        )
        snt = StandardNameTable.from_xml(file_path)
        snt._valid_characters = valid_characters
        snt._pattern = pattern
        return snt

    @staticmethod
    def from_versionname(version_name: str):
        """reads the table from an xml file stored in this package"""
        vn_split = version_name.rsplit('-v', 1)
        if len(vn_split) != 2:
            raise ValueError(f'Unexpected version name: {version_name}. Expecting syntax NAME-v999')
        return StandardNameTable.load_registered(version_name)

    def to_xml(self, xml_filename: Path, datetime_str=None, parents=True) -> Path:
        """Save the convention in a XML file"""
        if not xml_filename.parent.exists() and parents:
            xml_filename.parent.mkdir(parents=parents)
        if datetime_str is None:
            datetime_str = '%Y-%m-%d_%H:%M:%S'
        last_modified = datetime.now().strftime(datetime_str)

        xml_parent = xml_filename.parent
        xml_name = xml_filename.name
        xml_translation_filename = xml_parent / 'translation' / xml_name
        if not xml_translation_filename.parent.exists():
            xml_translation_filename.parent.mkdir(parents=True)

        return dict2xml(filename=xml_filename,
                        name=self.name,
                        dictionary=self._dict,
                        version_number=self.version_number,
                        contact=self.contact,
                        institution=self.institution,
                        last_modified=last_modified)

    def to_yml(self, *args, **kwargs) -> Path:
        """alias of to_yaml()"""
        return self.to_yaml(*args, **kwargs)

    def to_yaml(self, yml_filename: Path, datetime_str=None, parents=True) -> Path:
        """Save the convention in a XML file"""
        yml_filename = Path(yml_filename)
        if not yml_filename.parent.exists() and parents:
            yml_filename.parent.mkdir(parents=parents)
        if datetime_str is None:
            datetime_str = '%Y-%m-%d_%H:%M:%S'
        last_modified = datetime.now().strftime(datetime_str)
        with open(yml_filename, 'w') as f:
            yaml.dump({'name': self.name}, f)
            yaml.dump({'version_number': self.version_number}, f)
            yaml.dump({'institution': self.institution}, f)
            yaml.dump({'contact': self.contact}, f)
            yaml.dump({'valid_characters': self.valid_characters}, f)
            yaml.dump({'pattern': self.pattern}, f)
            yaml.dump({'last_modified': last_modified}, f)
            yaml.dump({'table_dict': self._dict}, f)
        return yml_filename

    def check_name(self, name, strict: bool = None) -> bool:
        """Verifies general requirements like lower-case writing and no
        invalid character exist in the name.
        If strict is True, it is further checked whether the name exists
        in the standard name table. This is a global setting which can be changed
        in `conventions.identifier.STRICT`"""
        if strict is None:
            strict = STRICT

        if not len(name) > 0:
            raise StandardNameError(f'Name too short!')

        if name[0] == ' ':
            raise StandardNameError(f'Name must not start with a space!')

        if name[-1] == ' ':
            raise StandardNameError(f'Name must not end with a space!')

        if re.sub(self.valid_characters, '', name) != name:
            raise StandardNameError(f'Invalid special characters in name "{name}": Only "{self.valid_characters}" '
                                    'is allowed.')

        if self.pattern != '' and self.pattern is not None:
            if re.match(self.pattern, name):
                raise StandardNameError(f'Name must not start with a number!')

        if strict:
            if self._dict:
                if name not in self._dict:
                    raise StandardNameError(f'Standardized name "{name}" not in '
                                            'name table')
        return True

    def check_units(self, name, units) -> bool:
        """Raises an error if units is wrong. """
        self.check_name(name, strict=True)  # will raise an error if name not in self._dict
        if name in self._dict:
            if not equal_base_units(_units_power_fix(self._dict[name]['canonical_units']), units):
                raise StandardNameError(f'Unit of standard name "{name}" not as expected: '
                                        f'"{units}" != "{self[name].canonical_units}"')
        return True

    def check_file(self, filename, recursive: bool = True, raise_error: bool = True):
        """Check file for standard names"""
        with h5py.File(filename) as h5:
            self.check_grp(h5['/'], recursive=recursive, raise_error=raise_error)

    def check_grp(self, h5grp: h5py.Group, recursive: bool = True, raise_error: bool = True):
        """Check group dataset """

        def _check_ds(name, node):
            if isinstance(node, h5py.Dataset):
                if 'standard_name' in node.attrs:
                    units = node.attrs['units']
                    try:
                        self.check_units(node.attrs['standard_name'], units=units)
                    except StandardNameError as e:
                        if raise_error:
                            raise StandardNameError(e)
                        else:
                            print(f' > ds: {node.name}: {e}')

        h5grp.visititems(_check_ds)

    def register(self, overwrite: bool = False) -> None:
        """Register the standard name table under its versionname."""
        trg = user_dirs['standard_name_tables'] / f'{self.versionname}.yml'
        if trg.exists() and not overwrite:
            raise FileExistsError(f'Standard name table {self.versionname} already exists!')
        self.to_yaml(trg)

    @staticmethod
    def load_registered(name: str) -> 'StandardNameTable':
        """Load from user data dir"""
        # search for names:
        candidates = list(user_dirs['standard_name_tables'].glob(f'{name}.yml'))
        if len(candidates) == 1:
            return StandardNameTable.from_yml(candidates[0])
        list_of_reg_names = [snt.versionname for snt in StandardNameTable.get_registered()]
        raise FileNotFoundError(f'File {name} could not be found or passed name was not unique. '
                                f'Registered tables are: {list_of_reg_names}')

    @staticmethod
    def get_registered() -> List["StandardNameTable"]:
        """Return sorted list of standard names files"""
        return [StandardNameTable.from_yaml(f) for f in sorted(user_dirs['standard_name_tables'].glob('*'))]

    @staticmethod
    def print_registered() -> None:
        """Return sorted list of standard names files"""
        for f in StandardNameTable.get_registered():
            print(f' > {f.versionname}')


class StandardNameTableTranslation:
    """Translation Interface which translates a name into a standard name based on a
    translation dictionary"""
    raise_error: bool = False

    def __init__(self, translation_dict: Dict, snt: StandardNameTable):
        self.translation_dict = translation_dict
        self.snt = snt

    def __getitem__(self, item):
        return self.translate(item)

    def __contains__(self, item):
        return item in self.translation_dict

    @property
    def name(self) -> str:
        """Equal to name of snt"""
        return self.snt.name

    @property
    def versionname(self) -> str:
        """Equal to versionname of snt"""
        return self.snt.versionname

    @staticmethod
    def from_yaml(yaml_filename: pathlib.Path) -> "StandardNameTableTranslation":
        """Init Translation from  yaml file"""
        return StandardNameTableTranslation(**read_yaml(yaml_filename))

    def to_yaml(self, yaml_filename: pathlib.Path, parents: bool = True,
                overwrite: bool = False) -> pathlib.Path:
        """Dump translation dict to yaml"""
        yml_filename = pathlib.Path(yaml_filename)
        if yml_filename.exists() and not overwrite:
            raise FileExistsError('File exists and overwrite is False')
        if not yml_filename.parent.exists() and parents:
            yml_filename.parent.mkdir(parents=parents)

        with open(yml_filename, 'w') as f:
            yaml.dump({'snt': self.snt.versionname,
                       'translation_dict': self.translation_dict}, f)

    def translate(self, name: str) -> Union[str, None]:
        """Translate name into a standard."""
        try:
            return self.translation_dict[name]
        except KeyError:
            return None

    def verify(self) -> bool:
        """Verifies if all values re part of the standard name table passed"""
        for v in self.translation_dict.values():
            if v not in self.snt._dict:
                raise KeyError(f'{v} is not part of the standard name table {self.snt.versionname}')
        return True

    def register(self, overwrite: bool = False) -> None:
        """Register the standard name table under its versionname."""
        trg = user_dirs['standard_name_table_translations'] / f'{self.versionname}.yml'
        if trg.exists() and not overwrite:
            raise FileExistsError(f'Standard name translation {self.versionname} already exists!')
        self.to_yaml(trg)

    @staticmethod
    def load_registered(versionname: str) -> 'StandardNameTableTranslation':
        """Load from user data dir"""
        # search for names:
        candidates = list(user_dirs['standard_name_table_translations'].glob(f'{versionname}.yml'))
        if len(candidates) == 1:
            return StandardNameTableTranslation.from_yaml(candidates[0])
        list_of_reg_names = [snt.versionname for snt in StandardNameTableTranslation.get_registered()]
        raise FileNotFoundError(f'File {versionname} could not be found or passed name was not unique. '
                                f'Registered tables are: {list_of_reg_names}')


def merge(list_of_snt: List[StandardNameTable], name: str, version_number: int, institution: str,
          contact: str) -> StandardNameTable:
    """Merge multiple standard name tables to a new one"""
    if len(list_of_snt) < 2:
        raise ValueError('List of standard name tables must at least contain two entries.')
    _dict0 = list_of_snt[0]._dict
    for snt in list_of_snt[1:]:
        _dict0.update(snt._dict)
    return StandardNameTable(name=name, table_dict=_dict0,
                             version_number=version_number,
                             institution=institution, contact=contact)


Empty_Standard_Name_Table = StandardNameTable(name='EmptyStandardNameTable',
                                              table_dict={},
                                              version_number=0,
                                              institution=None,
                                              contact='none@none.none',
                                              last_modified=None,
                                              valid_characters='')


@register_standard_attribute(H5Dataset, name='standard_name_table')
@register_standard_attribute(H5Group, name='standard_name_table')
class StandardNameTableAttribute:
    """Standard Name Table attribute"""

    def set(self, snt: Union[str, StandardNameTable]):
        """Set (write to root group) Standard Name Table

        Raises
        ------
        StandardNameTableError
            If no write intent on file.

        """
        if isinstance(snt, str):
            StandardNameTable.print_registered()
            snt = StandardNameTable.load_registered(snt)
        if self.mode == 'r':
            raise StandardNameTableError('Cannot write Standard Name Table (no write intent on file)')
        self.rootparent.attrs.modify(config.standard_name_table_attribute_name, snt.versionname)
        _SNT_CACHE[self.id.id] = snt

    def get(self) -> StandardNameTable:
        """Get (if exists) Standard Name Table from file

        Raises
        ------
        KeyError
            If cannot load SNT from registration.
        """
        snt = self.rootparent.attrs.get(config.standard_name_table_attribute_name, None)
        if snt is not None:
            try:
                return _SNT_CACHE[self.file.id.id]
            except KeyError:
                return StandardNameTable.load_registered(
                    self.rootparent.attrs[config.standard_name_table_attribute_name])
        return Empty_Standard_Name_Table

    def delete(self):
        """Delete standard name table from root attributes"""
        self.attrs.__delitem__(config.standard_name_table_attribute_name)
