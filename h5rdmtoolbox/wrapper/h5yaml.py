import pathlib
from typing import Dict, Optional, Protocol

import yaml

from ..wrapper.core import Group


class _H5DictDataInterface(Protocol):

    @property
    def data(self) -> Dict:
        """Return data"""
        ...

    def write(self, h5: Group, num_dtype: Optional[str] = None):
        data = self.data
        for k, v in data.items():
            if not isinstance(v, dict):
                # is an attribute of the grou
                h5.attrs[k] = v
            else:
                item = v.copy()
                # can be dataset or group
                if self.is_dataset(item):
                    item.pop('type', None)
                    if 'name' not in item:
                        item['name'] = k
                    # units = v.pop('units', None)
                    # standard_name = v.pop('standard_name', None)
                    # TODO remove the following hotfix
                    name = item.pop('name')
                    dataset_data = item.pop('data')
                    dtype = item.pop('dtype', None)
                    try:
                        if dtype is None and num_dtype and not isinstance(dataset_data, str):
                            dtype = num_dtype
                        if isinstance(dataset_data, str):
                            h5.create_string_dataset(name, data=dataset_data, **item)
                        else:
                            h5.create_dataset(name, data=dataset_data, dtype=dtype, **item)
                    except (TypeError,) as e:
                        raise RuntimeError('Could not create dataset. Please check the yaml file. The orig. '
                                           f'error is "{e}"')
                elif self.is_group(item):
                    item.pop('type', None)

                    group_data = item.copy()

                    datasets = {_k: group_data.pop(_k) for _k, _v in item.items() if H5Yaml.is_dataset(_v)}

                    group_data['overwrite'] = group_data.get('overwrite', None)
                    group_data['update_attrs'] = group_data.get('update_attrs', True)

                    if 'name' not in group_data:
                        group_data['name'] = k

                    g = h5.create_group(**group_data)

                    for ds_name, ds_params in datasets.items():
                        ds_params = ds_params.copy()
                        dtype = ds_params.pop('dtype', None)
                        if dtype is None and num_dtype and not isinstance(ds_params['data'], str):
                            dtype = num_dtype
                        g.create_dataset(name=ds_name, dtype=dtype, **ds_params)

    @staticmethod
    def is_dataset(item) -> bool:
        if 'type' in item:
            return item['type'].lower() == 'dataset'
        if 'shape' in item:
            return True
        if 'data' in item:
            return True
        return False

    @staticmethod
    def is_group(item) -> bool:
        if 'type' in item:
            return item['type'].lower() == 'group'
        if isinstance(item, dict):
            for n, v in item.items():
                if isinstance(v, dict):
                    return True
                break
            return not H5Yaml.is_dataset(item)
        return False


class H5Dict(_H5DictDataInterface):

    def __init__(self, data):
        self._data = data

    @property
    def data(self) -> Dict:
        return self._data


class H5Yaml(_H5DictDataInterface):
    """Interface class to yaml files which allow to create HDF5
    objects from a yaml file definition"""

    def __init__(self, filename):
        self.filename = pathlib.Path(filename)
        if not self.filename.exists():
            raise FileNotFoundError(f'File not found: {self.filename}')
        if not self.filename.is_file():
            raise FileExistsError(f'Not a file: {self.filename}')
        self._data = None

    @property
    def data(self) -> Dict:
        """Return data"""
        if self._data is None:
            with open(self.filename, 'r') as f:
                self._data = yaml.safe_load(f)
        return self._data
