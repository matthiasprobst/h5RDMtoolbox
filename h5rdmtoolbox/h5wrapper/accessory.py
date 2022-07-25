import warnings
from typing import List, Tuple

import h5py
import xarray as xr


class SpecialDatasetRegistrationWarning(Warning):
    """Warning in case special dataset overwrites existing one."""


class _CachedAccessor:
    """Custom property-like object (descriptor) for caching accessors."""

    def __init__(self, name, accessor):
        self._name = name
        self._accessor = accessor

    def __get__(self, obj, cls):
        if obj is None:
            # we're accessing the attribute of the class, i.e., Dataset.geo
            return self._accessor

        # Use the same dict as @pandas.util.cache_readonly.
        # It must be explicitly declared in obj.__slots__.
        try:
            cache = obj._cache
        except AttributeError:
            cache = obj._cache = {}

        try:
            return cache[self._name]
        except KeyError:
            pass

        try:
            accessor_obj = self._accessor(obj)
        except AttributeError:
            # __getattr__ on data object will swallow any AttributeErrors
            # raised when initializing the accessor, so we need to raise as
            # something else (GH933):
            raise RuntimeError(f"error initializing {self._name!r} accessor.")

        cache[self._name] = accessor_obj
        return accessor_obj


def _register_special_dataset(name, cls):
    def decorator(accessor):
        """decorator"""
        if hasattr(cls, name):
            warnings.warn(
                f"registration of accessor {accessor!r} under name {name!r} for type {cls!r} is "
                "overriding a preexisting attribute with the same name.",
                SpecialDatasetRegistrationWarning,
                stacklevel=2,
            )
        setattr(cls, name, _CachedAccessor(name, accessor))
        return accessor

    return decorator


def register_special_dataset(name, grpcls):
    return _register_special_dataset(name, grpcls)  # grpcls --> e.g. H5FlowGroup


# sample class:
class SpecialDataset:
    standard_names: Tuple = ()

    def __init__(self, h5grp: h5py.Group, comp_names: List = None, attrs=None):
        self._grp = h5grp
        if attrs is None:
            self._attrs = {}
        else:
            self._attrs = attrs
        self._comp_dataarrays = comp_names
        if comp_names is None:
            self._comp_dataarrays = self._get_datasets(*self.standard_names)
        self._dset = None

    def __contains__(self, item):
        return item in self._dset

    def __call__(self, *args, names=None, standard_names=None):
        _comp_dataarrays = self._get_datasets(args, names, standard_names)
        SpecialDataset(self._grp, _comp_dataarrays)

    def __str__(self):
        return f'SpecialDataset of group "{self._grp.name}"\n' + self._dset.__str__()

    def __getitem__(self, args, new_dtype=None):
        if isinstance(args, str):
            return self._dset[args]
        if self._comp_dataarrays is None:
            raise NameError('Could not determine component datasets.')
        base_shape = self._comp_dataarrays[0].shape
        assert all([ds.shape == base_shape for ds in self._comp_dataarrays[1:]])

        xrds = xr.merge([ds.__getitem__(args, new_dtype=new_dtype) for ds in self._comp_dataarrays],
                        combine_attrs="drop_conflicts")
        for icomp, xrarr in enumerate(xrds):
            xrds[xrarr].attrs['vector_component'] = icomp
        xrds.attrs['long_name'] = self._attrs.pop('long_name', 'vector data')
        for k, v in self._attrs.items():
            xrds.attrs[k] = v
        # return xrds
        self._dset = xrds
        return self

    @property
    def data_vars(self):
        return self._dset.data_vars

    def __getattr__(self, item):
        try:
            return self._dset[item]
        except AttributeError as e:
            pass
        try:
            return object.__getattribute__(self, item)
        except AttributeError as e2:
            raise AttributeError(e2)
        raise AttributeError(e)
        # if name not in {"__dict__", "__setstate__"}:

    #     a = self.__getattribute__(item)
    #     print(a)
    #     return a
    #
    #     if item in self._dset:
    #         return self._dset[item]
    #     return self.__getattribute__(item)

    def __setitem__(self, key, value):
        try:
            self._dset[key] = value
        except AttributeError as exr:
            raise AttributeError(exr)

    def _get_datasets(self, *args, names=None, standard_names=None):
        """get vector dataset by standard names or names. Either must be given"""
        if standard_names is None and names is None and len(args) == 0:
            raise ValueError('Either standard_names or names must be provided')
        if args and standard_names is None:
            standard_names = args
        if standard_names and names:
            raise ValueError('Either standard_names or names must be provided but not both')

        if standard_names:
            list_of_component_datasets = []
            for sn in standard_names:
                try:
                    list_of_component_datasets.append(self._grp.get_dataset_by_standard_name(sn, n=1))
                except NameError:
                    print(f'Could not find sandard_name {sn}')
            if len(list_of_component_datasets) == 0:
                list_of_component_datasets = None

        elif names:
            list_of_component_datasets = [self._grp.get(sn) for sn in names]

        if list_of_component_datasets is not None:
            if len(list_of_component_datasets) < 2:
                raise ValueError('Not enough vector components identified. '
                                 'Need at least two to build a vector dataset')
        return list_of_component_datasets

    def to_grp(self, h5grp=None):
        raise NotImplementedError('Writing dataset to hdf group not implemented yet')
        if h5grp is None:
            h5grp = self._grp
        # TODO:
        # h5grp.from_xarray_dataset(self._dset, drop='conflicts')
