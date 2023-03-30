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
import h5py
import json
import os
import pandas as pd
import pathlib
import re
import warnings
import xml.etree.ElementTree as ET
import yaml
from IPython.display import display, HTML
from datetime import datetime
from enum import Enum
from omegaconf import DictConfig, OmegaConf
from pathlib import Path
from pint.errors import UndefinedUnitError
from typing import Dict, Union, List, Tuple

from ._logger import logger
from .standard_attribute import StandardAttribute
from .utils import equal_base_units, is_valid_email_address, dict2xml, get_similar_names_ratio
from .._config import ureg
from .._user import UserDir
from ..utils import generate_temporary_filename

try:
    from tabulate import tabulate
    import requests
    import xmltodict
except ImportError:
    raise ImportError('Please install tabulate, requests and xmltodict to use this standard names')

STRICT = True

CF_DATETIME_STR = '%Y-%m-%dT%H:%M:%SZ%z'
_SNT_CACHE = {}


class StandardNameError(Exception):
    """Exception class for error associated with standard name usage"""


class StandardNameTableError(Exception):
    """Exception class for error associated with standard name usage"""


class StandardNameTableError(Exception):
    """Exception class for StandardName Tables"""


class StandardNameTableVersionError(Exception):
    """Incompatible Errors"""


class EmailError(ValueError):
    """Wrong Email Error"""


def verify_unit_object(_units):
    """Raise error if _units is not processable by pint package"""
    try:
        ureg.Unit(_units)
    except UndefinedUnitError as e:
        raise UndefinedUnitError(f'Units cannot be understood using pint_xarray package: {_units}. --> {e}')


def xmlsnt2dict(xml_filename: Path) -> Tuple[dict, dict]:
    """reads an SNT as xml file and returns data and meta dictionaries"""
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


def _units_power_fix(_str: str):
    """Fixes strings like 'm s-1' to 'm s^-1'"""
    s = re.search('[a-zA-Z][+|-]', _str)
    if s:
        return _str[0:s.span()[0] + 1] + '^' + _str[s.span()[1] - 1:]
    return _str


class StandardName:
    """Standard name class

    Parameters
    ----------
    name : str
        standard name
    canonical_units : str
        The canonical units. The package pint is used. If the units are not valid, an error is raised.
    description : str, optional=None
        description, by default None
    snt : str | StandardNameTable, optional=None
        Standard Name Table. If None, a minimal SNT is used, by default None

        .. note::

            If a standard name table is provided, the standard name is checked against the table.


    Examples
    --------
    >>> from h5rdmtoolbox.conventions.standard_name import StandardName
    >>> StandardName('x_wind', 'm/s', 'x wind component')
    <StandardName: x_wind [m/s] | SNT: None | desc: x wind component>
    """

    def __init__(self,
                 name,
                 canonical_units: str,
                 description: str = None,
                 snt: Union[str, "StandardNameTable"] = None
                 ):
        self.name = name
        self.description = description
        self.canonical_units = f'{ureg.Unit(_units_power_fix(canonical_units))}'
        if snt is None:
            # select a "minimal snt", which has no valid online resource but allows performing checks
            snt = MinimalStandardNameTable(None, {})
        else:
            # perform a check as standard name table is provided:
            snt.check_name(name)
        self.snt = snt

    def __repr__(self):
        return f'<StandardName: {self.name} [{self.canonical_units}] | SNT: {self.snt.name} | desc: {self.description}>'

    def __eq__(self, other):
        if isinstance(other, StandardName):
            return all([self.name == other.name,
                        self.description == other.description,
                        self.canonical_units == other.canonical_units,
                        self.snt == other.snt])
        return self.name == other

    def __ne__(self, other):
        """Not equal"""
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.name)

    @property
    def units(self) -> str:
        """alias for canonical_units"""
        return self.canonical_units

    @staticmethod
    def from_snt(name, snt: "StandardNameTable") -> "StandardName":
        """Initialize the StandardName object from StandardNameTable object

        Parameters
        ----------
        name : str
            The name of the standard name
        snt : StandardNameTable
            The StandardNameTable object from which the standard name is initialized.
            The name must be contained in the Standard Name Table.

        Returns
        -------
        StandardName

        Raises
        ------
        KeyError
            If the name is not contained in the Standard Name Table.

        """
        if name not in snt:
            raise KeyError(f'Name {name} not found in standard name table {snt.name}. Cannot initialize StandardName.')
        description = snt[name]['description']
        canonical_units = snt[name]['canonical_units']
        return StandardName(name, canonical_units, description, snt)

    def check_syntax(self):
        """Run the name check of the standard name."""
        return self.snt.check_syntax(self)


