"""Transformation module"""
from collections import OrderedDict

import inspect
import numpy as np
import re
import xarray as xr
from typing import Callable

from .name import StandardName
from .. import errors
from ...protected_attributes import PROVENANCE


class Transformation:
    """Transformation class used to transform standard names to new valid standard names"""

    def __init__(self, pattern: str, func: Callable, mfunc: Callable = None,
                 name: str = None):
        if name is None:
            self.name = func.__name__.strip('_')
        else:
            self.name = name
        self.pattern = pattern
        if not self._verify_func(func):
            raise errors.TransformationFunctionError(f"Invalid function {func.__name__}: "
                                                     "Must have parameters 'match' and 'snt'")
        self.func = func
        self.mfunc = mfunc  # mathematical function called in __call__()

    @staticmethod
    def _verify_func(func) -> bool:
        """expecting it to have parameters 'match' and 'snt'"""
        signature = inspect.signature(func)
        return list(signature.parameters.keys()) == ['match', 'snt']

    def __call__(self, da: xr.DataArray, snt=None):
        if snt is None:
            snt = self._snt
        if self.mfunc is None:
            raise NotImplementedError(f'Mathematical function not implemented for transformation "{self}"')
        if not isinstance(da, xr.DataArray):
            raise TypeError(f"Expected xr.DataArray, got {type(da)}")
        return self.mfunc(da, snt)

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name}, pattern={self.pattern}, func={self.func.__name__})"

    @property
    def snt(self):
        if self._snt is None:
            raise errors.TransformationError("No Standard name table has been assigned to this transformation yet")
        return self._snt

    standard_name_table = snt  # alias

    def match(self, standard_name):
        """Check if the transformation is applicable to the standard name"""
        return re.match(self.pattern, standard_name)

    def build_name(self, match, snt=None):
        """Build a new standard name from the match object"""
        if snt is None:
            snt = self._snt
        return self.func(match, snt)


# def evaluate(transformation: Transformation, match, snt) -> StandardName:
#     """Evaluate the transformation. Raises an error if the transformation is not applicable."""
#     return transformation.func(match, snt)


def _magnitude_of(match, snt) -> StandardName:
    groups = match.groups()
    assert len(groups) == 1
    sn = snt[groups[0]]
    new_description = f"Magnitude of {sn.name}. {sn.description}"
    return StandardName(match.string, sn.units, new_description)


magnitude_of = Transformation(r"^magnitude_of_(.*)$", _magnitude_of)


def _arithmetic_mean_of(match, snt) -> StandardName:
    """Arithmetic mean"""
    groups = match.groups()
    assert len(groups) == 1
    wrt_split = groups[0].split('_wrt_')
    sn = snt[wrt_split[0]]
    if len(wrt_split) == 1:
        new_description = f"Arithmetic mean of {sn.name}. {sn.description}"
    else:
        if wrt_split[1] == '':
            raise KeyError('No standard name provided for "wrt"')
        else:
            wrt_names = wrt_split[1].split('_and_')
            # this will raise errors if the standard names do not exist:
            wrt_sn = [snt[name] for name in wrt_names]
            wrt_names_str = " and ".join(wrt_names)
            wrt_sn_descriptions = " ".join([sn.description for sn in wrt_sn])
            new_description = f"Arithmetic mean of {sn.name} wrt to {wrt_names_str}. {wrt_sn_descriptions}"
    return StandardName(match.string, sn.units, new_description)


