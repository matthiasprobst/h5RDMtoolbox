"""Standard name table module"""
import h5py
import json
import pandas as pd
import pathlib
import pint
import shutil
import warnings
import yaml
from IPython.display import display, HTML
from datetime import datetime, timezone
from typing import Callable, List
from typing import Dict, Tuple

from h5rdmtoolbox._user import UserDir
from h5rdmtoolbox.utils import generate_temporary_filename
from . import constructor
from . import consts
from .transformation import *
from .. import logger
from ..utils import dict2xml, get_similar_names_ratio
from ... import errors

__this_dir__ = pathlib.Path(__file__).parent


class StandardNameTable:
    """Standard Name Table (SNT) class

    Parameters
    ----------
    name: str
        Name of the SNT
    version: str
        Version of the table. Must be something like v1.0
    meta: Dict
        Meta data of the table
    standards: Dict
        Contains all entries in the YAML file, which is not meta.
        Currently expected:
        - table: Dict
            The table containing 'units' and 'description'
        - alias: Dict
            Dictionary containing the aliases
        - devices: List[str]
            List of defined devices to be used in transformations like
            difference_of_<standard_name>_across_<Device>
        - locations: List[str]
            List of defined locations to be used in transformations like
            difference_of_<standard_name>_between_<location>_and_<location>

    Notes
    -----
    Call `StandardNameTable.transformations` to get a list of available transformations

    Examples
    --------
    >>> from h5rdmtoolbox.conventions.standard_names.table import StandardNameTable
    >>> table = StandardNameTable.from_yaml('standard_name_table.yaml')
    >>> # check a standard name
    >>> table.check('x_velocity')
    True
    >>> # check a transformed standard name
    >>> table.check('derivative_of_x_velocity_wrt_to_x_coordinate')
    True
    """

    # __slots__ = ('_standard_names', '_meta', '_alias', '_name', '_version',
    #              '_devices', '_locations', '_reference_frames', '_transformations',
    #              '_standard_components')

    def __init__(self,
                 name: str,
                 version: str,
                 meta: Dict,
                 standard_names: Dict = None,
                 standards: Dict = None):
        self._name = name
        if standard_names is None:
            standard_names = {}
        if standards is None:
            standards = {}

        if 'table' in standards:
            self.standard_names = standards.pop('table')
            logger.warning('Parameter "table" is depreciated. Use "standard_names" instead.')

        self._standard_names = standard_names

        def _parse_input(v):
            if isinstance(v, str):
                return {'description': v}
            if isinstance(v, dict):
                return v
            if v is None:
                return {'description': None}
            raise TypeError(f'Wrong type for "v". Expecting dict or str but got {type(v)}')

        self.standards = {}

        standard_reference_frame = standards.pop('reference_frames', None)
        if standard_reference_frame:
            from .constructor import StandardReferenceFrames, StandardReferenceFrame
            self.standards['standard_reference_frame'] = StandardReferenceFrames(
                [StandardReferenceFrame(k, **v) for k, v in standard_reference_frame.items()]
            )

        for k, v in standards.items():
            if v:
                if isinstance(v, (list, tuple)):
                    self.standards[k] = constructor.StandardConstructors(
                        [constructor.StandardConstructor(_k, None) for _k in v]
                    )
                else:
                    self.standards[k] = constructor.StandardConstructors(
                        [constructor.StandardConstructor(_k, **_parse_input(_v)) for _k, _v in v.items()]
                    )

        if version is None and meta.get('version_number', None) is not None:
            version = f'v{meta["version_number"]}'
        meta['version'] = StandardNameTable.validate_version(version)
        # fix key canonical_units
        for k, v in self.standard_names.items():
            if 'canonical_units' in v:
                v['units'] = v['canonical_units']
                del v['canonical_units']
        self._meta = meta
        self._transformations = (derivative_of_X_wrt_to_Y,
                                 magnitude_of,
                                 arithmetic_mean_of,
                                 standard_deviation_of,
                                 square_of,
                                 product_of_X_and_Y,
                                 ratio_of_X_and_Y,
                                 difference_of_X_across_device,
                                 difference_of_X_and_Y_across_device,
                                 difference_of_X_and_Y_between_LOC1_and_LOC2,
                                 X_at_LOC,
                                 in_reference_frame,
                                 component_of,)

    @property
    def locations(self) -> List[str]:
        """List of valid locations"""
        return self.standards.get('locations', None)  # , constructor.EMPTYSTANDARDCONSTRUCTORS)

    @property
    def components(self) -> List[str]:
        """List of valid locations"""
        return self.standards.get('standard_components', None)  # , constructor.EMPTYSTANDARDCONSTRUCTORS)

    @property
    def standard_components(self) -> List[str]:
        """List of valid locations"""
        return self.standards.get('standard_components', None)  # , constructor.EMPTYSTANDARDCONSTRUCTORS)

    @property
    def transformations(self) -> List[Callable]:
        """List of available transformations"""
        return self._transformations

    @property
    def standard_names(self) -> Dict:
        """Return the table containing all standard names with their units and descriptions"""
        return self._standard_names

    @property
    def standard_reference_frames(self):
        """Return list of standard reference frames"""
        return self.standards.get('standard_reference_frame', None)  # , constructor.EMPTYSTANDARDCONSTRUCTORS)

    @property
    def devices(self) -> List[str]:
        """List of defined devices"""
        return self.standards.get('devices', None)  # , constructor.EMPTYSTANDARDCONSTRUCTORS)

    @property
    def aliases(self) -> Dict:
        """returns a dictionary of alias names and the respective standard name"""
        return {v['alias']: k for k, v in self.standard_names.items() if 'alias' in v}

    @property
    def list_of_aliases(self) -> Tuple[str]:
        """Returns list of available aliases"""
        return tuple([v['alias'] for v in self.standard_names.values() if 'alias' in v])

    @property
    def name(self) -> str:
        """Return name of the Standard Name Table"""
        return self._name

    @property
    def meta(self) -> Dict:
        """Return meta data dictionary"""
        return self._meta

    @property
    def version(self) -> str:
        """Return version number of the Standard Name Table"""
        return self._meta.get('version', None)

    @property
    def institution(self) -> str:
        """Return institution name"""
        return self._meta.get('institution', None)

    @property
    def contact(self) -> str:
        """Return version_number"""
        return self._meta.get('contact', None)

    @property
    def valid_characters(self) -> str:
        """Return valid_characters"""
        return self._meta.get('valid_characters', None)

    @property
    def pattern(self) -> str:
        """Return pattern"""
        return self._meta.get('pattern', None)

    @property
    def version_number(self) -> str:
        """Return version_number"""
        return self._meta.get('version_number', None)

    @property
    def versionname(self) -> str:
        """Return version name which is constructed like this: <name>-<version>"""
        return f'{self.name}-{self.version}'

    def __repr__(self):
        _meta = self.meta.pop('alias', None)
        meta_str = ', '.join([f'{key}: {value}' for key, value in self.meta.items()])
        return f'<StandardNameTable: ({meta_str})>'

    def __contains__(self, standard_name):
        return standard_name in self.standard_names

    def __getitem__(self, standard_name: str) -> StandardName:
        """Return table entry"""
        logger.debug(f'Checking "{standard_name}"')
        if standard_name in self.standard_names:
            entry = self.standard_names[standard_name]
            if 'canonical_units' in entry:
                units = entry['canonical_units']
                warnings.warn('canonical_units is deprecated. Use units instead.',
                              DeprecationWarning)
            else:
                units = entry['units']
            return StandardName(name=standard_name,
                                units=units,
                                description=entry['description'],
                                isvector=entry.get('vector', False),
                                alias=entry.get('alias', None))

        logger.debug(f'No exact match of standard name "{standard_name}" in table')

        for transformation in self.transformations:
            sn = transformation(standard_name, self)
            if sn:
                return sn
        logger.debug(f'No transformation applied successfully on "{standard_name}"')

        if standard_name in self.list_of_aliases:
            return self[self.aliases[standard_name]]

        # provide a suggestion for similar standard names
        similar_names = [k for k in [*self.standard_names.keys(), *self.list_of_aliases] if
                         get_similar_names_ratio(standard_name, k) > 0.75]
        if similar_names:
            raise errors.StandardNameError(f'{standard_name} not found in Standard Name Table "{self.name}".'
                                           ' Did you mean one of these: '
                                           f'{similar_names}?')
        raise errors.StandardNameError(f'{standard_name} not found in Standard Name Table "{self.name}".')

    @staticmethod
    def validate_version(version_string: str) -> str:
        """Validate version number. Must be MAJOR.MINOR(a|b|rc|dev). If validated, return version string, else
        raise ValueError."""
        if version_string is None:
            version_string = '0.0'
            warnings.warn(f'Version number is not set. Setting version number to {version_string}.')
        version_string = str(version_string)
        if not re.match(consts.VERSION_PATTERN, version_string):
            raise ValueError(f'Version number "{version_string}" is not valid. Expecting MAJOR.MINOR(a|b|rc|dev).')
        return version_string

    def update(self, **standard_names):
        """Update the table with new standard names"""
        for k, v in standard_names.items():
            self.set(k, **v)

    def check_name(self, standard_name: str) -> bool:
        """check the standard name against the table. If the name is not
        exactly in the table, check if it is a transformed standard name."""
        if standard_name in self.standard_names:
            return True
        for transformation in self.transformations:
            if transformation(standard_name, self):
                return True
            logger.debug(f'No transformation applied successfully on "{standard_name}"')
        return False

    def check(self, standard_name: Union[str, StandardName], units: Union[pint.Unit, str] = None) -> bool:
        """check the standard name against the table. If the name is not
        exactly in the table, check if it is a transformed standard name.
        If `units` is provided, check if the units are equal to the units"""
        if isinstance(standard_name, StandardName):
            standard_name = standard_name.name
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

        def _check_ds(name, node):
            if isinstance(node, h5py.Dataset):
                if 'standard_name' in node.attrs:
                    units = node.attrs.get('units', '')

                    valid = self.check(node.attrs['standard_name'], units=units)
                    if not valid:
                        if raise_error:
                            raise errors.StandardNameError(f'Dataset "{name}" has invalid standard_name '
                                                           f'"{node.attrs["standard_name"]}"')
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

        return True

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
        >>> from h5rdmtoolbox.conventions.standard_names.table import StandardNameTable
        >>> from h5rdmtoolbox.conventions.standard_names.name import StandardName
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
            _data = {'name': None, 'units': None, 'description': None}
            for k, v in zip(_data.keys(), args):
                _data[k] = v
            _data.update(kwargs)
            sn = StandardName(**_data)
        self.standard_names.update({sn.name: {'units': str(sn.units), 'description': sn.description}})
        return self

    def sort(self) -> "StandardNameTable":
        """Sorts the standard name table"""
        _tmp_yaml_filename = generate_temporary_filename(suffix='.yaml')
        self.to_yaml(_tmp_yaml_filename)
        return StandardNameTable.from_yaml(_tmp_yaml_filename)

    # Loader: ---------------------------------------------------------------
    @staticmethod
    def from_yaml(yaml_filename):
        """Initialize a StandardNameTable from a YAML file"""
        with open(yaml_filename, 'r') as f:
            _dict = {}

            REQ_KEYS = ['standard_names',
                        'name',
                        'version',
                        'institution',
                        'contact',
                        'valid_characters',
                        'pattern',
                        'last_modified', ]

            for d in yaml.full_load_all(f):
                _dict.update(d)

            if 'name' not in _dict:
                _dict['name'] = pathlib.Path(yaml_filename).stem
            version = _dict.pop('version', None)
            name = _dict.pop('name', None)

            meta = {}
            for k, v in _dict.items():
                if isinstance(v, (str, int, float)):
                    meta[k] = v
            for k in meta:
                _dict.pop(k)

            if k not in REQ_KEYS:
                for k in meta.keys():
                    raise ValueError(f'Invalid key "{k}" in YAML file. Valid keys are: {REQ_KEYS}')

            standard_names = _dict.pop('standard_names', None)
            if standard_names is None:
                standard_names = _dict.pop('table', None)
                if standard_names is None:
                    raise ValueError('No key "standard_names" names found in the YAML file')
            else:
                logger.warning('The "table" key is deprecated. Use "standard_names" instead')

            standard_devices = _dict.pop('standard_devices', None)
            standard_locations = _dict.pop('standard_locations', None)
            standard_reference_frames = _dict.pop('standard_reference_frames', None)
            standard_components = _dict.pop('standard_components', None)
            return StandardNameTable(name=name,
                                     version=version,
                                     standard_names=standard_names,
                                     standards=dict(
                                         devices=standard_devices,
                                         reference_frames=standard_reference_frames,
                                         standard_components=standard_components,
                                         locations=standard_locations),
                                     meta=meta)

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
        if _alias:
            warnings.warn('aliases are not implemented yet', UserWarning)

        if _alias:
            for aliasentry in _alias:
                k, v = list(aliasentry.values())
                table[v]['alias'] = k

        if 'version' not in meta:
            meta['version'] = f"v{meta.get('version_number', None)}"

        snt = StandardNameTable(name=name,
                                version=meta.pop('version'),
                                meta=meta,
                                standard_names=table)
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
        """Download a file from a gitlab repository and provide StandardNameTable based on this.

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
    def from_zenodo(doi: str) -> "StandardNameTable":
        """Download standard name table from Zenodo based on URL

        Parameters
        ----------
        doi: str
            DOI

        Returns
        -------
        snt: StandardNameTable
            Instance of this class


        Example
        -------
        >>> StandardNameTable.from_zenodo(doi="doi:10.5281/zenodo.8158764")

        Notes
        -----
        Zenodo API: https://vlp-new.ur.de/developers/#using-access-tokens
        """
        import zenodo_search as zsearch

        doi = zsearch.utils.parse_doi(doi)

        yaml_filename = UserDir['standard_name_tables'] / f'{doi.replace("/", "_")}.yaml'
        if not yaml_filename.exists():
            record = zsearch.search_doi(doi)
            file0 = record.files[0]
            assert record.files[0].type == 'yaml'
            _yaml_filename = file0.download(destination_dir=UserDir['standard_name_tables'])
            shutil.move(_yaml_filename, yaml_filename)
        snt = StandardNameTable.from_yaml(yaml_filename)
        snt._meta.update(dict(zenodo_doi=doi))

        return snt

    @staticmethod
    def load_registered(name: str) -> 'StandardNameTable':
        """Load from user data dir"""
        # search for names:

        candidates = list(UserDir['standard_name_tables'].glob(f'{name}.yml')) + list(
            UserDir['standard_name_tables'].glob(f'{name}.yaml'))
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
    def to_yaml(self, yaml_filename: Union[str, pathlib.Path]):
        """Export the SNT to a YAML file"""
        snt_dict = self.to_dict()

        with open(yaml_filename, 'w') as f:
            yaml.safe_dump(snt_dict, f, sort_keys=False)

    def to_xml(self,
               xml_filename: pathlib.Path,
               datetime_str: Union[str, None] = None) -> pathlib.Path:
        """Export the SNT in a XML file

        Parameters
        ----------
        xml_filename: pathlib.Path
            Path to use for the XML file
        datetime_str: str, optional
            Datetime format to use for the last_modified field. If None, then
            ISO 6801 format is used.

        Returns
        -------
        pathlib.Path
            Path to the XML file
        """
        if datetime_str is None:
            last_modified = datetime.now(datetime.timezone.utc).isoformat()
        else:
            last_modified = datetime.now().strftime(datetime_str)

        xml_parent = xml_filename.parent
        xml_name = xml_filename.name
        xml_translation_filename = xml_parent / 'translation' / xml_name
        if not xml_translation_filename.parent.exists():
            xml_translation_filename.parent.mkdir(parents=True)

        meta = self.meta
        meta.update(last_modified=last_modified)

        meta.update(dict(version=self.version))

        return dict2xml(filename=xml_filename,
                        name=self.name,
                        dictionary=self.standard_names,
                        **meta)

    def to_markdown(self, markdown_filename) -> pathlib.Path:
        """Export the SNT to a markdown file"""
        markdown_filename = pathlib.Path(markdown_filename)
        with open(markdown_filename, 'w') as f:
            f.write(consts.README_HEADER)
            for k, v in self.sort().standard_names.items():
                f.write(f'| {k} | {v["units"]} | {v["description"]} |\n')
        return markdown_filename

    def to_html(self, html_filename, open_in_browser: bool = False) -> pathlib.Path:
        """Export the SNT to html and optionally open it directly if `open_in_browser` is True"""
        html_filename = pathlib.Path(html_filename)

        markdown_filename = self.to_markdown(generate_temporary_filename(suffix='.md'))

        # Read the Markdown file
        markdown_filename = pathlib.Path(markdown_filename)

        template_filename = __this_dir__ / '../html' / 'template.html'

        if not template_filename.exists():
            raise FileNotFoundError(f'Could not find the template file at {template_filename.absolute()}')

        # Convert Markdown to HTML using pandoc
        import pypandoc
        output = pypandoc.convert_file(str(markdown_filename.absolute()), 'html', format='md',
                                       extra_args=['--template', template_filename])

        with open(html_filename, 'w') as f:
            f.write(output)

        # subprocess.call(['pandoc', str(markdown_filename.absolute()),
        #                  '--template',
        #                  str(template_filename),
        #                  '-o', str(html_filename.absolute())])

        if open_in_browser:
            import webbrowser
            webbrowser.open('file://' + str(html_filename.resolve()))
        return html_filename

    def to_latex(self, latex_filename,
                 column_parameter: str = 'p{0.4\\textwidth}lp{.40\\textwidth}',
                 caption: str = 'Standard Name Table',
                 with_header_and_footer: bool = True):
        """Export a StandardNameTable to a LaTeX file"""
        latex_filename = pathlib.Path(latex_filename)
        LATEX_HEADER = f"""\\begin{{table}}[htbp]