# @dataclass
# class StandardName:
#     """basic standardized name class"""
#     name: str
#     description: Union[str, None]
#     canonical_units: Union[str, None]
#     snt: "StandardNameTable"
#
#     def __post_init__(self):
#         if self.canonical_units:
#             self.canonical_units = f'{ureg.Unit(_units_power_fix(self.canonical_units))}'
#         self.name = str(self.name)
#
#     def __format__(self, spec):
#         return self.name.__format__(spec)
#
#     def __str__(self):
#         return self.name
#
#     def __eq__(self, other):
#         if isinstance(other, str):
#             return self.name == other
#         return all([self.name == other.name,
#                     self.description == other.description,
#                     self.canonical_units == other.canonical_units,
#                     self.snt == other.snt])
#
#     def check(self):
#         """Run the name check of the standard name."""
#         self.snt.check_name(self.name)
#


class StandardNameTableStoreOption(Enum):
    """Enum class to define how to store standard name tables in files"""
    url = 1
    dict = 2
    versionname = 3
    none = 4


def url_exists(url: str) -> bool:
    """Return True if URL exist"""
    response = requests.head(url, timeout=2)
    return response.status_code == 200


config = {'valid_characters': '[^a-zA-Z0-9_]', 'pattern': '^[0-9 ].*'}


class MinimalStandardNameTable:
    """Minimal version of a standard name table, which only contains name, and the table but no contanct or
    versioning information"""

    def __init__(self, name, table,
                 valid_characters: Union[str, None] = None,
                 pattern: Union[str, None] = None):
        self._name = name
        self._table = table
        if valid_characters is None:
            valid_characters = config['valid_characters']
        self._valid_characters = valid_characters
        if pattern is None:
            pattern = config['pattern']
        self._pattern = pattern

        if self._table:
            self.check_table()

    def __eq__(self, other):
        """Check if two standard name tables are equal"""
        return all([self.name == other.name,
                    self.table == other.table, ])

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def name(self) -> str:
        """Return name of standard name table"""
        return self._name

    @property
    def table(self) -> Union[Dict, DictConfig]:
        """Return table as dictionary"""
        if self._table is None:
            return {}
        if isinstance(self._table, DictConfig):
            return OmegaConf.to_container(self._table)
        return self._table  # assuming it is a dict

    @property
    def names(self):
        """Return keys of table"""
        return [*list(self.table.keys()), *list(self.alias.keys())]

    @property
    def valid_characters(self) -> str:
        """Return valid characters of the snt"""
        return self._valid_characters

    @property
    def pattern(self) -> str:
        """Return valid pattern of the snt"""
        return self._pattern

    def check_table(self):
        """Check if table is valid"""
        for v in self._table.values():
            if isinstance(v, (dict, DictConfig)):
                if 'description' not in v:
                    raise KeyError(f'Keyword "description" missing: {v}')
                if 'canonical_units' not in v:
                    raise KeyError(f'Keyword "canonical_units" missing: {v}')
            else:
                raise TypeError(f'Content of Table is unexpected: {self._table}')

    def set(self, name: str, description: str, canonical_units: str):
        """Set the value of a standard name"""
        if name in self.table:
            raise StandardNameError(f'name "{name}" already exists in table. Use modify() '
                                    'to change the content')
        verify_unit_object(canonical_units)
        self._table[name] = dict(description=description, canonical_units=canonical_units)

    def modify(self, name: str, description: str, canonical_units: str):
        """Modify a standard name or creates one if non-existing"""
        if name not in self.table:
            if not description or not canonical_units:
                raise ValueError(f'Name {name} does not exist yet. You must provide string values '
                                 'for both description and canonical_units')
            self.table[name] = dict(description=description, canonical_units=canonical_units)
        else:
            if description:
                self.table[name]['description'] = description
            if canonical_units:
                self.table[name]['canonical_units'] = canonical_units

    def rename(self, name, new_name) -> None:
        """Rename an existing standard name. Make sure that description and unit is still
        valid as this only renames the name of the standard name"""
        if name not in self:
            raise KeyError(f'"{name}" does not exist in table')
        existing_sn = self.table.get(name)
        self.set(new_name, **existing_sn)
        del self._table[name]

    def check_syntax(self, name: str) -> bool:
        """Checks if the syntax of the name is correct according to the syntax rules of the StandardNameTable."""
        if not len(name) > 0:
            raise StandardNameError('Name too short!')

        if name[0] == ' ':
            raise StandardNameError('Name must not start with a space!')

        if name[-1] == ' ':
            raise StandardNameError('Name must not end with a space!')

        if re.sub(self.valid_characters, '', name) != name:
            raise StandardNameError('Invalid special characters in name '
                                    f'"{name}": Only "{self.valid_characters}" '
                                    'is allowed.')

        if self.pattern != '' and self.pattern is not None:
            if re.match(self.pattern, name):
                raise StandardNameError('Name must not start with a number!')
        return True

    def check_name(self, name, strict: bool = None) -> bool:
        """Verifies general requirements like lower-case writing and no
        invalid character exist in the name.
        If strict is True, it is further checked whether the name exists
        in the standard name table. This is a global setting which can be changed
        in `conventions.standard_attributes.standard_name.STRICT`"""
        self.check_syntax(name)
        if strict:
            if name not in self.table:
                if name not in self.alias:
                    err_msg = f'Standard name "{name}" not in name table {self.versionname}.'
                    if self.table:
                        similar_names = self.find_similar_names(name)
                        if similar_names:
                            err_msg += f'\nSimilar names are {similar_names}'
                        raise StandardNameError(err_msg)
        return True


