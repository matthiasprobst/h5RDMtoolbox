import os
from time import perf_counter_ns
from typing import Union

import h5py
import pkg_resources
from numpy import ndarray

from . import config, utils

IGNORE_ATTRS = ('units', 'DIMENSION_LIST', 'REFERENCE_LIST', 'NAME', 'CLASS', 'COORDINATES')
CSS_STR = pkg_resources.resource_string('h5rdmtoolbox', 'h5wrapper/static/style.css').decode("utf8")

"""
disclaimer:

dropdown _html representation realized with "h5file_html_repr"
is inspired and mostly taken from:
https://jsfiddle.net/tay08cn9/4/ (xarray package)

"""

SDUMP_TABLE_SPACING = 30, 20, 8, 30


def sdump(h5grp, ret=False,
          nspaces=0, grp_only=False,
          hide_attributes=False,
          color_code_verification=True,
          is_layout=False):
    """
    Generates string representation of the hdf5 file content (name, shape, units, long_name)

    Parameters
    ----------
    h5grp: h5py.Group
        Group to print content of (recursively)
    ret : bool, optional
        Whether to return the information string or
        print it. Default is False, which prints the string
    nspaces : int, optional
        number of spaces used as indentation. Default is 0
    grp_only : bool, optional=False
        Only gets group information
    hide_attributes : bool, optional=False
        Hides attributes in output string.
    color_code_verification: bool, optional=True
    is_layout: bool, optional=False
        Flag for specific dataset representation. Shape is irrelevant.

    Returns
    -------
    out : str
        Information string if asked

    Notes
    -----
    Working under notebooks, explore() gives a greater representation, including attributes.
    """

    sp_name, sp_shape, sp_unit, sp_desc = SDUMP_TABLE_SPACING
    out = ''
    spaces = ' ' * nspaces

    if h5grp.name == '/':  # only for root
        if isinstance(h5grp, h5py.Group):
            out += f'> {h5grp.__class__.__name__}: Group name: {h5grp.name}.\n'
        else:
            out += f'> {h5grp.__class__.__name__}: {h5grp.filename}.\n'

    if not hide_attributes:
        # write attributes:
        for ak, av in h5grp.attrs.items():
            if ak not in ('long_name', 'units', 'REFERENCE_LIST', 'NAME', 'CLASS', 'DIMENSION_LIST'):
                _ak = f'{ak}:'
                if isinstance(av, (h5py.Dataset, h5py.Group)):
                    _av = av.name
                else:
                    _av = f'{av}'
                if len(_av) > sp_desc:
                    _av = f'{_av[0:sp_desc]}...'
                out += utils.make_italic(f'\n{spaces}a: {_ak:{sp_name}} {_av}')

    grp_keys = [k for k in h5grp.keys() if isinstance(h5grp[k], h5py.Group)]
    if not grp_only:
        dataset_names = [k for k in h5grp.keys(
        ) if isinstance(h5grp[k], h5py.Dataset)]
        for dataset_name in dataset_names:
            # varname = utils._make_bold(os.path.basename(h5grp._h5ds(h5grp[dataset_name]).name))
            varname = utils.make_bold(os.path.basename(h5grp[dataset_name].name))
            if is_layout:
                out += f'\n{spaces}{varname:{sp_name}} '
            else:
                shape = h5grp[dataset_name].shape
                units = h5grp[dataset_name].units
                if units is None:
                    units = 'NA'
                else:
                    if units == ' ':
                        units = '-'

                out += f'\n{spaces}{varname:{sp_name}} {str(shape):<{sp_shape}}  {units:<{sp_unit}}'

            if not hide_attributes:
                # write attributes:
                for ak, av in h5grp[dataset_name].attrs.items():
                    if ak not in ('long_name', 'units', 'REFERENCE_LIST', 'NAME', 'CLASS', 'DIMENSION_LIST'):
                        _ak = f'{ak}:'
                        if isinstance(av, (h5py.Dataset, h5py.Group)):
                            _av = av.name
                        else:
                            _av = f'{av}'
                        if len(_av) > sp_desc:
                            _av = f'{_av[0:sp_desc]}...'
                        out += utils.make_italic(f'\n\t{spaces}a: {_ak:{sp_name}} {_av}')
        out += '\n'
    nspaces += 2
    for k in grp_keys:
        _grp_name = utils.make_italic(utils.make_bold(f'{spaces}/{k}'))
        _grp_long_name = h5grp[k].long_name
        if grp_only:
            if _grp_long_name is None:
                out += f'\n{_grp_name}'
            else:
                out += f'\n{_grp_name}  ({h5grp[k].long_name})'
        else:
            if _grp_long_name is None:
                out += f'{_grp_name}'
            else:
                out += f'{_grp_name}  ({h5grp[k].long_name})'

        if isinstance(h5grp, h5py.Group):
            out += h5grp[k].sdump(ret=True, nspaces=nspaces, grp_only=grp_only,
                                  color_code_verification=color_code_verification,
                                  hide_attributes=hide_attributes)
        # else:
        #     out += h5grp[k].info(ret=True, nspaces=nspaces, grp_only=grp_only,
        #                         color_code_verification=color_code_verification,
        #                                         hide_attributes=hide_attributes)
    if ret:
        return out
    else:
        print(out)


