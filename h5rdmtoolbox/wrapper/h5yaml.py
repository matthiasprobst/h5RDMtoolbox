import h5py
import pathlib
import yaml
from typing import Dict


class H5Yaml:
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
        if self._data is None:
            with open(self.filename, 'r') as f:
                self._data = yaml.safe_load(f)
        return self._data

    def write(self, h5: h5py.Group):
        data = self.data
        for k, v in data.items():
            if not isinstance(v, dict):
                # is an attribute of the grou
                h5.attrs[k] = v
            else:
                # can be dataset or group
                if H5Yaml.is_dataset(v):
                    v.pop('type', None)
                    if 'name' not in v:
                        v['name'] = k

                    h5.create_dataset(**v)
                elif H5Yaml.is_group(v):
                    v.pop('type', None)

                    group_data = v.copy()

                    datasets = {_k: group_data.pop(_k) for _k, _v in v.items() if H5Yaml.is_dataset(_v)}

                    group_data['overwrite'] = group_data.get('overwrite', False)
                    group_data['update_attrs'] = group_data.get('update_attrs', True)

                    if 'name' not in group_data:
                        group_data['name'] = k

                    g = h5.create_group(**group_data)

                    for ds_name, ds_params in datasets.items():
                        g.create_dataset(name=ds_name, **ds_params)

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
