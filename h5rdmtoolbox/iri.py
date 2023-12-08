import h5py
from typing import Dict

from . import consts

NAME_KW = 'name'
DATA_KW = 'data'


def set_name(attr: h5py.AttributeManager, attr_name: str, cls: str) -> None:
    """Set the class of an attribute"""
    iri_name_data = attr.get(consts.IRI_NAME_ATTR_NAME, None)
    if iri_name_data is None:
        iri_name_data = {}
    iri_name_data.update({attr_name: cls})
    attr[consts.IRI_NAME_ATTR_NAME] = iri_name_data


def del_iri_entry(attr: h5py.AttributeManager, attr_name: str) -> None:
    """Delete the attribute name from name and data iri dicts"""
    iri_name_data = attr.get(consts.IRI_NAME_ATTR_NAME, None)
    iri_data_data = attr.get(consts.IRI_NAME_ATTR_NAME, None)
    if iri_name_data is None:
        iri_name_data = {}
    if iri_data_data is None:
        iri_data_data = {}
    iri_name_data.pop(attr_name, None)
    iri_data_data.pop(attr_name, None)
    attr[consts.IRI_NAME_ATTR_NAME] = iri_name_data
    attr[consts.IRI_DATA_ATTR_NAME] = iri_data_data


def set_data(attr: h5py.AttributeManager, attr_name: str, data: str) -> None:
    """Set the class of an attribute"""
    iri_data_data = attr.get(consts.IRI_DATA_ATTR_NAME, None)
    if iri_data_data is None:
        iri_data_data = {}
    iri_data_data.update({attr_name: data})
    attr[consts.IRI_DATA_ATTR_NAME] = iri_data_data


class IRIDict(Dict):
    def __init__(self, _dict: Dict, attr: h5py.AttributeManager = None, attr_name: str = None):
        super().__init__(_dict)
        self._attr = attr
        self._attr_name = attr_name

    @property
    def name(self):
        return self[NAME_KW]

    @name.setter
    def name(self, value):
        set_name(self._attr, self._attr_name, value)

    @property
    def data(self):
        return self[DATA_KW]

    @data.setter
    def data(self, value):
        set_data(self._attr, self._attr_name, value)

    def __setitem__(self, key, value):
        if key == NAME_KW:
            set_name(self._attr, self._attr_name, value)
        elif key == DATA_KW:
            set_data(self._attr, self._attr_name, value)
        else:
            raise KeyError(f'key must be "{NAME_KW}" or "{DATA_KW}"')


class IRIManager:
    """IRI attribute manager"""

    def __init__(self, attr: h5py.AttributeManager = None):
        self._attr = attr

    def get(self, attr_name: str) -> IRIDict:
        return self.__getitem__(attr_name)

    def __setitem__(self, key, value):
        if not isinstance(value, dict):
            raise TypeError('value must be a dict')
        cls = value.pop(NAME_KW, None)
        data = value.pop(DATA_KW, None)
        if len(value) > 0:
            raise ValueError(f'value must be a dict with keys "{NAME_KW}" and/or "{DATA_KW}"')
        if cls is not None:
            set_name(self._attr, key, cls)
        if data is not None:
            set_data(self._attr, key, data)

    def __getitem__(self, item) -> IRIDict:
        return IRIDict({NAME_KW: self._attr.get(consts.IRI_NAME_ATTR_NAME, {}).get(item, None),
                        DATA_KW: self._attr.get(consts.IRI_DATA_ATTR_NAME, {}).get(item, None)},
                       self._attr, item)

    def __delitem__(self, attr_name: str):
        del_iri_entry(self._attr, attr_name)


class IRI_NAME(str):
    """IRI class attribute manager"""

    def __new__(cls, attr):
        instance = super().__new__(cls, '')
        instance._attr = attr
        return instance

    def __setitem__(self, key, value):
        set_name(self._attr, key, value)

    def __getitem__(self, item):
        return self._attr[consts.IRI_NAME_ATTR_NAME].get(item, None)


class IRI_DATA(IRIManager):
    """IRI data attribute manager"""

    def __setitem__(self, key, value):
        set_name(self._attr, key, value)
