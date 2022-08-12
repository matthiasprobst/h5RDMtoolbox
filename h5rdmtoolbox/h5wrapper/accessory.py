import warnings
from typing import List, Tuple
from typing import TypeVar
from typing import Union

import h5py
import xarray as xr
from IPython.display import HTML, display

T_H5Dataset = TypeVar('T_H5Dataset')
T_H5Group = TypeVar('T_H5Group')


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


USER_PROPERTIES = []


def _register_special_property(cls, overwrite=False):
    def decorator(accessor):
        """decorator"""
        if hasattr(accessor, '__propname__'):
            name = accessor.__propname__
        else:
            name = accessor.__name__
        USER_PROPERTIES.append(name)
        if hasattr(cls, name):
            if overwrite:
                print(f'Overwriting existing property {name}.')
                delattr(cls, name)
            else:
                raise AttributeError(f'Cannot register property {name} to {cls} because it has already a property with '
                                     'this name.')
        fget, fset, fdel, doc = None, None, None, None
        if hasattr(accessor, 'get'):
            fget = accessor.get
        if hasattr(accessor, 'set'):
            fset = accessor.set
        if hasattr(accessor, 'delete'):
            fdel = accessor.delete
        if hasattr(accessor, 'doc'):
            doc = accessor.doc
        setattr(cls, name, property(fget, fset, fdel, doc))
        return accessor

    return decorator


def register_special_dataset(name, cls: Union[T_H5Dataset, T_H5Group]):
    """registers a special dataset to a wrapper class"""
    # if not isinstance(cls, (H5Dataset, H5Group)):
    #     raise TypeError(f'Registration is only possible to H5dataset or H5Group but not {type(cls)}')
    return _register_special_dataset(name, cls)  # grpcls --> e.g. H5FlowGroup


def register_special_property(cls: Union[T_H5Dataset, T_H5Group], overwrite=False):
    """registers a property to a group or dataset. getting method must be specified, setting and deleting are optional,
    also docstring is optional but strongly recommended!"""
    # if not isinstance(cls, (H5Dataset, H5Group)):
    #     raise TypeError(f'Registration is only possible to H5dataset or H5Group but not {type(cls)}')
    return _register_special_property(cls, overwrite)


# sample class:
class SpecialDataset:
    """Basic class of special datasets. Inherited classes typically are vector datasets"""

    standard_names: Tuple = ()

    def __init__(self, h5grp: h5py.Group, comp_names: List = None, attrs=None):
        self._grp = h5grp
        self._grp_name = self._grp.name
        if attrs is None:
            self._attrs = {}
        else:
            self._attrs = attrs
        self._dset = None
        if comp_names is None:
            if len(self.standard_names) == 0:
                self._comp_dataarrays = None
            else:
                self._comp_dataarrays = self._get_datasets(self.standard_names)
        else:
            self._comp_dataarrays = comp_names

    def __contains__(self, item):
        return item in self._dset

    def __call__(self, standard_names=None, names=None):
        _comp_dataarrays = self._get_datasets(standard_names=standard_names, names=names)
        return self.__class__(self._grp, _comp_dataarrays)

    def _repr_html_(self):
        return display(HTML(self._dset._repr_html_()))

    def __repr__(self):
        if self._dset is None:
            if self._grp.name is None:
                return f'SpecialDataset of group "{self._grp_name}" (closed)\n' + self._dset.__repr__()
            if self._dset is None:
                return f'SpecialDataset of group "{self._grp_name}"\n' + self._dset.__repr__()
        return self._dset.__repr__()

    def __str__(self):
        if self._grp.name is None:
            return f'SpecialDataset of group "{self._grp_name}" (closed)\n' + self._dset.__str__()
        return f'SpecialDataset of group "{self._grp_name}"\n' + self._dset.__str__()

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

    def __getattr__(self, item):
        if item in self.__dict__:
            return object.__getattribute__(item)
        if self._dset is not None:
            return self._dset.__getattr__(item)
        if self._comp_dataarrays is not None:
            for ds in self._comp_dataarrays:
                if ds.name[0] == '/':
                    if ds.name[1:] == item:
                        return ds
                if ds.name == item:
                    return ds
        return object.__getattribute__(self, item)

    def __setitem__(self, key, value):
        try:
            self._dset[key] = value
        except AttributeError as exr:
            raise AttributeError(exr)

    @property
    def data_vars(self):
        """returns the variables of the xr.Dataset"""
        return self._dset.data_vars

    def _get_datasets(self, standard_names=None, names=None):
        """get vector dataset by standard names or names. Either must be given"""
        if standard_names is None and names is None:
            raise ValueError('Either "standard_names" or "names" must be provided')
        if standard_names is not None and names is not None:
            raise ValueError('Either "standard_names" or "names" must be provided but not both')

        if standard_names:
            list_of_component_datasets = []
            for sn in standard_names:
                try:
                    list_of_component_datasets.append(self._grp.get_dataset_by_standard_name(sn, n=1))
                except NameError:
                    print(f'Cannot find standard_name {sn}')
            if len(list_of_component_datasets) == 0:
                list_of_component_datasets = None

        elif names:
            list_of_component_datasets = [self._grp.get(sn) for sn in names]

        if list_of_component_datasets is not None:
            if len(list_of_component_datasets) < 2:
                raise ValueError('Not enough vector components identified. '
                                 'Need at least two to build a vector dataset')
        return list_of_component_datasets

    def get_by_attribute(self, attr_name):
        candidats = []
        for var in self._dset.data_vars:
            if attr_name in self._dset[var].attrs:
                candidats.append(self._dset[var])
        if len(candidats) == 1:
            return candidats[0]
        return candidats

    def get_by_standard_name(self, standard_name):
        candidats = []
        for var in self._dset.data_vars:
            if self._dset[var].attrs.get('standard_name') == standard_name:
                candidats.append(self._dset[var])
        if len(candidats) == 1:
            return candidats[0]
        return candidats

    def to_grp(self, h5grp=None):
        raise NotImplementedError('Writing dataset to hdf group not implemented yet')
        if h5grp is None:
            h5grp = self._grp
        # TODO:
        # h5grp.from_xarray_dataset(self._dset, drop='conflicts')