def _mfunc_arithmetic_mean_of(da, snt, dim=None):
    with xr.set_options(keep_attrs=True):
        new_da = da.mean(dim=dim)
        new_sn_name = f'arithmetic_mean_of_{da.standard_name}'
        # check if it exists by getting the SN from the SNT:
        new_sn = snt[new_sn_name]
        new_sn.equal_unit(new_da.units)
        new_da.attrs['standard_name'] = new_sn_name

        # tracking provenance:
        coord_data = da.coords[da.dims[0]]
        prov = new_da.attrs.get(PROVENANCE, {})

        method_prov = OrderedDict(prov.get('SNT', {}))
        # if 'arithmetic_mean_of' in method_prov:
        #     # TODO: the following error might not be true for ND-arrays. e.g. first call mean over x, then over y...
        #     # leave it for now...
        #     raise KeyError('There is provenance data about "arithmetic_mean_of". This function cannot be called again.')
        if dim is None:
            dims = da.dims
        else:
            if isinstance(dim, str):
                dims = [dim]
            else:
                dims = dim
        proc = {}
        for d in dims:
            print(d)
            coord = da.coords.get(d, None)
            if coord is not None:
                proc[d] = [coord[0].to_dict(), coord[-1].to_dict()]
        method_prov['arithmetic_mean_of'] = proc
        method_prov.move_to_end('arithmetic_mean_of', False)
        prov['SNT'] = dict(method_prov)
        new_da.attrs[PROVENANCE] = prov

        return new_da


arithmetic_mean_of = Transformation(r"arithmetic_mean_of_(.*)?",
                                    _arithmetic_mean_of, _mfunc_arithmetic_mean_of)


def _standard_deviation_of(match, snt) -> StandardName:
    groups = match.groups()
    assert len(groups) == 1
    sn = snt[groups[0]]
    new_description = f"Standard deviation of {sn.name}"
    return StandardName(match.string, sn.units, new_description)


standard_deviation_of = Transformation(r"^standard_deviation_of_(.*)$", _standard_deviation_of)


def _square_of(match, snt) -> StandardName:
    groups = match.groups()
    assert len(groups) == 1
    sn = snt[groups[0]]
    new_description = f"Square of {sn}. {sn.description}"
    new_units = (1 * sn.units * sn.units).units
    return StandardName(match.string, new_units, new_description)


square_of = Transformation(r"^square_of_(.*)$", _square_of)


def _derivative_of_X_wrt_to_Y(match, snt) -> StandardName:
    """Check if a standard name is a derivative of X wrt to Y"""

    groups = match.groups()
    assert len(groups) == 2
    try:
        sn1, sn2 = [snt[n] for n in groups]
    except errors.StandardNameError as e:
        raise errors.StandardNameError(f'One or multiple standard names in "{match.string}" are not valid. '
                                       f'(orig error: {e})')
    new_units = sn1.units / sn2.units
    new_description = f"Derivative of {sn1.name} with respect to {sn2.name}. {sn1.description} {sn2.description}"
    return StandardName(match.string, new_units, new_description)


derivative_of_X_wrt_to_Y = Transformation(r"^derivative_of_(.*)_wrt_(.*)$",
                                          _derivative_of_X_wrt_to_Y)


def _product_of_X_and_Y(match, snt) -> StandardName:
    """Check if a standard name is a derivative of X wrt to Y"""
    groups = match.groups()
    assert len(groups) == 2
    if all([snt.check(n) for n in groups]):
        sn1 = snt[groups[0]]
        sn2 = snt[groups[1]]
        new_units = (1 * sn1.units * sn2.units).units
        new_description = f"Product of {sn1.name} and {sn2.name}. {sn1.description} {sn2.description}"
        return StandardName(match.string, new_units, new_description)
    raise errors.StandardNameError(f'One or multiple standard names in "{match.string}" are not valid.')


product_of_X_and_Y = Transformation(r"^product_of_(.*)_and_(.*)$",
                                    _product_of_X_and_Y)


def _ratio_of_X_and_Y(match, snt) -> StandardName:
    """Check if a standard name is a derivative of X wrt to Y"""
    groups = match.groups()
    assert len(groups) == 2
    if all([snt.check(n) for n in groups]):
        sn1 = snt[groups[0]]
        sn2 = snt[groups[1]]
        new_units = (1 * sn1.units / sn2.units).units
        new_description = f"Ratio of {sn1.name} and {sn2.name}. {sn1.description} {sn2.description}"
        return StandardName(match.string, new_units, new_description)
    raise errors.StandardNameError(f'One or multiple standard names in "{match.string}" are not valid.')


ratio_of_X_and_Y = Transformation(r"^ratio_of_(.*)_and_(.*)$",
                                  _ratio_of_X_and_Y)
