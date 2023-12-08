import h5py
from typing import Dict

from . import consts


def set_cls(attr: h5py.AttributeManager, attr_name: str, cls: str) -> None:
    """Set the class of an attribute"""
    iri_cls_data = attr.get(consts.IRI_CLASS_ATTR_NAME, None)
    if iri_cls_data is None:
        iri_cls_data = {}
    iri_cls_data.update({attr_name: cls})
    attr[consts.IRI_CLASS_ATTR_NAME] = iri_cls_data


def set_individual(attr: h5py.AttributeManager, attr_name: str, individual: str) -> None:
    """Set the class of an attribute"""
    iri_individual_data = attr.get(consts.IRI_INDIVIDUAL_ATTR_NAME, None)
    if iri_individual_data is None:
        iri_individual_data = {}
    iri_individual_data.update({attr_name: individual})
    attr[consts.IRI_INDIVIDUAL_ATTR_NAME] = iri_individual_data


class IRIDict(Dict):
    def __init__(self, _dict: Dict, attr: h5py.AttributeManager = None, attr_name: str = None):
        super().__init__(_dict)
        self._attr = attr
        self._attr_name = attr_name

    def __setitem__(self, key, value):
        if key == 'class':
            set_cls(self._attr, self._attr_name, value)
        elif key == 'individual':
            set_individual(self._attr, self._attr_name, value)
        else:
            raise KeyError('key must be "class" or "individual"')


class IRIManager:
    """IRI attribute manager"""

    def __init__(self, attr: h5py.AttributeManager = None):
        self._attr = attr

    def get(self, attr_name: str) -> IRIDict:
        return self.__getitem__(attr_name)

    def __setitem__(self, key, value):
        if not isinstance(value, dict):
            raise TypeError('value must be a dict')
        cls = value.pop('class', None)
        individual = value.pop('individual', None)
        if len(value) > 0:
            raise ValueError('value must be a dict with keys "class" and/or "individual"')
        if cls is not None:
            set_cls(self._attr, key, cls)
        if individual is not None:
            set_individual(self._attr, key, individual)

    def __getitem__(self, item) -> IRIDict:
        return IRIDict({'class': self._attr.get(consts.IRI_CLASS_ATTR_NAME, {}).get(item, None),
                        'individual': self._attr.get(consts.IRI_INDIVIDUAL_ATTR_NAME, {}).get(item, None)},
                       self._attr, item)


class IRIC(str):
    """IRI class attribute manager"""

    def __new__(cls, attr):
        instance = super().__new__(cls, '')
        instance._attr = attr
        return instance

    def __setitem__(self, key, value):
        set_cls(self._attr, key, value)

    def __getitem__(self, item):
        return self._attr[consts.IRI_CLASS_ATTR_NAME].get(item, None)


class IRII(IRIManager):
    """IRI individual attribute manager"""

    def __setitem__(self, key, value):
        set_cls(self._attr, key, value)