class StandardNameTable(MinimalStandardNameTable):
    """Minimal version of a StandardNameTable.

    Parameters
    ----------
    name: str
        Name of the standard name table
    table: DictConfig or Dict
        Dictionary containing the standard names
    version_number: int
        Version number of the standard name table
    institution: str
        Institution that maintains the standard name table
    contact: str
        Contact person of the institution

        .. note::

            The email address is validated on common email address patterns.

    last_modified: str
        Date of last modification of the standard name table
    valid_characters: str
        String containing all valid characters for standard names, e.g. \"[\^a-zA-Z0-9\_]"
    pattern: str
        Regular expression pattern that standard names must match, e.g. \"^[0-9 ].*"
    url: str
        URL to the standard name table
    alias: Dict
        Dictionary containing aliases for standard names

    Examples
    --------
    >>> from h5rdmtoolbox.conventions.standard_name import StandardNameTable
    >>> sc = StandardNameTable(
    >>>             name='Test_SNC',
    >>>             table={},
    >>>             version_number=1,
    >>>             contact='contact@python.com',
    >>>             institution='my_institution'
    >>>             )
    >>> sc
    Test_SNC (version number: 1)

    """
    STORE_AS: StandardNameTableStoreOption = StandardNameTableStoreOption.none

    def __init__(self,
                 name: str,
                 table: Union[DictConfig, Dict, None],
                 version_number: int,
                 institution: str,
                 contact: str,
                 last_modified: Union[str, None] = None,
                 valid_characters: str = '',
                 pattern: str = '',
                 url: str = None,
                 alias: Dict = None):
        super().__init__(name, table, valid_characters, pattern)
        self._version_number = version_number
        self._institution = institution
        self.contact = contact
        self._filename = None
        self.url = url
        self._alias = alias
        if last_modified is None:
            now = datetime.now()
            self._last_modified = now.strftime(CF_DATETIME_STR)
        else:
            self._last_modified = last_modified
        self._alias = alias

    @property
    def alias(self) -> Union[Dict, DictConfig]:
        """Return alias dictionary"""
        if self._alias is None:
            return {}
        if isinstance(self._alias, DictConfig):
            return OmegaConf.to_container(self._alias)
        return self._alias  # assuming it is a dict

    @property
    def versionname(self) -> str:
        """Return version name which is constructed like this: <name>-v<version_number>"""
        return f'{self._name}-v{self._version_number}'

    @property
    def contact(self) -> str:
        """Return contact (email)"""
        return self._contact

    @contact.setter
    def contact(self, contact):
        """Set contact (email)"""
        if not isinstance(contact, str):
            raise ValueError(f'Invalid type for contact Expcting str but got {type(contact)}')
        if not is_valid_email_address(contact):
            raise EmailError(f'Invalid email address: {contact}')
        self._contact = contact

    @property
    def last_modified(self) -> str:
        """Return when the snt was last modified"""
        return self._last_modified

    @property
    def institution(self) -> str:
        """Return the institution at which the snt was created"""
        return self._institution

    @property
    def version_number(self) -> int:
        """Return the version number of the snt"""
        return self._version_number

    @property
    def filename(self) -> Union[None, pathlib.Path]:
        """Return the filename if exists else return None"""
        return self._filename

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
        if item in self.table:
            return StandardName(name=item,
                                canonical_units=self.table[item]['canonical_units'],
                                description=self.table[item]['description'],
                                snt=self)
        if item in self.alias:
            return StandardName(item,
                                self.table[self.alias[item]]['canonical_units'],
                                self.table[self.alias[item]]['description'],
                                snt=self)
        # return a standard name that is not in the table
        return StandardName(item, None, None, snt=self)

    def __contains__(self, item):
        return item in self.table

    def __eq__(self, other):
        return all([self.name == other.name,
                    self.contact == other.contact,
                    self.institution == other.institution,
                    self.table == other.table,
                    self.versionname == other.versionname])

    def compare_versionname(self, other):
        """Compare versionname"""
        return self.versionname == other.versionname

    def get_table(self, sort_by: str = 'name', maxcolwidths=None) -> str:
        """string representation of the SNT in form of a table"""
        if self._name is None:
            name = self.__class__.__name__
        else:
            name = self._name
        if self._version_number:
            version = self._version_number
        else:
            version = 'None'
        df = pd.DataFrame(self.table).T
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
        df = pd.DataFrame(self.table).T
        if sort_by.lower() in ('name', 'names', 'standard_name', 'standard_names'):
            display(HTML(df.sort_index().to_html(**kwargs)))
        elif sort_by.lower() in ('units', 'unit', 'canoncial_units'):
            display(HTML(df.sort_values('canonical_units').to_html(**kwargs)))
        else:
            raise ValueError(f'Invalid value for sortby: {sort_by}')

    def has_valid_structure(self) -> bool:
        """verifies the structure of the standard name dictionary"""
        if self.table:
            for v in self.table.values():
                if isinstance(v, str):
                    return False
                if 'description' not in v.keys() and 'canonical_units' not in v.keys():
                    return False
        return True

    def copy(self):
        """Return a copy of the object"""
        return StandardNameTable(name=self.name,
                                 table=self.table,
                                 version_number=self.version_number,
                                 institution=self.institution,
                                 contact=self.contact,
                                 last_modified=self.last_modified,
                                 pattern=self.pattern,
                                 url=self.url,
                                 alias=self.alias)

    def update(self, data: Union[Dict, "StandardNameTable"]):
        if isinstance(data, StandardNameTable):
            self.table.update(data)
        elif isinstance(data, dict):
            self.table.update(data)

    @staticmethod
    def from_xml(xml_filename, name: str = None) -> "StandardNameTable":
        """Create a StandardNameTable from an xml file

        Parameters
        ----------
        xml_filename : str
            Filename of the xml file
        name : str, optional
            Name of the StandardNameTable, by default None. If None, the name of the xml file is used.

        Returns
        -------
        snt: StandardNameTable
            The StandardNameTable object

        Raises
        ------
        FileNotFoundError
            If the xml file does not exist
        """
        with open(xml_filename, 'r', encoding='utf-8') as file:
            my_xml = file.read()
        xmldict = xmltodict.parse(my_xml)
        _name = list(xmldict.keys())[0]
        if name is None:
            name = _name
        data = xmldict[_name]

        version_number = data.get('version_number', None)
        last_modified = data.get('last_modified', None)
        institution = data.get('institution', None)
        contact = data.get('contact', None)
        _alias = data.get('alias', None)
        valid_characters = data.get('valid_characters', None)
        pattern = data.get('pattern', None)

        table = {}
        for entry in data['entry']:
            table[entry.pop('@id')] = entry

        alias = {}
        if _alias:
            for aliasentry in _alias:
                k, v = list(aliasentry.values())
                alias[k] = v

        snt = StandardNameTable(name, table=table,
                                version_number=version_number,
                                institution=institution,
                                contact=contact,
                                valid_characters=valid_characters,
                                pattern=pattern,
                                last_modified=last_modified,
                                alias=alias
                                )
        snt._filename = xml_filename
        return snt

    @staticmethod
    def from_yaml(yaml_filename) -> "StandardNameTable":
        """Create a StandardNameTable from a yaml file

        Parameters
        ----------
        yaml_filename : str
            Filename of the yaml file

        Returns
        -------
        snt: StandardNameTable
            The StandardNameTable object
        """
        try:
            oc = OmegaConf.load(yaml_filename)
        except yaml.composer.ComposerError:
            with open(yaml_filename, 'r') as f:
                _dict = {}
                for d in yaml.full_load_all(f):
                    _dict.update(d)
                oc = DictConfig(_dict)
        snt = StandardNameTable(**oc)
        snt._filename = yaml_filename
        return snt

    @staticmethod
    def from_web(url: str, known_hash: str = None,
                 name: str = None,
                 valid_characters: str = None,
                 pattern: str = None):
        """Create a StandardNameTable from an online resource.
        Provide a hash is recommended.

        Parameters
        ----------
        url : str
            URL of the file to download
        known_hash : str, optional
            Hash of the file, by default None
        name : str, optional
            Name of the StandardNameTable, by default None. If None, the name of the xml file is used.
        valid_characters : str, optional
            Regular expression for valid characters. If None, the default value from the config file is used.
        pattern : str, optional
            Regular expression for valid standard names. If None, the default value from the config file is used.

        Returns
        -------
        snt: StandardNameTable
            The StandardNameTable object

        Notes
        -----
        This method requires the package pooch to be installed.

        .. seealso::

            For more info see documentation of `pooch.retrieve()`

        """
        try:
            import pooch
        except ImportError:
            raise ImportError('Package "pooch" is needed to download the file cf-standard-name-table.xml')
        file_path = pooch.retrieve(
            url=url,
            known_hash=known_hash,
        )
        file_path = pathlib.Path(file_path)
        if file_path.suffix == '.xml':
            snt = StandardNameTable.from_xml(file_path, name)
        elif file_path.suffix in ('.yml', '.yaml'):
            snt = StandardNameTable.from_yaml(file_path)
        else:
            raise ValueError(f'Unexpected file suffix: {file_path.suffix}. Expected .xml, .yml or .yaml')
        if valid_characters is None:
            valid_characters = config['valid_characters']
        snt._valid_characters = valid_characters
        if pattern is None:
            pattern = config['pattern']
        snt._pattern = pattern
        snt.url = url
        return snt

    @staticmethod
    def from_gitlab(url: str, project_id: int, ref_name: str,
                    file_path: str, private_token: str = None) -> "StandardNameTable":
        """
        Download a file from a gitlab repository and provide StandardNameTable based on this.

        Parameters
        ----------
        url: str
            gitlab url, e.g. https://gitlab.com
        project_id: str
            ID of gitlab project
        ref_name: str
            Name of branch or tag
        file_path: str
            Path to file in gitlab project
        private_token: str
            Token if porject is not public

        Returns
        -------
        StandardNameTable

        Examples
        --------
        >>> StandardNameTable.from_gitlab(url='https://git.scc.kit.edu',
        >>>                               file_path='open_centrifugal_fan_database-v1.yaml',
        >>>                               project_id='35443',
        >>>                               ref_name='main')


        Notes
        -----
        This method requires the package python-gitlab to be installed.

        Equivalent curl statement:
        curl <url>/api/v4/projects/<project-id>/repository/files/<file-path>/raw?ref\=<ref_name> -o <output-filename>
        """
        try:
            import gitlab
        except ImportError:
            raise ImportError('python-gitlab not installed')
        gl = gitlab.Gitlab(url, private_token=private_token)
        pl = gl.projects.get(id=project_id)

        tmpfilename = generate_temporary_filename(suffix=f".{file_path.rsplit('.', 1)[1]}")
        with open(tmpfilename, 'wb') as f:
            pl.files.raw(file_path=file_path, ref=ref_name, streamed=True, action=f.write)

        if file_path.endswith('.yaml') or file_path.endswith('.yml'):
            return StandardNameTable.from_yaml(tmpfilename)
        if file_path.endswith('.xml'):
            return StandardNameTable.from_xml(tmpfilename)
        raise NotImplementedError(f'Cannot handle file name extension {file_path.rsplit(".", 1)[1]}. '
                                  'Expected yml/yaml or xml')

    @staticmethod
    def from_dict(d: dict) -> "StandardNameTable":
        """Create a StandardNameTable from a dictionary

        Parameters
        ----------
        d : dict
            Dictionary containing the StandardNameTable information

        Returns
        -------
        snt: StandardNameTable
            The StandardNameTable object
        """
        snt = StandardNameTable(**d)
        return snt

    @staticmethod
    def from_versionname(version_name: str):
        """reads the table from an xml file stored in this package"""
        vn_split = version_name.rsplit('-v', 1)
        if len(vn_split) != 2:
            raise ValueError(f'Unexpected version name: {version_name}. Expecting syntax NAME-v999')
        return StandardNameTable.load_registered(version_name)

    def to_dict(self):
        """Dictionary representation of the standard name table"""
        return dict(name=self.name,
                    version_number=self.version_number,
                    institution=self.institution,
                    contact=self.contact,
                    valid_characters=self.valid_characters,
                    pattern=self.pattern,
                    url=self.url,
                    table=self.table,
                    alias=self.alias
                    )

    def to_xml(self, xml_filename: Path, datetime_str=None, parents=True) -> Path:
        """Save the SNT in a XML file"""
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
                        dictionary=self.table,
                        version_number=self.version_number,
                        contact=self.contact,
                        institution=self.institution,
                        last_modified=last_modified)

    def to_yaml(self, yaml_filename: Path, datetime_str=None, parents=True) -> Path:
        """Save the SNT in a YAML file"""
        yaml_filename = Path(yaml_filename)
        if not yaml_filename.parent.exists() and parents:
            yaml_filename.parent.mkdir(parents=parents)
        if datetime_str is None:
            datetime_str = '%Y-%m-%d_%H:%M:%S'
        last_modified = datetime.now().strftime(datetime_str)
        with open(yaml_filename, 'w') as f:
            yaml.dump({'name': self.name}, f)
            yaml.dump({'version_number': self.version_number}, f)
            yaml.dump({'institution': self.institution}, f)
            yaml.dump({'contact': self.contact}, f)
            yaml.dump({'valid_characters': self.valid_characters}, f)
            yaml.dump({'pattern': self.pattern}, f)
            yaml.dump({'last_modified': last_modified}, f)
            f.writelines('---\n')
            yaml.dump({'table': self.table}, f)
        return yaml_filename

    def find_similar_names(self, key):
        """Return similar names to key"""
        return [k for k in [*self.table.keys(), *self.alias.keys()] if get_similar_names_ratio(key, k) > 0.75]

    def check_units(self, name, units) -> bool:
        """Raises an error if units is wrong. """
        self.check_name(name, strict=True)  # will raise an error if name not in self._table
        if name in self.table:
            canonical_units = self.table[name]['canonical_units']
            if canonical_units is None:
                canonical_units = ''
                logger.error('The standard name table has a units with value "None" for name %s. Adjusting to "". '
                             'Consider change the entry', name)
            if not equal_base_units(_units_power_fix(canonical_units), units):
                raise StandardNameError(f'Unit of standard name "{name}" not as expected: '
                                        f'"{units}" != "{canonical_units}"')
        return True

    def check_file(self, filename, recursive: bool = True, raise_error: bool = True):
        """Check file for standard names"""
        with h5py.File(filename) as h5:
            self.check_grp(h5['/'], recursive=recursive, raise_error=raise_error)

    def check_grp(self, h5grp: h5py.Group, recursive: bool = True, raise_error: bool = True):
        """Check group datasets. Run recursively if requested."""

        def _check_ds(name, node):
            if isinstance(node, h5py.Dataset):
                if 'standard_name' in node.attrs:
                    units = node.attrs['units']
                    if units is None:
                        logger.warning(f'Dataset %s has not attribute %s! Assuming it is dimensionless', name, 'units')
                        units = ''
                    try:
                        self.check_units(node.attrs['standard_name'], units=units)
                    except StandardNameError as e:
                        if raise_error:
                            raise StandardNameError(e)
                        else:
                            logger.error(' > ds: %s: %s', node.name, e)

        if recursive:
            h5grp.visititems(_check_ds)
        else:
            _check_ds(None, h5grp)

    def register(self, overwrite: bool = False) -> None:
        """Register the standard name table under its versionname."""
        trg = UserDir['standard_name_tables'] / f'{self.versionname}.yml'
        if trg.exists() and not overwrite:
            raise FileExistsError(f'Standard name table {self.versionname} already exists!')
        self.to_yaml(trg)

    @staticmethod
    def load_registered(name: str) -> 'StandardNameTable':
        """Load from user data dir"""
        # search for names:
        candidates = list(UserDir['standard_name_tables'].glob(f'{name}.yml'))
        if len(candidates) == 1:
            return StandardNameTable.from_yaml(candidates[0])
        if len(candidates) == 0:
            raise FileNotFoundError(f'No file found under the name {name} at this location: '
                                    f'{UserDir["standard_name_tables"]}')
        list_of_reg_names = [snt.versionname for snt in StandardNameTable.get_registered()]
        raise FileNotFoundError(f'File {name} could not be found or passed name was not unique. '
                                f'Registered tables are: {list_of_reg_names}')

    @staticmethod
    def get_registered() -> List["StandardNameTable"]:
        """Return sorted list of standard names files"""
        return [StandardNameTable.from_yaml(f) for f in sorted(UserDir['standard_name_tables'].glob('*'))]

    @staticmethod
    def print_registered() -> None:
        """Return sorted list of standard names files"""
        for f in StandardNameTable.get_registered():
            print(f' > {f.versionname}')