\\centering
\\caption{caption}
\\begin{{tabular}}{column_parameter}
"""
        LATEX_FOOTER = """\\end{tabular}"""
        with open(latex_filename, 'w') as f:
            if with_header_and_footer:
                f.write(LATEX_HEADER)
            for k, v in self.sort().standard_names.items():
                desc = v["description"]
                desc[0].upper()
                f.write(
                    f'{k.replace("_", consts.LATEX_UNDERSCORE)} & {v["units"]} & '
                    f'{desc.replace("_", consts.LATEX_UNDERSCORE)} \\\\\n'
                )
            if with_header_and_footer:
                f.write(LATEX_FOOTER)
        return latex_filename

    def to_dict(self):
        """Export a StandardNameTable to a dictionary"""
        d = dict(name=self.name,
                 **self.meta,
                 standard_names=self.standard_names)
        for k, v in self.standards.items():
            # for name, item in zip(('locations', 'devices', 'standard_components'),
            #                       (self.locations, self.devices, self.components)):
            vdict = v.to_dict()
            if vdict:
                d[k] = vdict

        if self.standard_reference_frames:
            d['standard_reference_frames'] = self.standard_reference_frames.to_dict()['standard_reference_frames']

        dt = d.get('last_modified', datetime.now(timezone.utc).isoformat())
        d.update(dict(last_modified=str(dt)))
        return d

    def to_sdict(self):
        """Export a StandardNameTable to a dictionary as string"""
        return json.dumps(self.to_dict())

    # End Export ---------------------------------------------------------------

    def register(self, overwrite: bool = False) -> None:
        """Register the standard name table under its versionname."""
        trg = UserDir['standard_name_tables'] / f'{self.versionname}.yml'
        if trg.exists() and not overwrite:
            raise FileExistsError(f'Standard name table {self.versionname} already exists!')
        self.to_yaml(trg)

    def dump(self, sort_by: str = 'name', **kwargs):
        """pretty representation of the table for jupyter notebooks"""
        df = pd.DataFrame(self.standard_names).T
        if sort_by.lower() in ('name', 'names', 'standard_name', 'standard_names'):
            display(HTML(df.sort_index().to_html(**kwargs)))
        elif sort_by.lower() in ('units', 'unit', 'canonical_units'):
            display(HTML(df.sort_values('canonical_units').to_html(**kwargs)))
        else:
            raise ValueError(f'Invalid value for sort by: {sort_by}')

    def get_pretty_table(self, sort_by: str = 'name', **kwargs) -> str:
        """string representation of the SNT in form of a table"""
        try:
            from tabulate import tabulate
        except ImportError:
            raise ImportError('Package "tabulate" is missing.')
        df = pd.DataFrame(self.standard_names).T
        if sort_by.lower() in ('name', 'names', 'standard_name', 'standard_names'):
            sorted_df = df.sort_index()
        elif sort_by.lower() in ('units', 'unit', 'canonical_units'):
            sorted_df = df.sort_values('canonical_units')
        else:
            sorted_df = df
        tablefmt = kwargs.pop('tablefmt', 'psql')
        headers = kwargs.pop('headers', 'keys')
        return tabulate(sorted_df, headers=headers, tablefmt=tablefmt, **kwargs)

    def dumps(self, sort_by: str = 'name', **kwargs) -> None:
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
