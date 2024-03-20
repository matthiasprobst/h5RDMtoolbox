import h5py
import importlib_resources
import numpy as np
import os
import re
import typing
import warnings
import xarray as xr
from IPython.display import HTML, display
from abc import abstractmethod
from numpy import ndarray
from time import perf_counter_ns

from . import get_config
from . import identifiers
from . import protected_attributes

H5PY_SPECIAL_ATTRIBUTES = ('DIMENSION_LIST', 'REFERENCE_LIST', 'NAME', 'CLASS', protected_attributes.COORDINATES)
try:
    CSS_STR = importlib_resources.files('h5rdmtoolbox').joinpath('data/style.css').read_bytes().decode("utf8")
except FileNotFoundError:
    import pathlib

    with open(pathlib.Path(__file__).parent / 'data/style.css') as f:
        CSS_STR = f.read().rstrip()

# IRI_ICON = importlib_resources.files('h5rdmtoolbox').joinpath('data/iri_icon.png')
# if IRI_ICON.exists():
#     IRI_ICON = rf'file:///{IRI_ICON}'
# else:
IRI_ICON = "https://github.com/matthiasprobst/h5RDMtoolbox/blob/dev/h5rdmtoolbox/data/iri_icon.png?raw=true"

"""
disclaimer:

dropdown _html representation realized with "h5file_html_repr"
is inspired and mostly taken from:
https://jsfiddle.net/tay08cn9/4/ (xarray package)

"""


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


def make_href(url: str, text: str) -> str:
    """Builds HTML hyperlink from url

    Parameters
    ----------
    url: str
        link destination
    text: str
        display text

    Returns
    -------
    The HTML <a> tag string
    """
    if not url.startswith('http'):
        raise ValueError(f'Invalid URL: "{url}". Must start with "http"')
    return f'<a href="{url}">{text}</a>'


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
            img_url = f'https://zenodo.org/badge/DOI/10.5281/zenodo.{string.split("/")[-1]}.svg'
        return make_href(url=zenodo_url, text=f'<img src="{img_url}" alt="DOI">'), True
    for p in (r"(https?://\S+)", r"(ftp://\S+)", r"(www\.\S+)"):
        urls = re.findall(p, string)
        if urls:
            for url in urls:
                identifier = identifiers.from_url(url)
                if identifier:
                    orcid_url_repr = identifier._repr_html_()
                    string = string.replace(url, orcid_url_repr)
                else:
                    string = string.replace(url, make_href(url, url))
            return string, True

    return string, False


def get_iri_icon_href(iri: str, tooltiptext=None) -> str:
    """get html representation of an IRI with icon. The URL is shown as a tooltip"""
    return f'<a href="{iri}" target="_blank" class="tooltip"> ' \
           f'<img class="size_of_img" src="{IRI_ICON}" alt="Image 1" width="16" height="16" />' \
           f' <span class="tooltiptext">{tooltiptext or iri}</span></a>'


class _HDF5StructureRepr:

    def __init__(self, ignore_attrs=None):
        self.base_intent = '  '
        self.max_attr_length = 100
        self.collapsed = None

        self._obj_cfg = {}
        if ignore_attrs is None:
            self.ignore_attrs = H5PY_SPECIAL_ATTRIBUTES
        else:
            self.ignore_attrs = ignore_attrs

    @property
    def checkbox_state(self) -> str:
        return '' if self.collapsed else 'checked'

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


from . import consts