class StandardNameTableTranslation:
    """Translation Interface which translates a name into a standard name based on a
    translation dictionary"""
    raise_error: bool = False

    def __init__(self, application_name: str, translation_dict: Union[Dict, DictConfig]):
        self.application_name = application_name
        self.translation_dict = translation_dict
        self.filename = None

    def __getitem__(self, item):
        return self.translate(item)

    def __contains__(self, item):
        return item in self.translation_dict

    @staticmethod
    def from_yaml(yaml_filename: pathlib.Path) -> "StandardNameTableTranslation":
        """read from yaml file"""

        with open(yaml_filename, 'r') as f:
            g = yaml.safe_load_all(f)
            while True:
                try:
                    splitdata = next(g)
                except StopIteration:
                    break
                if 'table' in splitdata:
                    break

        yaml_filename = pathlib.Path(yaml_filename)
        application_name = yaml_filename.stem.split('-to-', 1)[0]
        if 'table' in splitdata:
            sntt = StandardNameTableTranslation(application_name=application_name,
                                                translation_dict=DictConfig(splitdata['table']))
        else:
            raise KeyError(f'Key "table" not found in yaml file {yaml_filename}. It seems that the yaml file is not '
                           'built as expected.')
        sntt.filename = yaml_filename
        return sntt

    def to_yaml(self, target_dir: pathlib.Path,
                snt: StandardNameTable,
                parents: bool = True,
                overwrite: bool = False) -> pathlib.Path:
        """Dump translation dict to yaml"""
        name = f'{self.application_name}-to-{snt.versionname}.yml'
        yaml_filename = pathlib.Path(target_dir) / name

        if yaml_filename.exists() and not overwrite:
            raise FileExistsError('File exists and overwrite is False')
        if not yaml_filename.parent.exists() and parents:
            yaml_filename.parent.mkdir(parents=parents)

        with open(yaml_filename, 'w') as f:
            yaml.dump({'snt': snt.versionname}, f)
            f.writelines('---\n')
            yaml.dump({'table': self.translation_dict}, f)
        return yaml_filename

    def translate_dataset(self, ds: h5py.Dataset):
        """Based on the dataset basename the attribute standard_name is created"""
        ds_basename = os.path.basename(ds.name)
        ds.attrs['standard_name'] = self.translate(ds_basename)

    def translate_group(self, grp: h5py.Group, rec: bool = True):
        """Translate all datasets in group and recursive if rec==True"""

        def sn_update(name, node):
            """function called when visiting HDF objects"""
            if isinstance(node, h5py.Dataset):
                if node.name in self.translation_dict:
                    sn = self.translation_dict[node.name]
                    node.attrs['standard_name'] = sn
                    logger.debug(f'translate name %s to standard name %s', name, sn)
                elif os.path.basename(node.name) in self.translation_dict:
                    sn = self.translation_dict[os.path.basename(node.name)]
                    node.attrs['standard_name'] = sn
                    logger.debug(f'translate name {name} to standard name {sn}')

        if rec:
            grp.visititems(sn_update)
        else:
            sn_update(grp.name, grp)

    def translate(self, name: str) -> Union[str, None]:
        """Translate name into a standard."""
        try:
            return self.translation_dict[name]
        except KeyError:
            return None

    def verify(self, snt: StandardNameTable) -> bool:
        """Verifies if all values re part of the standard name table passed"""
        for v in self.translation_dict.values():
            if v not in snt.table:
                raise KeyError(f'{v} is not part of the standard name table {snt.versionname}')
        return True

    def register(self, snt: StandardNameTable, overwrite: bool = False) -> None:
        """Register the standard name table under its versionname.

        Parameters
        ----------
        snt: StandardNameTable
            The standard name table to which the translation dicitonary referrs to
        overwrite: bool, default=False
            Whether to overwrite an existing translation name
        """
        self.to_yaml(target_dir=UserDir['standard_name_table_translations'],
                     snt=snt, overwrite=overwrite)

    @staticmethod
    def load_registered(name: str) -> 'StandardNameTableTranslation':
        """Load from user data dir

        source_name:
            Application name from which the names are translated into the standard name table
        """
        # search for names:
        fbasename = f'{name}.yml'
        if (UserDir['standard_name_table_translations'] / fbasename).exists():
            return StandardNameTableTranslation.from_yaml(UserDir['standard_name_table_translations'] / fbasename)

        list_of_reg_names = [fname.stem for fname in UserDir['standard_name_table_translations'].glob('*.y*ml')]
        raise FileNotFoundError(f'File {fbasename} could not be found or passed name was not unique. '
                                f'Registered tables are: {list_of_reg_names}')

    @staticmethod
    def get_registered() -> List["StandardNameTableTranslation"]:
        """Return sorted list of standard names files"""
        return [StandardNameTableTranslation.from_yaml(f) for f in
                sorted(UserDir['standard_name_table_translations'].glob('*.y*ml'))]

    @staticmethod
    def print_registered():
        """Return sorted list of standard names files"""
        for f in StandardNameTableTranslation.get_registered():
            print(f' > {f.filename.stem}')


