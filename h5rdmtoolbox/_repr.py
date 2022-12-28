import h5py
import os
import pkg_resources
from numpy import ndarray
from time import perf_counter_ns
from typing import Union

from .config import CONFIG as config

IGNORE_ATTRS = ('units', 'DIMENSION_LIST', 'REFERENCE_LIST', 'NAME', 'CLASS', 'COORDINATES')
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


class HDF5Printer:
    def __init__(self, root: h5py.Group = None, ignore_attrs=None):
        self.root = root
        self.base_intent = '  '
        self.max_attr_length = None
        self.collapsed = False
        if ignore_attrs is None:
            self.ignore_attrs = []
        else:
            self.ignore_attrs = ignore_attrs

    def __dataset_str__(self, key, item) -> str:
        return f"\033[1m{key}\033[0m: {item.shape} dtype: {item.dtype}"

    def __dataset_html__(self, ds_name, h5dataset, max_attr_length: Union[int, None],
                         _ignore_attrs=IGNORE_ATTRS):

        ds_dirname = os.path.dirname(h5dataset.name)
        if h5dataset.ndim == 0:
            _shape_repr = ''
        else:
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
        if h5dataset.dtype.char == 'S':
            if h5dataset.ndim == 0:
                _html_pre = f"""\n
                            <ul id="{_id1}" class="h5tb-var-list">
                            <input id="{_id2}" class="h5tb-varname-in" type="checkbox">
                            <label class='h5tb-varname' 
                                for="{_id2}">{ds_name}</label>
                            <span class="h5tb-dims">{_shape_repr}</span>: {h5dataset[()]}"""
            else:
                _html_pre = f"""\n
                            <ul id="{_id1}" class="h5tb-var-list">
                            <input id="{_id2}" class="h5tb-varname-in" type="checkbox">
                            <label class='h5tb-varname' 
                                for="{_id2}">{ds_name}</label>
                            <span class="h5tb-dims">{_shape_repr}</span>"""
        else:
            _html_pre = f"""\n
                        <ul id="{_id1}" class="h5tb-var-list">
                        <input id="{_id2}" class="h5tb-varname-in" type="checkbox">
                        <label class='h5tb-varname' 
                            for="{_id2}">{ds_name}</label>
                        <span class="h5tb-dims">{_shape_repr}</span>"""
        # now all attributes of the dataset:
        # open attribute section:
        _html_ds_attrs = """\n<ul class="h5tb-attr-list">"""
        # write attributes:
        for k, v in h5dataset.attrs.items():
            if k not in _ignore_attrs:
                _html_ds_attrs += self.__attr_html__(k, v, max_attr_length)
        # close attribute section
        _html_ds_attrs += """\n
                    </ul>"""

        # close dataset section
        _html_post = """\n
                 </ul>
                 """
        _html_ds = _html_pre + _html_ds_attrs + _html_post
        return _html_ds

    def __group_str__(self, key, item) -> str:
        return f"/\033[1m{key}\033[0m"

    def __group_html__(self, key, h5group, max_attr_length: Union[int, None]) -> str:
        nkeys = len(h5group.keys())
        _id = f'ds-{key}-{perf_counter_ns().__str__()}'
        _groupname = os.path.basename(h5group.name)
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
        for k, v in h5group.attrs.items():
            _html += self.__attr_html__(k, v, max_attr_length)
        # close attribute section
        _html += """
                    </ul>"""

        datasets = [(k, v) for k, v in h5group.items() if isinstance(v, h5py.Dataset) or isinstance(v, h5py.Dataset)]
        groups = [(k, v) for k, v in h5group.items() if isinstance(v, h5py.Group) or isinstance(v, h5py.Group)]

        for k, v in datasets:
            _html += self.__dataset_html__(k, v, max_attr_length)

        for k, v in groups:
            _html += self.__group_html__(k, v, max_attr_length)
        _html += '\n</li>'
        _html += '\n</ul>'
        return _html

    def __attr_str__(self, key, value) -> str:
        return f'\033[3ma: {key}\033[0m: {value}'

    def __attr_html__(self, name, value, max_attr_length: Union[int, None]):
        if isinstance(value, ndarray):
            _value = value.copy()
            for i, v in enumerate(value):
                if isinstance(v, str):
                    if max_attr_length:
                        if len(v) > max_attr_length:
                            _value[i] = f'{v[0:max_attr_length]}...'
        else:
            _value_str = f'{value}'
            if max_attr_length:
                if len(_value_str) > max_attr_length:
                    _value = f'{_value_str[0:max_attr_length]}...'
                else:
                    _value = value
            else:
                _value = value

        if name in ('DIMENSION_LIST', 'REFERENCE_LIST'):
            _value = _value.__str__().replace('<', '&#60;')
            _value = _value.replace('>', '&#62;')

        if isinstance(_value, ndarray):
            _value_str = _value.__str__().replace("' '", "', '")
        else:
            _value_str = _value

        if name == 'standard_name':
            # TODO give standard name a dropdown which shows description and canonical_units
            return f"""<li style="list-style-type: none; font-style:
             italic">{name} : {_value_str}</li>"""
        return f'<li style="list-style-type: none; font-style: italic">{name} : {_value_str}</li>'

    def print_structure(self, group, indent=0) -> None:
        """print the HDF5 structure"""
        for attr_name, attr_value in group.attrs.items():
            if not attr_name.isupper():
                print(self.base_intent * indent + self.__attr_str__(attr_name, attr_value))
        for key, item in group.items():
            if isinstance(item, h5py.Dataset):
                print(self.base_intent * indent + self.__dataset_str__(key, item))
                for attr_name, attr_value in item.attrs.items():
                    if not attr_name.isupper() and attr_name not in self.ignore_attrs:
                        print(self.base_intent * (indent + 2) + self.__attr_str__(attr_name, attr_value))
            elif isinstance(item, h5py.Group):
                print(self.base_intent * indent + self.__group_str__(key, item))
                self.print_structure(item, indent + 1)
                # for attr_name, attr_value in item.attrs.items():
                #     if not attr_name.isupper() and attr_name not in self.ignore_attrs:
                #         print(self.base_intent * (indent + 2) + self.__attr_str__(attr_name, attr_value))

    def html_dump(self, h5: h5py.Group):
        if isinstance(h5, h5py.Group):
            h5group = h5
        else:
            h5group = h5['/']

        _id = h5group.name + perf_counter_ns().__str__()

        _html = f'<head><style>{CSS_STR}</style></head>'
        _html += "\n<div class='h5tb-warp'>"
        _html += self.__group_html__(h5group.name.rsplit('/', 1)[1], h5group, max_attr_length=self.max_attr_length)
        _html += "\n</div>"
        return _html