class HDF5StructureStrRepr(_HDF5StructureRepr):

    def __call__(self, group, indent=0, preamble=None):
        if preamble:
            print(preamble)
        spaces = self.base_intent * indent
        predicate = group.rdf.predicate.get('SELF', None)
        if predicate:
            print(spaces + f'@predicate: {predicate}')
        for attr_name in group.attrs.raw.keys():
            if attr_name == consts.RDF_SUBJECT_ATTR_NAME:
                print(spaces + f'@type: {group.attrs[attr_name]}')
            else:
                if not attr_name.isupper():
                    print(spaces + self.__attrs__(attr_name, group))
        for key, item in group.items():
            if isinstance(item, h5py.Dataset):
                print(spaces + self.__dataset__(key, item))
                for attr_name in item.attrs.raw.keys():
                    if not attr_name.isupper() and attr_name not in self.ignore_attrs:
                        print(self.base_intent * (indent + 2) + self.__attrs__(attr_name, item))
            elif isinstance(item, h5py.Group):
                print(spaces + self.__group__(key, item))
                self(item, indent + 1)

    def __dataset__(self, name: str, h5obj: h5py.Dataset) -> str:
        if h5obj.dtype.char == 'S':
            # handel string datasets:
            return self.__stringdataset__(name, h5obj)
        if h5obj.ndim == 0:
            return self.__0Ddataset__(name, h5obj)
        return self.__NDdataset__(name, h5obj)

    def __stringdataset__(self, name: str, h5obj: h5py.Dataset) -> str:
        """string representation of a string dataset"""
        if h5obj.ndim == 0:
            return f"\033[1m{name}\033[0m: {h5obj.values[()]}"
        return f"\033[1m{name}\033[0m: {h5obj.shape}, dtype: {h5obj.dtype}"

    def __0Ddataset__(self, name: str, h5obj: h5py.Dataset) -> str:
        """string representation of a 0D dataset"""
        value = h5obj.values[()]
        if isinstance(value, (float, np.floating)):
            value = f'{value:f}'
        elif isinstance(value, (int, np.integer)):
            value = f'{int(value):d}'
        elif isinstance(value, (bool, np.bool_)):
            value = f'{value}'
        else:
            warnings.warn(f'Unexpected type {type(value)}', UserWarning)
            value = '?type?'
        return f"\033[1m{name}\033[0m {value}, dtype: {h5obj.dtype}"

    def __NDdataset__(self, name, h5obj: h5py.Dataset):
        """string representation of a ND dataset"""
        return f"\033[1m{name}\033[0m: {h5obj.shape}, dtype: {h5obj.dtype}"

    def __group__(self, name, item) -> str:
        return f"/\033[1m{name}\033[0m"

    def __attrs__(self, name, h5obj) -> str:
        attr_value = h5obj.attrs.raw[name]

        pred = h5obj.rdf[name]['predicate']
        if pred:
            use_attr_name = f'{name} ({pred})'
        else:
            use_attr_name = name

        if isinstance(attr_value, h5py.Group):
            attr_value = f'grp:{attr_value.name}'
        elif isinstance(attr_value, h5py.Dataset):
            attr_value = f'dset:{attr_value.name}'
        return f'\033[3ma: {use_attr_name}\033[0m: {attr_value}'


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
        if h5obj.ndim == 0:
            _pcns = perf_counter_ns().__str__()
            _id1 = f'ds-1-{h5obj.name}-{_pcns}1'
            _id2 = f'ds-2-{h5obj.name}-{_pcns}2'
            return f"""\n
                    <ul id="{_id1}" class="h5tb-var-list">
                    <input id="{_id2}" class="h5tb-varname-in" type="checkbox" {self.checkbox_state}>
                    <label class='h5tb-varname' 
                    for="{_id2}">{name}</label>: [{h5obj.dtype}] data={h5obj.values[()]}
                    """
        elif h5obj.ndim == 1:
            _pcns = perf_counter_ns().__str__()
            _id1 = f'ds-1-{h5obj.name}-{_pcns}1'
            _id2 = f'ds-2-{h5obj.name}-{_pcns}2'
            _strdata = h5obj[()]
            if isinstance(_strdata, xr.DataArray):
                return f"""\n
                        <ul id="{_id1}" class="h5tb-var-list">
                        <input id="{_id2}" class="h5tb-varname-in" type="checkbox" {self.checkbox_state}>
                        <label class='h5tb-varname'
                        for="{_id2}">{name}</label>: [{h5obj.dtype}]
                        """
            try:
                str_values = ', '.join(_strdata)
            except UnicodeDecodeError:
                str_values = '<i>UnicodeDecodeError</i>'
            except TypeError:
                str_values = f'<i>TypeError: {type(_strdata)}</i>'
            return f"""\n
                    <ul id="{_id1}" class="h5tb-var-list">
                    <input id="{_id2}" class="h5tb-varname-in" type="checkbox" {self.checkbox_state}>
                    <label class='h5tb-varname'
                    for="{_id2}">{name}</label>: [{h5obj.dtype}] data="{str_values}"
                    """
        return self.__NDdataset__(name, h5obj)

    def __0Ddataset__(self, name: str, h5obj: h5py.Dataset) -> str:
        _id1 = f'ds-1-{h5obj.name}-{perf_counter_ns().__str__()}'
        _id2 = f'ds-2-{h5obj.name}-{perf_counter_ns().__str__()}'
        units = h5obj.attrs.get('units', None)
        if units is None:
            units = h5obj.attrs.get('hasUnit', '')
        _html = f"""\n
                <ul id="{_id1}" class="h5tb-var-list">
                <input id="{_id2}" class="h5tb-varname-in" type="checkbox" {self.checkbox_state}>
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
                    <input id="{_id2}" class="h5tb-varname-in" type="checkbox" {self.checkbox_state}>
                    <label class='h5tb-varname' for="{_id2}">{name}</label>
                    <span class="h5tb-dims">{_shape_repr} [{h5obj.dtype}]{chunks_str}{maxshape_str}</span>"""
        return _html

    def __dataset__(self, name, h5obj) -> str:
        """generate html representation of a dataset"""

        # iri = h5obj.rdf.predicate.get('SELF', None)
        self_predicate = h5obj.rdf.predicate.get('SELF', None)
        self_subject = h5obj.rdf.subject
        _dsname = name
        if self_predicate is not None:
            _dsname += get_iri_icon_href(self_predicate)

        if self_subject is not None:
            _dsname += get_iri_icon_href(
                self_subject,
                tooltiptext=f'@type: {self_subject}')

        is_string_dataset = h5obj.dtype.char == 'S'
        if is_string_dataset:
            _html_pre = self.__stringdataset__(_dsname, h5obj)
        else:
            if h5obj.ndim == 0:
                _html_pre = self.__0Ddataset__(_dsname, h5obj)
            else:
                _html_pre = self.__NDdataset__(_dsname, h5obj)

        # now all attributes of the dataset:
        # open attribute section:
        _html_ds_attrs = """\n                <ul class="h5tb-attr-list">"""

        for k in h5obj.attrs.keys():
            if k not in self.ignore_attrs and not k.isupper() and k != '@type':
                _html_ds_attrs += self.__attrs__(k, h5obj)

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

        if _groupname == '':
            _groupname = '/'  # recover root name
            checkbox_state = 'checked'
        else:
            checkbox_state = self.checkbox_state

        self_predicate = h5obj.rdf.predicate.get('SELF', None)
        if self_predicate:
            print(self_predicate)
        self_subject = h5obj.rdf.subject

        if self_predicate is not None:
            _groupname += get_iri_icon_href(self_predicate)

        if self_subject is not None:
            _groupname += get_iri_icon_href(self_subject,
                                            tooltiptext=f'@type: {self_subject}')

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
        for k in h5obj.attrs.keys():
            if not k.isupper() and k != '@type':
                _html += self.__attrs__(k, h5obj)
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
        attr_value = h5obj.attrs.raw[name]

        if isinstance(attr_value, np.bytes_):
            try:
                attr_value = attr_value.decode('utf-8')
            except UnicodeDecodeError:
                warnings.warn(f'Cannot decode attribute value for {name}', RuntimeWarning)
        rdf = h5obj.rdf.get(name)

        rdf_predicate = rdf.predicate
        if rdf_predicate is not None:
            name += get_iri_icon_href(rdf_predicate)

        rdf_object = rdf.object

        if isinstance(attr_value, ndarray):

            if all(isinstance(item, str) for item in attr_value):
                _string_value_list = []
                for item in attr_value:
                    _value, is_url = process_string_for_link(item)
                    if is_url:
                        _string_value_list.append(_value)
                    else:
                        _string_value_list.append(item)
                _value_str = ", ".join(_string_value_list)

                if rdf_object is not None:
                    _value_str += get_iri_icon_href(rdf_object)
                return '<li style="list-style-type: none; ' \
                       f'font-style: italic">{name} : {_value_str}</li>'
            else:
                _value = attr_value.__repr__()

                if len(_value) > self.max_attr_length:
                    _value = f'{_value[0:self.max_attr_length]}...'

                if rdf_object is not None:
                    _value += get_iri_icon_href(rdf_predicate)

                return f'<li style="list-style-type: none; font-style: italic">{name} : {_value}</li>'

        if isinstance(attr_value, str):
            _value_str = f'{attr_value}'
            if len(_value_str) > 1:
                if _value_str[0] == '<' and _value_str[-1] == '>':
                    _value_str = _value_str[1:-1]

            # check if it is a identifier:
            identifier = identifiers.from_url(_value_str)
            if identifier is not None:
                _value_html = identifier._repr_html_()
                is_url = True
            else:  # maybe some other url:
                _value_html, is_url = process_string_for_link(_value_str)
                # if is_url and not _value_html.startswith('{'):

            # add rdf icon if available:
            if rdf_object is not None:
                _value_html += get_iri_icon_href(rdf_object)

            if is_url and not _value_html.startswith('{'):  # TODO: why the second condition?
                return f'<li style="list-style-type: none; font-style: italic">{name} : {_value_html}</li>'
            else:
                if self.max_attr_length:
                    if len(_value_str) > self.max_attr_length:
                        _value_str = f'{_value_str[0:self.max_attr_length - 3]}...'
                    else:
                        _value_str = attr_value
                else:
                    _value_str = attr_value
            if rdf_object is not None:
                _value_str += get_iri_icon_href(rdf_object)
            return f'<li style="list-style-type: none; font-style: italic">{name} : {_value_str}</li>'

        if not isinstance(attr_value, ndarray):
            if getattr(attr_value, '_repr_html_', None):
                _value_str = attr_value._repr_html_()
            else:
                _value_str = str(attr_value)
                if _value_str[0] == '<' and _value_str[-1] == '>':
                    _value_str = _value_str[1:-1]
                if self.max_attr_length:
                    if len(_value_str) > self.max_attr_length:
                        _value_str = f'{_value_str[0:self.max_attr_length - 3]}...'
                    else:
                        _value_str = attr_value
                else:
                    _value_str = attr_value

        if rdf_object is not None:
            _value_str += get_iri_icon_href(rdf_object)
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