def merge(list_of_snt: List[StandardNameTable], name: str, version_number: int, institution: str,
          contact: str) -> StandardNameTable:
    """Merge multiple standard name tables to a new one"""
    if len(list_of_snt) < 2:
        raise ValueError('List of standard name tables must at least contain two entries.')
    _dict0 = list_of_snt[0].table
    for snt in list_of_snt[1:]:
        _dict0.update(snt.table)
    return StandardNameTable(name=name, table=_dict0,
                             version_number=version_number,
                             institution=institution, contact=contact)


Empty_Standard_Name_Table = StandardNameTable(name='EmptyStandardNameTable',
                                              table={},
                                              version_number=0,
                                              institution=None,
                                              contact='none@none.none',
                                              last_modified=None,
                                              valid_characters='')


class StandardNameAttribute(StandardAttribute):
    """Standard Name attribute"""

    name = 'standard_name'

    def setter(self, obj, new_standard_name):
        """Writes attribute standard_name if passed string is not None.
        The rules for the standard_name is checked before writing to file."""
        if new_standard_name:
            snt = obj.standard_name_table
            if snt:
                if snt.check_name(new_standard_name):
                    if STRICT:
                        if 'units' in obj.attrs:
                            if not snt.check_units(new_standard_name, obj.attrs['units']):
                                raise ValueError(f'Units {obj.attrs["units"]} failed he unit check of standard name '
                                                 f'table {snt.versionname} for standard name {new_standard_name}')
                    return obj.attrs.create(self.name, str(new_standard_name))
            raise ValueError(f'No standard name table found for {obj.name}')

    def getter(self, obj):
        """Return the standardized name of the dataset. The attribute name is `standard_name`.
        Returns `None` if it does not exist."""
        sn = self.safe_getter(obj)
        if sn is None:
            return None
        return StandardName(name=sn,
                            canonical_units=obj.attrs.get('units', None),
                            snt=obj.attrs.get('standard_name_table', None)
                            )


