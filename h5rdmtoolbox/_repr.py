import h5py
import numpy as np
import os
import pkg_resources
import re
import typing
from IPython.display import HTML, display
from abc import abstractmethod
from numpy import ndarray
from time import perf_counter_ns

from . import get_config
from .orcid import is_valid_orcid_pattern, get_html_repr

H5PY_SPECIAL_ATTRIBUTES = ('DIMENSION_LIST', 'REFERENCE_LIST', 'NAME', 'CLASS', 'COORDINATES')
try:
    CSS_STR = pkg_resources.resource_string('h5rdmtoolbox', 'data/style.css').decode("utf8")
except FileNotFoundError:
    import pathlib

    with open(pathlib.Path(__file__).parent / 'data/style.css') as f:
        CSS_STR = f.read().rstrip()

"""
disclaimer:

dropdown _html representation realized with "h5file_html_repr"
is inspired and mostly taken from:
https://jsfiddle.net/tay08cn9/4/ (xarray package)

"""

SDUMP_TABLE_SPACING = 30, 20, 8, 30


class BColors:
    """Color class to color text"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    ITALIC = '\033[3m'


def make_italic(string):
    """make string italic"""
    return f"{BColors.ITALIC}{string}{BColors.ENDC}"


def make_bold(string):
    """make string bold"""
    return f"{BColors.BOLD}{string}{BColors.ENDC}"


def warningtext(string):
    """make string orange"""
    return f"{BColors.WARNING}{string}{BColors.ENDC}"


def failtext(string):
    """make string red"""
    return f"{BColors.FAIL}{string}{BColors.ENDC}"


def failprint(string):
    """print string in red"""
    print(failtext(string))


def oktext(string):
    """make string green"""
    return f"{BColors.OKGREEN}{string}{BColors.ENDC}"


def okprint(string):
    """print string in red"""
    print(oktext(string))


def process_string_for_link(string: str) -> typing.Tuple[str, bool]:
    """process string to make links actually clickable in html

    Parameters
    ----------
    string: str
        string to process

    Returns
    -------
    str
        processed string
    bool
        True if string actually contains a link

    """
    if 'zenodo.' in string:
        if re.match(r'10\.\d{4,9}/zenodo\.\d{4,9}', string):
            zenodo_url = f'https://doi.org/{string}'
            img_url = f'https://zenodo.org/badge/DOI/{string}.svg'
        if string.startswith('https://zenodo.org/record/'):
            zenodo_url = string
            img_url = f'https://zenodo.org/badge/DOI/{string.split("/")[-1]}.svg'
        return f'<a href="{zenodo_url}"><img src="{img_url}" alt="DOI"></a>', True
    for p in (r"(https?://\S+)", r"(ftp://\S+)", r"(www\.\S+)"):
        urls = re.findall(p, string)
        if urls:
            for url in urls:
                if is_valid_orcid_pattern(url):
                    orcid_url_repr = get_html_repr(url)
                    string = string.replace(url, orcid_url_repr)
                else:
                    string = string.replace(url, f'<a href="{url}">{url}</a>')
            return string, True

    return string, False


class _HDF5StructureRepr:

    def __init__(self, ignore_attrs=None):
        self.base_intent = '  '
        self.max_attr_length = None
        self.collapsed = True
        self._obj_cfg = {}
        if ignore_attrs is None:
            self.ignore_attrs = H5PY_SPECIAL_ATTRIBUTES
        else:
            self.ignore_attrs = ignore_attrs

    def __dataset__(self, name, h5obj) -> str:
        """overwrite the H5Repr parent method"""
        if h5obj.dtype.char == 'S':
            # handel string datasets:
            return self.__stringdataset__(name, h5obj)
        if h5obj.ndim == 0:
            return self.__0Ddataset__(name, h5obj)
        return self.__NDdataset__(name, h5obj)

    @abstractmethod
    def __stringdataset__(self, name, h5obj):
        """dataset representation"""

    @abstractmethod
    def __0Ddataset__(self, name, h5obj):
        """dataset representation"""

    @abstractmethod
    def __NDdataset__(self, name, h5obj):
        """dataset representation"""

    @abstractmethod
    def __group__(self, name, h5obj):
        """dataset representation"""

    @abstractmethod
    def __attrs__(self, name, h5obj):
        """dataset representation"""


class HDF5StructureStrRepr(_HDF5StructureRepr):

    def __call__(self, group, indent=0, preamble=None):
        if preamble:
            print(preamble)
        for attr_name, attr_value in group.attrs.raw.items():
            if not attr_name.isupper():
                print(self.base_intent * indent + self.__attrs__(attr_name, attr_value))
        for key, item in group.items():
            if isinstance(item, h5py.Dataset):
                print(self.base_intent * indent + self.__dataset__(key, item))
                for attr_name, attr_value in item.attrs.raw.items():
                    if not attr_name.isupper() and attr_name not in self.ignore_attrs:
                        print(self.base_intent * (indent + 2) + self.__attrs__(attr_name, attr_value))
            elif isinstance(item, h5py.Group):
                print(self.base_intent * indent + self.__group__(key, item))
                self(item, indent + 1)
                # for attr_name, attr_value in item.attrs.items():
                #     if not attr_name.isupper() and attr_name not in self.ignore_attrs:
                #         print(self.base_intent * (indent + 2) + self.__attr_str__(attr_name, attr_value))

    def __dataset__(self, name: str, h5obj: h5py.Dataset) -> str:
        if h5obj.dtype.char == 'S':
            # handel string datasets:
            return self.__stringdataset__(name, h5obj)
        if h5obj.ndim == 0:
            return self.__0Ddataset__(name, h5obj)
        return self.__NDdataset__(name, h5obj)

    def __stringdataset__(self, name: str, h5obj: h5py.Dataset) -> str:
        """string representation of a string dataset"""
        return f"\033[1m{name}\033[0m: {h5obj.values[()]}"

    def __0Ddataset__(self, name: str, h5obj: h5py.Dataset) -> str:
        """string representation of a 0D dataset"""
        value = h5obj.values[()]
        if isinstance(value, (float, np.float)):
            value = f'{float(value):f}'
        elif isinstance(value, (int, np.integer)):
            value = f'{int(value):d}'
        else:
            raise TypeError(f'Unexpected type {type(value)}')
        return f"\033[1m{name}\033[0m {value}, dtype: {h5obj.dtype}"

    def __NDdataset__(self, name, h5obj: h5py.Dataset):
        """string representation of a ND dataset"""
        return f"\033[1m{name}\033[0m: {h5obj.shape}, dtype: {h5obj.dtype}"

    def __group__(self, name, item) -> str:
        return f"/\033[1m{name}\033[0m"

    def __attrs__(self, name, value) -> str:
        return f'\033[3ma: {name}\033[0m: {value}'


class HDF5StructureHTMLRepr(_HDF5StructureRepr):

    def __call__(self,
                 group,
                 collapsed: bool = True,
                 preamble: str = None,
                 indent: int = 0,
                 chunks: bool = False,
                 maxshape: bool = False):
        if isinstance(group, h5py.Group):
            h5group = group
        else:
            h5group = group['/']

        self.collapsed = collapsed

        self._obj_cfg.update({'chunks': chunks,
                              'maxshape': maxshape})

        _id = h5group.name + perf_counter_ns().__str__()

        _html = f'<head><style>{CSS_STR}</style></head>'
        if preamble:
            _html += f'\n{preamble}\n'
        _html += "\n<div class='h5tb-warp'>"
        _html += self.__group__(h5group.name.rsplit('/', 1)[1], h5group)
        _html += "\n</div>"
        return _html

    def __stringdataset__(self, name, h5obj) -> str:
        _id1 = f'ds-1-{h5obj.name}-{perf_counter_ns().__str__()}'
        _id2 = f'ds-2-{h5obj.name}-{perf_counter_ns().__str__()}'
        _html = f"""\n
                <ul id="{_id1}" class="h5tb-var-list">
                <input id="{_id2}" class="h5tb-varname-in" type="checkbox">
                <label class='h5tb-varname' 
                for="{_id2}">{name}</label>: {h5obj.values[()]}
                """
        return _html

    def __0Ddataset__(self, name: str, h5obj: h5py.Dataset) -> str:
        _id1 = f'ds-1-{h5obj.name}-{perf_counter_ns().__str__()}'
        _id2 = f'ds-2-{h5obj.name}-{perf_counter_ns().__str__()}'
        units = h5obj.attrs.get('units', '')
        _html = f"""\n
                <ul id="{_id1}" class="h5tb-var-list">
                <input id="{_id2}" class="h5tb-varname-in" type="checkbox">
                <label class='h5tb-varname' for="{_id2}">{name}</label>
                <span class="h5tb-dims">{h5obj.values[()]} [{units}] ({h5obj.dtype})</span>"""
        return _html

    def __NDdataset__(self, name, h5obj: h5py.Dataset):
        ds_dirname = os.path.dirname(h5obj.name)
        _shape = h5obj.shape
        if get_config('advanced_shape_repr'):
            _shape_repr = '('
            ndim = h5obj.ndim
            for i in range(ndim):
                orig_dim_name = None
                try:
                    orig_dim_name = h5obj.dims[i][0].name
                except RuntimeError:
                    pass  # no dimension scale could be found
                if orig_dim_name:
                    if os.path.dirname(orig_dim_name) == ds_dirname:
                        dim_name = os.path.basename(orig_dim_name)
                    else:
                        dim_name = orig_dim_name
                    if i == 0:
                        _shape_repr += f'{dim_name}: {_shape[i]}'
                    else:
                        _shape_repr += f', {dim_name}: {_shape[i]}'
                else:
                    if i == 0:
                        _shape_repr += f'{_shape[i]}'
                    else:
                        _shape_repr += f', {_shape[i]}'
            _shape_repr += ')'
            if _shape_repr == '()' and ndim > 0:
                _shape_repr = _shape
        else:
            _shape_repr = _shape

        if self._obj_cfg['chunks']:
            chunks_str = f' chunks={h5obj.chunks}'
        else:
            chunks_str = ''

        if self._obj_cfg['maxshape']:
            maxshape_str = f' maxshape={h5obj.maxshape}'
        else:
            maxshape_str = ''

        _id1 = f'ds-1-{h5obj.name}-{perf_counter_ns().__str__()}'
        _id2 = f'ds-2-{h5obj.name}-{perf_counter_ns().__str__()}'
        _html = f"""\n
                <ul id="{_id1}" class="h5tb-var-list">
                    <input id="{_id2}" class="h5tb-varname-in" type="checkbox">
                    <label class='h5tb-varname' for="{_id2}">{name}</label>
                    <span class="h5tb-dims">{_shape_repr} [{h5obj.dtype}]{chunks_str}{maxshape_str}</span>"""
        return _html

    def __dataset__(self, name, h5obj) -> str:
        """generate html representation of a dataset"""
        if h5obj.dtype.char == 'S':
            _html_pre = self.__stringdataset__(name, h5obj)
        else:
            if h5obj.ndim == 0:
                _html_pre = self.__0Ddataset__(name, h5obj)
            else:
                _html_pre = self.__NDdataset__(name, h5obj)

        # now all attributes of the dataset:
        # open attribute section:
        _html_ds_attrs = """\n                <ul class="h5tb-attr-list">"""
        # write attributes:
        for k, v in h5obj.attrs.raw.items():
            if k not in self.ignore_attrs and not k.isupper():
                _html_ds_attrs += self.__attrs__(k, v)
        # close attribute section
        _html_ds_attrs += """\n                </ul>"""

        # close dataset section
        _html_post = """\n                </ul>"""
        _html_ds = _html_pre + _html_ds_attrs + _html_post
        return _html_ds

    def __group__(self, name, h5obj: h5py.Group):
        nkeys = len(h5obj.keys())
        _id = f'ds-{name}-{perf_counter_ns().__str__()}'
        _groupname = os.path.basename(h5obj.name)
        checkbox_state = 'checked'
        if _groupname == '':
            _groupname = '/'  # recover root name
        else:
            if self.collapsed:
                checkbox_state = ''

        _html = f"""\n
              <ul style="list-style-type: none;" class="h5grp-sections">
                    <li>
                        <input id="group-{_id}" type="checkbox" {checkbox_state}>
                        <label style="font-weight: bold" for="group-{_id}">
                        {_groupname}<span>({nkeys})</span></label>
                  """

        _html += """\n
                    <ul class="h5tb-attr-list">"""
        # write attributes:
        for k, v in h5obj.attrs.raw.items():
            _html += self.__attrs__(k, v)
        # close attribute section
        _html += """
                    </ul>"""

        datasets = [(k, v) for k, v in h5obj.items() if isinstance(v, h5py.Dataset)]
        groups = [(k, v) for k, v in h5obj.items() if isinstance(v, h5py.Group)]

        for k, v in datasets:
            _html += self.__dataset__(k, v)

        for k, v in groups:
            _html += self.__group__(k, v)
        _html += '\n</li>'
        _html += '\n</ul>'
        return _html

    def __attrs__(self, name, h5obj):
        if isinstance(h5obj, ndarray):
            _value = h5obj.copy()
            for i, v in enumerate(h5obj):
                if isinstance(v, str):
                    _value[i], is_url = process_string_for_link(v)
                    if not is_url and self.max_attr_length:
                        if len(v) > self.max_attr_length:
                            _value[i] = f'{v[0:self.max_attr_length]}...'
        else:
            _value_str = f'{h5obj}'
            _value, is_url = process_string_for_link(_value_str)
            if not is_url:
                if self.max_attr_length:
                    if len(_value_str) > self.max_attr_length:
                        _value = f'{_value_str[0:self.max_attr_length]}...'
                    else:
                        _value = h5obj
                else:
                    _value = h5obj

        if name in ('DIMENSION_LIST', 'REFERENCE_LIST'):
            _value = _value.__str__().replace('<', '&#60;')
            _value = _value.replace('>', '&#62;')

        if isinstance(_value, ndarray):
            _value_str = ', '.join(_value)  # _value.__str__().replace("' '", "', '")
        # elif isinstance(_value, str):
        #     _value_str = process_string_for_link(_value)
        else:
            _value_str = _value

        if name == 'standard_name':
            # TODO give standard name a dropdown which shows description and canonical_units
            return f"""<li style="list-style-type: none; font-style:
             italic">{name}: {_value_str}</li>"""
        return f'<li style="list-style-type: none; font-style: italic">{name} : {_value_str}</li>'


class H5Repr:
    """Class managing the sting/html output of HDF5 content"""

    def __init__(self, str_repr: _HDF5StructureRepr = None, html_repr: _HDF5StructureRepr = None):
        if str_repr is None:
            self.str_repr = HDF5StructureStrRepr()
        else:
            self.str_repr = str_repr

        if html_repr is None:
            self.html_repr = HDF5StructureHTMLRepr()
        else:
            self.html_repr = html_repr

    def __html__(self, group, collapsed: bool = True, preamble: str = None,
                 chunks: bool = False, maxshape: bool = False) -> None:
        display(
            HTML(
                self.html_repr(
                    group=group,
                    collapsed=collapsed,
                    preamble=preamble,
                    chunks=chunks,
                    maxshape=maxshape
                )
            )
        )
