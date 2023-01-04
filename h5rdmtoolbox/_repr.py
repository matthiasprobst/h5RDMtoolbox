import h5py
import os
import pkg_resources
from IPython.display import HTML, display
from abc import abstractmethod
from numpy import ndarray
from time import perf_counter_ns

from .config import CONFIG as config

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


def make_italic(string):
    """make string italic"""
    return f'\x1B[3m{string}\x1B[0m'


def make_bold(string):
    """make string bold"""
    return f"{BColors.BOLD}{string}{BColors.ENDC}"


def warningtext(string):
    """make string orange"""
    return f"{BColors.WARNING}{string}{BColors.ENDC}"


def failtext(string):
    """make string red"""
    return f"{BColors.FAIL}{string}{BColors.ENDC}"


def oktext(string):
    """make string green"""
    return f"{BColors.OKGREEN}{string}{BColors.ENDC}"


class _HDF5StructureRepr:

    def __init__(self, ignore_attrs=None):
        self.base_intent = '  '
        self.max_attr_length = None
        self.collapsed = True
        if ignore_attrs is None:
            self.ignore_attrs = H5PY_SPECIAL_ATTRIBUTES
        else:
            self.ignore_attrs = ignore_attrs

    def __dataset__(self, name, h5dataset) -> str:
        """overwrite the H5Repr parent method"""
        if h5dataset.dtype.char == 'S':
            # handel string datasets:
            return self.__stringdataset__(name, h5dataset)
        if h5dataset.ndim == 0:
            return self.__0Ddataset__(name, h5dataset)
        return self.__NDdataset__(name, h5dataset)

    @abstractmethod
    def __stringdataset__(self, key, value):
        """dataset representation"""

    @abstractmethod
    def __0Ddataset__(self, key, value):
        """dataset representation"""

    @abstractmethod
    def __NDdataset__(self, key, value):
        """dataset representation"""

    @abstractmethod
    def __group__(self, key, value):
        """dataset representation"""

    @abstractmethod
    def __attrs__(self, key, value):
        """dataset representation"""


class HDF5StructureStrRepr(_HDF5StructureRepr):

    def __call__(self, group, indent=0):
        for attr_name, attr_value in group.attrs.items():
            if not attr_name.isupper():
                print(self.base_intent * indent + self.__attrs__(attr_name, attr_value))
        for key, item in group.items():
            if isinstance(item, h5py.Dataset):
                print(self.base_intent * indent + self.__dataset__(key, item))
                for attr_name, attr_value in item.attrs.items():
                    if not attr_name.isupper() and attr_name not in self.ignore_attrs:
                        print(self.base_intent * (indent + 2) + self.__attrs__(attr_name, attr_value))
            elif isinstance(item, h5py.Group):
                print(self.base_intent * indent + self.__group__(key, item))
                self(item, indent + 1)
                # for attr_name, attr_value in item.attrs.items():
                #     if not attr_name.isupper() and attr_name not in self.ignore_attrs:
                #         print(self.base_intent * (indent + 2) + self.__attr_str__(attr_name, attr_value))

    def __dataset__(self, key, item) -> str:
        if item.dtype.char == 'S':
            # handel string datasets:
            return self.__stringdataset__(key, item)
        if item.ndim == 0:
            return self.__0Ddataset__(key, item)
        return self.__NDdataset__(key, item)

    def __stringdataset__(self, name, h5dataset) -> str:
        """string representation of a string dataset"""
        return f"\033[1m{name}\033[0m: {h5dataset.values[()]}"

    def __0Ddataset__(self, name: str, h5dataset: h5py.Dataset) -> str:
        """string representation of a 0D dataset"""
        value = h5dataset.values[()]
        if isinstance(value, float):
            value = f'{float(value)} '
        elif isinstance(value, int):
            value = f'{int(value)} '
        return f"\033[1m{name}\033[0m {value}, dtype: {h5dataset.dtype}"

    def __NDdataset__(self, name, h5dataset):
        """string representation of a ND dataset"""
        return f"\033[1m{name}\033[0m: {h5dataset.shape}, dtype: {h5dataset.dtype}"

    def __group__(self, key, item) -> str:
        return f"/\033[1m{key}\033[0m"

    def __attrs__(self, key, value) -> str:
        return f'\033[3ma: {key}\033[0m: {value}'