class StandardNameTableAttribute(StandardAttribute):
    """Standard Name Table attribute"""

    name = 'standard_name_table'

    def setter(self, obj, snt: Union[str, StandardNameTable]):
        """Set (write to root group) Standard Name Table

        Raises
        ------
        StandardNameTableError
            If no write intent on file.

        """
        if isinstance(snt, str):
            StandardNameTable.print_registered()
            if snt[0] == '{':
                json.dumps(snt)
                snt = StandardNameTable.from_dict(json.loads(snt))
            else:
                snt = StandardNameTable.load_registered(snt)
        if obj.mode == 'r':
            raise StandardNameTableError('Cannot write Standard Name Table (no write intent on file)')
        if snt.STORE_AS == StandardNameTableStoreOption.none:
            if snt.url:
                if url_exists(snt.url):
                    self.safe_setter(obj.rootparent, snt.url)
                else:
                    warnings.warn(f'URL {snt.url} not reached. Storing SNT as dictionary instead')
                    self.safe_setter(obj.rootparent, json.dumps(snt.to_dict()))
            else:
                self.safe_setter(obj.rootparent, json.dumps(snt.to_dict()))
        if snt.STORE_AS == StandardNameTableStoreOption.versionname:
            obj.rootparent.attrs.modify(self.name, snt.versionname)
            self.safe_setter(obj.rootparent, snt.versionname)
        elif snt.STORE_AS == StandardNameTableStoreOption.dict:
            self.safe_setter(obj.rootparent, json.dumps(snt.to_dict()))
        elif snt.STORE_AS == StandardNameTableStoreOption.url:
            if snt.url is not None:
                if url_exists(snt.url):
                    obj.rootparent.attrs.modify(self.name, snt.url)
                else:
                    warnings.warn(f'URL {snt.url} not reached. Storing SNT as dictionary instead')
                    obj.rootparent.attrs.modify(self.name, snt.to_dict())
            else:  # else fall back to writing dict. better than versionname because cannot get lost
                obj.rootparent.attrs.modify(self.name,
                                            json.dumps(snt.to_dict()))
        _SNT_CACHE[obj.id.id] = snt

    @staticmethod
    def parse(snt, self=None):
        """Get (if exists) Standard Name Table from file

        Raises
        ------
        KeyError
            If cannot load SNT from registration.
        """
        if self:
            try:
                return _SNT_CACHE[self.file.id.id]
            except KeyError:
                pass  # not cached

        if snt is not None:
            # snt is a string
            if isinstance(snt, dict):
                return StandardNameTable(**snt)
            if snt[0] == '{':
                return StandardNameTable(**json.loads(snt))
            elif snt[0:4] in ('http', 'wwww.'):
                return StandardNameTable.from_web(snt)
            return StandardNameTable.from_versionname(snt)
        return Empty_Standard_Name_Table

    def getter(self, obj) -> StandardNameTable:
        """Get (if exists) Standard Name Table from file"""
        snt = self.safe_getter(obj)

        try:
            return _SNT_CACHE[obj.file.id.id]
        except KeyError:
            pass  # not cached

        if snt is not None:
            # snt is a string
            if isinstance(snt, dict):
                return StandardNameTable(**snt)
            if snt[0] == '{':
                return StandardNameTable(**json.loads(snt))
            elif snt[0:4] in ('http', 'wwww.'):
                return StandardNameTable.from_web(snt)
            return StandardNameTable.from_versionname(snt)
        return Empty_Standard_Name_Table
