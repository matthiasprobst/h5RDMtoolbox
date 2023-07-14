import h5py
import pandas as pd
import pathlib
import pint
import yaml
from IPython.display import display, HTML
from datetime import datetime
from typing import List, Union, Dict

from . import errors
from .standard_name import StandardName
from .transformation import derivative_of_X_wrt_to_Y
from .._logger import logger
from ..utils import dict2xml
from ..._user import UserDir
from ...utils import generate_temporary_filename


class StandardNameTable:
    """Standard Name Table class

    Examples
    --------
    >>> from h5rdmtoolbox.conventions.tbx import StandardNameTable
    >>> table = StandardNameTable.from_yaml('standard_name_table.yaml')
    >>> # check a standard name
    >>> table.check('x_velocity')
    True
    >>> # check a transformed standard name
    >>> table.check('derivative_of_x_velocity_wrt_to_x_coordinate')
    True
    """
    __slots__ = ('table', '_meta', '_alias', '_name', '_version_number', 'transformations')

    def __init__(self, name, version_number, table, alias=None, **meta):
        if table is None:
            table = {}
        self.table = table
        self._name = name
        self._version_number = version_number
        # fix key canonical_units
        for k, v in self.table.items():
            if 'canonical_units' in v:
                v['units'] = v['canonical_units']
                del v['canonical_units']
        self._meta = meta
        self.transformations = (derivative_of_X_wrt_to_Y,)
        if alias is None:
            self._alias = {}
        else:
            self._alias = alias

    def __repr__(self):
        _meta = self.meta.pop('alias', None)
        meta_str = ', '.join([f'{key}: {value}' for key, value in self.meta.items()])
        return f'<StandardNameTable: ({meta_str})>'

    def __contains__(self, standard_name):
        return standard_name in self.table

    def __getitem__(self, standard_name: str) -> StandardName:
        """Return table entry"""
        if standard_name in self.table:
            entry = self.table[standard_name]
            if 'canonical_units' in entry:
                units = entry['canonical_units']
                import warnings
                warnings.warn(f'canonical_units is deprecated. Use units instead.',
                              DeprecationWarning)
            else:
                units = entry['units']
            return StandardName(standard_name,
                                units,
                                entry['description'])
        for transformation in self.transformations:
            sn = transformation(standard_name, self)
            if sn:
                return sn
        raise errors.StandardNameError(f'{standard_name} not found in {self.name}')

    def __getattr__(self, item):
        if item in self.meta:
            return self.meta[item]
        return self.__getattribute__(item)

    @property
    def alias(self) -> Dict:
        """Return alias dictionary"""
        return self._alias

    @property
    def versionname(self) -> str:
        """Return version name which is constructed like this: <name>-v<version_number>"""
        return f'{self._name}-v{self._version_number}'

    @property
    def name(self) -> str:
        """Return name of the Standard Name Table"""
        return self._name

    @property
    def meta(self) -> Dict:
        """Return meta data dictionary"""
        return self._meta

    @property
    def version_number(self) -> str:
        """Return version number of the Standard Name Table"""
        return self._version_number

    @property
    def versionname(self) -> str:
        """Return version name which is constructed like this: <name>-v<version_number>"""
        return f'{self.name}-v{self.version_number}'

    def update(self, **standard_names):
        """Update the table with new standard names"""
        for k, v in standard_names.items():
            self.set(k, **v)

    def check_name(self, standard_name: str) -> bool:
        """check the standard name against the table. If the name is not
        exactly in the table, check if it is a transformed standard name."""
        if standard_name in self.table:
            return True
        for transformation in self.transformations:
            if transformation(standard_name, self):
                return True
        return False

    def check(self, standard_name: str, units: Union[pint.Unit, str] = None) -> bool:
        """check the standard name against the table. If the name is not
        exactly in the table, check if it is a transformed standard name.
        If `units` is provided, check if the units are equal to the units"""
        valid_sn = self.check_name(standard_name)
        if not valid_sn:
            return False
        if units is None:
            return True
        return self[standard_name].equal_unit(units)

    def check_hdf_group(self, h5grp: h5py.Group, recursive: bool = True, raise_error: bool = True):
        """Check group datasets. Run recursively if requested.
        If raise_error is True, raise an error if a dataset has an invalid standard_name.
        If raise_error is False, log a warning if a dataset has an invalid standard_name.
        """

        valid_group = True

        def _check_ds(name, node):
            if isinstance(node, h5py.Dataset):
                if 'standard_name' in node.attrs:
                    units = node.attrs.get('units', '')

                    valid = self.check(node.attrs['standard_name'], units=units)
                    if not valid:
                        valid_group = False
                        if raise_error:
                            raise errors.StandardNameError(f'Dataset "{name}" has invalid standard_name '
                                                           f'"{node.attrs["standard_name"]}"')
                        else:
                            logger.error(f'Dataset "{name}" has invalid standard_name '
                                         f'"{node.attrs["standard_name"]}"')
                    # units = node.attrs['units']
                    # if units is None:
                    #     logger.warning(f'Dataset %s has not attribute %s! Assuming it is dimensionless', name,
                    #                    'units')
                    #     units = ''
                    # try:
                    #     self.check_units(node.attrs['standard_name'], units=units)
                    # except errors.StandardNameError as e:
                    #     if raise_error:
                    #         raise errors.StandardNameError(e)
                    #     else:
                    #         logger.error(' > ds: %s: %s', node.name, e)

        if recursive:
            h5grp.visititems(_check_ds)
        else:
            _check_ds(None, h5grp)

        return valid_group

    def check_hdf_file(self, filename,
                       recursive: bool = True,
                       raise_error: bool = True):
        """Check file for standard names"""
        with h5py.File(filename) as h5:
            self.check_hdf_group(h5['/'],
                                 recursive=recursive,
                                 raise_error=raise_error)

    def set(self, *args, **kwargs):
        """Set standard names in the table

        Examples
        --------
        >>> from h5rdmtoolbox.conventions.tbx import StandardNameTable, StandardName
        >>> table = StandardNameTable.from_yaml('standard_name_table.yaml')
        >>> table.set('x_velocity', 'm s-1', 'x component of velocity')
        >>> # or
        >>> sn = StandardName('velocity', 'm s-1', 'velocity')
        >>> table.set(sn)
        """
        n_args = len(args)
        n_kwargs = len(kwargs)

        if n_args == 1 and n_kwargs == 0:
            sn = args[0]
            if not isinstance(sn, StandardName):
                raise TypeError(f'Expected a StandardName, got {type(sn)}')
        elif n_args + n_kwargs != 3:
            raise ValueError('Invalid arguments. Either a StandardName object or name, units and description '
                             'must be provided')
        else:
            _data = dict(name=None, units=None, description=None)
            for k, v in zip(_data.keys(), args):
                _data[k] = v
            _data.update(kwargs)
            sn = StandardName(**_data)
        self.table.update({sn.name: {'units': str(sn.units), 'description': sn.description}})
        return self

    # Loader: ---------------------------------------------------------------
    @staticmethod
    def from_yaml(yaml_filename):
        """Initialize a StandardNameTable from a YAML file"""
        with open(yaml_filename, 'r') as f:
            _dict = {}
            for d in yaml.full_load_all(f):
                _dict.update(d)
            table = _dict.pop('table')
            if 'name' not in _dict:
                _dict['name'] = pathlib.Path(yaml_filename).stem
            version_number = _dict.pop('version_number', None)
            name = _dict.pop('name', None)
            return StandardNameTable(name=name, version_number=version_number, table=table, **_dict)

    @staticmethod
    def from_xml(xml_filename: Union[str, pathlib.Path],
                 name: str = None) -> "StandardNameTable":
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

        try:
            import xmltodict
        except ImportError:
            raise ImportError('Package "xmltodict" is missing, but required to import from XML files.')
        with open(str(xml_filename), 'r', encoding='utf-8') as file:
            my_xml = file.read()
        xmldict = xmltodict.parse(my_xml)
        _name = list(xmldict.keys())[0]
        if name is None:
            name = _name

        data = xmldict[_name]

        meta = {'name': name}
        for k in data.keys():
            if k not in ('entry', 'alias') and k[0] != '@':
                meta[k] = data[k]

        table = {}
        for entry in data['entry']:
            table[entry.pop('@id')] = entry

        _alias = data.get('alias', {})
        alias = {}
        if _alias:
            for aliasentry in _alias:
                k, v = list(aliasentry.values())
                alias[k] = v

        snt = StandardNameTable(table=table,
                                alias=alias,
                                **meta
                                )
        return snt

    @staticmethod
    def from_web(url: str, known_hash: str = None,
                 name: str = None,
                 **meta):
        """Create a StandardNameTable from an online resource.
        Provide a hash is recommended.

        Parameters
        ----------
        url : str
            URL of the file to download.

            .. note::

                You may read a table stored as a yaml file from a github repository by using the following url:
                https://raw.githubusercontent.com/<username>/<repository>/<branch>/<filepath>

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
        meta['url'] = url
        snt.meta.update(meta)
        return snt

    @staticmethod
    def from_gitlab(url: str,
                    project_id: int,
                    ref_name: str,
                    file_path: Union[str, pathlib.Path],
                    private_token: str = None) -> "StandardNameTable":
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
        file_path: Union[str, pathlib.Path
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
            snt = StandardNameTable.from_yaml(tmpfilename)
        elif file_path.endswith('.xml'):
            snt = StandardNameTable.from_xml(tmpfilename)
        else:
            raise NotImplementedError(f'Cannot handle file name extension {file_path.rsplit(".", 1)[1]}. '
                                      'Expected yml/yaml or xml')
        snt.meta['url'] = url
        snt.meta['gitlab_src_info'] = dict(url=url, project_id=project_id, ref_name=ref_name, file_path=file_path)
        return snt

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

    # End Loader: -----------------------------------------------------------

    # Export: ---------------------------------------------------------------
    def to_yaml(self, yaml_filename):
        """Export a StandardNameTable to a YAML file"""
        snt_dict = self.to_dict()
        with open(yaml_filename, 'w') as f:
            yaml.dump(snt_dict, f)

    def to_xml(self,
               xml_filename: pathlib.Path,
               datetime_str=None) -> pathlib.Path:
        """Save the SNT in a XML file

        Parameters
        ----------
        xml_filename: pathlib.Path
            Path to use for the XML file
        datetime_str: str, optional
            Datetime format to use for the last_modified field

        Returns
        -------
        pathlib.Path
            Path to the XML file
        """
        if datetime_str is None:
            datetime_str = '%Y-%m-%d_%H:%M:%S'
        last_modified = datetime.now().strftime(datetime_str)

        xml_parent = xml_filename.parent
        xml_name = xml_filename.name
        xml_translation_filename = xml_parent / 'translation' / xml_name
        if not xml_translation_filename.parent.exists():
            xml_translation_filename.parent.mkdir(parents=True)

        meta = self.meta
        meta.update(last_modified=last_modified)

        meta.update(dict(version_number=self.version_number))

        return dict2xml(filename=xml_filename,
                        name=self.name,
                        dictionary=self.table,
                        **meta)

    def register(self, overwrite: bool = False) -> None:
        """Register the standard name table under its versionname."""
        trg = UserDir['standard_name_tables'] / f'{self.versionname}.yml'
        if trg.exists() and not overwrite:
            raise FileExistsError(f'Standard name table {self.versionname} already exists!')
        self.to_yaml(trg)

    # End Export ---------------------------------------------------------------

    def to_dict(self):
        """Export a StandardNameTable to a dictionary"""
        return dict(**self.meta, table=self.table)

    def dump(self, sort_by: str = 'name', **kwargs):
        """pretty representation of the table for jupyter notebooks"""
        df = pd.DataFrame(self.table).T
        if sort_by.lower() in ('name', 'names', 'standard_name', 'standard_names'):
            display(HTML(df.sort_index().to_html(**kwargs)))
        elif sort_by.lower() in ('units', 'unit', 'canoncial_units'):
            display(HTML(df.sort_values('canonical_units').to_html(**kwargs)))
        else:
            raise ValueError(f'Invalid value for sortby: {sort_by}')

    def get_pretty_table(self, sort_by: str = 'name', **kwargs) -> str:
        """string representation of the SNT in form of a table"""
        try:
            from tabulate import tabulate
        except ImportError:
            raise ImportError('Package "tabulate" is missing.')
        df = pd.DataFrame(self.table).T
        if sort_by.lower() in ('name', 'names', 'standard_name', 'standard_names'):
            sorted_df = df.sort_index()
        elif sort_by.lower() in ('units', 'unit', 'canoncial_units'):
            sorted_df = df.sort_values('canonical_units')
        else:
            sorted_df = df
        tablefmt = kwargs.pop('tablefmt', 'psql')
        headers = kwargs.pop('headers', 'keys')
        return tabulate(sorted_df, headers=headers, tablefmt=tablefmt, **kwargs)

    def sdump(self, sort_by: str = 'name', **kwargs) -> None:
        """Dumps (prints) the content as string"""
        meta_str = '\n'.join([f'{key}: {value}' for key, value in self.meta.items()])
        print(f"{meta_str}\n{self.get_pretty_table(sort_by, **kwargs)}")

    @staticmethod
    def get_registered() -> List["StandardNameTable"]:
        """Return sorted list of standard names files"""
        return [StandardNameTable.from_yaml(f) for f in sorted(UserDir['standard_name_tables'].glob('*'))]

    @staticmethod
    def print_registered() -> None:
        """Return sorted list of standard names files"""
        for f in StandardNameTable.get_registered():
            print(f' > {f}')