class HDF5StructureHTMLRepr(_HDF5StructureRepr):

    def __call__(self, group, collapsed: bool = True, preamble: str = None, indent: int = 0):
        if isinstance(group, h5py.Group):
            h5group = group
        else:
            h5group = group['/']

        self.collapsed = collapsed

        _id = h5group.name + perf_counter_ns().__str__()

        _html = f'<head><style>{CSS_STR}</style></head>'
        if preamble:
            _html += f'\n{preamble}\n'
        _html += "\n<div class='h5tb-warp'>"
        _html += self.__group__(h5group.name.rsplit('/', 1)[1], h5group)
        _html += "\n</div>"
        return _html

    def __stringdataset__(self, name, h5dataset) -> str:
        _id1 = f'ds-1-{h5dataset.name}-{perf_counter_ns().__str__()}'
        _id2 = f'ds-2-{h5dataset.name}-{perf_counter_ns().__str__()}'
        _html = f"""\n
                <ul id="{_id1}" class="h5tb-var-list">
                <input id="{_id2}" class="h5tb-varname-in" type="checkbox">
                <label class='h5tb-varname' 
                for="{_id2}">{name}</label>: {h5dataset.values[()]}
                """
        return _html

    def __0Ddataset__(self, name: str, h5dataset: h5py.Dataset) -> str:
        _id1 = f'ds-1-{h5dataset.name}-{perf_counter_ns().__str__()}'
        _id2 = f'ds-2-{h5dataset.name}-{perf_counter_ns().__str__()}'
        _html = f"""\n
                <ul id="{_id1}" class="h5tb-var-list">
                <input id="{_id2}" class="h5tb-varname-in" type="checkbox">
                <label class='h5tb-varname' 
                    for="{_id2}">{name}</label>
                <span class="h5tb-dims">{h5dataset.values[()]} ({h5dataset.dtype})</span>"""
        return _html

    def __NDdataset__(self, name, h5dataset):
        ds_dirname = os.path.dirname(h5dataset.name)
        _shape = h5dataset.shape
        if config.ADVANCED_SHAPE_REPR:
            _shape_repr = '('
            ndim = h5dataset.ndim
            for i in range(ndim):
                try:
                    orig_dim_name = h5dataset.dims[i][0].name
                    if os.path.dirname(orig_dim_name) == ds_dirname:
                        dim_name = os.path.basename(orig_dim_name)
                    else:
                        dim_name = orig_dim_name
                    if i == 0:
                        _shape_repr += f'{dim_name}: {_shape[i]}'
                    else:
                        _shape_repr += f', {dim_name}: {_shape[i]}'
                except RuntimeError:
                    pass
            _shape_repr += ')'
            if _shape_repr == '()' and ndim > 0:
                _shape_repr = _shape
        else:
            _shape_repr = _shape
        _id1 = f'ds-1-{h5dataset.name}-{perf_counter_ns().__str__()}'
        _id2 = f'ds-2-{h5dataset.name}-{perf_counter_ns().__str__()}'
        _html = f"""\n
                <ul id="{_id1}" class="h5tb-var-list">
                <input id="{_id2}" class="h5tb-varname-in" type="checkbox">
                <label class='h5tb-varname' 
                    for="{_id2}">{name}</label>
                <span class="h5tb-dims">{_shape_repr} ({h5dataset.dtype})</span>"""
        return _html

    def __dataset__(self, name, h5dataset) -> str:
        """generate html representation of a dataset"""
        if h5dataset.dtype.char == 'S':
            _html_pre = self.__stringdataset__(name, h5dataset)
        else:
            if h5dataset.ndim == 0:
                _html_pre = self.__0Ddataset__(name, h5dataset)
            else:
                _html_pre = self.__NDdataset__(name, h5dataset)

        # now all attributes of the dataset:
        # open attribute section:
        _html_ds_attrs = """\n<ul class="h5tb-attr-list">"""
        # write attributes:
        for k, v in h5dataset.attrs.items():
            if k not in self.ignore_attrs:
                _html_ds_attrs += self.__attrs__(k, v)
        # close attribute section
        _html_ds_attrs += """\n
                    </ul>"""

        # close dataset section
        _html_post = """\n
                 </ul>
                 """
        _html_ds = _html_pre + _html_ds_attrs + _html_post
        return _html_ds

    def __group__(self, key, group: h5py.Group):
        nkeys = len(group.keys())
        _id = f'ds-{key}-{perf_counter_ns().__str__()}'
        _groupname = os.path.basename(group.name)
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
        for k, v in group.attrs.items():
            _html += self.__attrs__(k, v)
        # close attribute section
        _html += """
                    </ul>"""

        datasets = [(k, v) for k, v in group.items() if isinstance(v, h5py.Dataset) or isinstance(v, h5py.Dataset)]
        groups = [(k, v) for k, v in group.items() if isinstance(v, h5py.Group) or isinstance(v, h5py.Group)]

        for k, v in datasets:
            _html += self.__dataset__(k, v)

        for k, v in groups:
            _html += self.__group__(k, v)
        _html += '\n</li>'
        _html += '\n</ul>'
        return _html

    def __attrs__(self, key, value):
        if isinstance(value, ndarray):
            _value = value.copy()
            for i, v in enumerate(value):
                if isinstance(v, str):
                    if self.max_attr_length:
                        if len(v) > self.max_attr_length:
                            _value[i] = f'{v[0:self.max_attr_length]}...'
        else:
            _value_str = f'{value}'
            if self.max_attr_length:
                if len(_value_str) > self.max_attr_length:
                    _value = f'{_value_str[0:self.max_attr_length]}...'
                else:
                    _value = value
            else:
                _value = value

        if key in ('DIMENSION_LIST', 'REFERENCE_LIST'):
            _value = _value.__str__().replace('<', '&#60;')
            _value = _value.replace('>', '&#62;')

        if isinstance(_value, ndarray):
            _value_str = _value.__str__().replace("' '", "', '")
        else:
            _value_str = _value

        if key == 'standard_name':
            # TODO give standard name a dropdown which shows description and canonical_units
            return f"""<li style="list-style-type: none; font-style:
             italic">{key} : {_value_str}</li>"""
        return f'<li style="list-style-type: none; font-style: italic">{key} : {_value_str}</li>'


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

    def __str__(self, group) -> str:
        return self.str_repr(group=group)

    def __html__(self, group, collapsed: bool = True, preamble: str = None):
        display(HTML(self.html_repr(group=group, collapsed=collapsed, preamble=preamble)))