def _attribute_repr_html(name, value, max_attr_length: Union[int, None]):
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

        # _id_int = perf_counter_ns().__str__()
        # return f"""<ul id="ds-sn-{_id_int}" class="standard-name">
        #         <input id="sn-{_id_int}" class="standard-name" type="checkbox">
        #         <label class='standard-name'; font-style: italic;
        #                for="sn-{_id_int}">{name}: {_value_str}</label>
        #         <ul class="standard-name">
        #             <li style="list-style-type: none; font-style: italic">
        #             description: {standard_names_dict[_value_str]['description']}</li>
        #             <li style="list-style-type: none; font-style: italic">
        #             canonical units: {standard_names_dict[_value_str]['canonical_units']}</li>
        #         </ul>
        #
        #     </ul>"""
    else:
        return f'<li style="list-style-type: none; font-style: italic">{name} : {_value_str}</li>'


def _group_repr_html(h5group, max_attr_length: Union[int, None], collapsed: bool):
    nkeys = len(h5group.keys())
    _id = f'ds-{h5group.name}-{perf_counter_ns().__str__()}'
    _groupname = os.path.basename(h5group.name)
    checkbox_state = 'checked'
    if _groupname == '':
        _groupname = '/'  # recover root name
    else:
        if collapsed:
            checkbox_state = ''

    _html = f"""\n
          <ul style="list-style-type: none;" class="h5grp-sections">
                <li>
                    <input id="group-{_id}" type="checkbox" {checkbox_state}>
                    <label style="font-weight: bold" for="group-{_id}">
                    {_groupname}<span>({nkeys})</span></label>
              """

    _html += f"""\n
                <ul class="h5tb-attr-list">"""
    # write attributes:
    for k, v in h5group.attrs.items():
        _html += _attribute_repr_html(k, v, max_attr_length)
    # close attribute section
    _html += f"""
                </ul>"""

    datasets = [(k, v) for k, v in h5group.items() if isinstance(v, h5py.Dataset) or isinstance(v, h5py.Dataset)]
    groups = [(k, v) for k, v in h5group.items() if isinstance(v, h5py.Group) or isinstance(v, h5py.Group)]

    for k, v in datasets:
        _html += _html_repr_dataset(v, max_attr_length)

    for k, v in groups:
        _html += _group_repr_html(v, max_attr_length, collapsed)
    _html += '\n</li>'
    _html += '\n</ul>'
    return _html


def _html_repr_dataset(h5dataset, max_attr_length: Union[int, None],
                       _ignore_attrs=IGNORE_ATTRS):
    if 'units' in h5dataset.attrs:
        _unit = h5dataset.attrs['units']
        if _unit in ('', ' '):
            _unit = '-'
    else:
        _unit = 'N.A.'

    ds_name = os.path.basename(h5dataset.name)
    ds_dirname = os.path.dirname(h5dataset.name)
    if h5dataset.ndim == 0:
        _shape_repr = ''
    else:
        _shape = h5dataset.shape
        if config.advanced_shape_repr:
            _shape_repr = '('
            ndim = h5dataset.ndim
            for i in range(ndim):
                try:
                    orig_dim_name = h5dataset.dims[i][0].name
                    # print(os.path.dirname(orig_dim_name), ds_dirname)
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
            # print(h5dataset.name, _shape_dim_names)

    _id1 = f'ds-1-{h5dataset.name}-{perf_counter_ns().__str__()}'
    _id2 = f'ds-2-{h5dataset.name}-{perf_counter_ns().__str__()}'
    _html_pre = f"""\n
                <ul id="{_id1}" class="h5tb-var-list">
                <input id="{_id2}" class="h5tb-varname-in" type="checkbox">
                <label class='h5tb-varname' 
                    for="{_id2}">{ds_name}</label>
                <span class="h5tb-dims">{_shape_repr}</span>  [
                <span class="h5tb-unit">{_unit}</span>]"""
    # now all attributes of the dataset:
    # open attribute section:
    _html_ds_attrs = f"""\n<ul class="h5tb-attr-list">"""
    # write attributes:
    for k, v in h5dataset.attrs.items():
        if k not in _ignore_attrs:
            _html_ds_attrs += _attribute_repr_html(k, v, max_attr_length)
    # close attribute section
    _html_ds_attrs += f"""\n
                </ul>"""

    # close dataset section
    _html_post = f"""\n
             </ul>
             """
    _html_ds = _html_pre + _html_ds_attrs + _html_post
    return _html_ds


def h5file_html_repr(h5, max_attr_length: Union[int, None], preamble: str = None,
                     build_debug_html_page: bool = False,
                     collapsed: bool = True):
    """

    Parameters
    ----------
    h5: Group
        HDF5 group instance
    max_attr_length: int
        Number of letters to show for attribues. after max_attr_length, the string is cut
    preamble: str=None
        Text to show before pretty html dopdown
    build_debug_html_page: bool
        for debugging purposes
    collapsed: bool, optional=True
        If True, all groups are shown collapsed.
    """
    if not h5.id:
        raise ValueError(f'Can only explore opened HDF files!')

    if isinstance(h5, h5py.Group) or isinstance(h5, h5py.Group):
        h5group = h5
    else:
        h5group = h5['/']

    _id = h5group.name + perf_counter_ns().__str__()

    _html = f'<head><style>{CSS_STR}</style></head>'
    if preamble:
        _html += f'\n{preamble}'
    _html += "\n<div class='h5tb-warp'>"
    _html += _group_repr_html(h5group, max_attr_length=max_attr_length, collapsed=collapsed)
    _html += "\n</div>"

    if build_debug_html_page:
        from pathlib import Path
        print(Path('debug_html_page._html').resolve())
        with open('debug_html_page._html', 'w', encoding='utf-8') as f:
            f.write(_html)
    return _html
