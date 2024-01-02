import abc
import h5py
from rdflib import URIRef
from typing import Dict, Union

from h5rdmtoolbox import consts

PREDICATE_KW = 'predicate'
OBJECT_KW = 'object'


def set_predicate(attr: h5py.AttributeManager, attr_name: str, value: str) -> None:
    """Set the class of an attribute

    Parameters
    ----------
    attr : h5py.AttributeManager
        The attribute manager object
    attr_name : str
        The name of the attribute
    value : str
        The value (identifier) to add to the iri dict attribute

    Returns
    -------
    None
    """
    iri_name_data = attr.get(consts.IRI_PREDICATE_ATTR_NAME, None)
    if iri_name_data is None:
        iri_name_data = {}
    iri_name_data.update({attr_name: value})
    attr[consts.IRI_PREDICATE_ATTR_NAME] = iri_name_data


def del_iri_entry(attr: h5py.AttributeManager, attr_name: str) -> None:
    """Delete the attribute name from name and data iri dicts"""
    iri_name_data = attr.get(consts.IRI_PREDICATE_ATTR_NAME, None)
    iri_data_data = attr.get(consts.IRI_PREDICATE_ATTR_NAME, None)
    if iri_name_data is None:
        iri_name_data = {}
    if iri_data_data is None:
        iri_data_data = {}
    iri_name_data.pop(attr_name, None)
    iri_data_data.pop(attr_name, None)
    attr[consts.IRI_PREDICATE_ATTR_NAME] = iri_name_data
    attr[consts.IRI_OBJECT_ATTR_NAME] = iri_data_data


def set_object(attr: h5py.AttributeManager, attr_name: str, data: str) -> None:
    """Set the class of an attribute"""
    iri_data_data = attr.get(consts.IRI_OBJECT_ATTR_NAME, None)
    if iri_data_data is None:
        iri_data_data = {}
    iri_data_data.update({attr_name: data})
    attr[consts.IRI_OBJECT_ATTR_NAME] = iri_data_data


class IRIDict(Dict):

    def __init__(self, _dict: Dict, attr: h5py.AttributeManager = None, attr_name: str = None):
        super().__init__(_dict)
        self._attr = attr
        self._attr_name = attr_name

    @property
    def predicate(self):
        p = self[PREDICATE_KW]
        if p is not None:
            return URIRef(p)
        return p

    @predicate.setter
    def predicate(self, value):
        set_predicate(self._attr, self._attr_name, value)

    @property
    def object(self):
        o = self[OBJECT_KW]
        if o is not None:
            return URIRef(o)
        return o

    @object.setter
    def object(self, value):
        set_object(self._attr, self._attr_name, value)

    def __setitem__(self, key, value):
        if key == PREDICATE_KW:
            set_predicate(self._attr, self._attr_name, value)
        elif key == OBJECT_KW:
            set_object(self._attr, self._attr_name, value)
        else:
            raise KeyError(f'key must be "{PREDICATE_KW}" or "{OBJECT_KW}"')


class IRIManager:
    """IRI attribute manager"""

    def __init__(self, attr: h5py.AttributeManager = None):
        self._attr = attr

    @property
    def subject(self) -> Union[URIRef, None]:
        s = self._attr.get(consts.IRI_SUBJECT_ATTR_NAME, None)
        if s is not None:
            return URIRef(s)
        return s

    @subject.setter
    def subject(self, iri: Union[URIRef, str]):
        self._attr[consts.IRI_SUBJECT_ATTR_NAME] = str(iri)

    # @property
    # def subject(self):
    #     return self._attr.get(consts.IRI_SUBJECT_ATTR_NAME, None)

    @property
    def predicate(self):
        return IRI_Predicate(self._attr)

    @property
    def object(self):
        return IRI_OBJECT(self._attr)

    def __eq__(self, other: str):
        return str(self.subject) == str(other)

    def __contains__(self, item):
        return item in self._attr.get(consts.IRI_SUBJECT_ATTR_NAME, list())

    def set_subject(self, iri):
        """Assign iri to an HDF5 object (group or dataset)"""
        self._attr[consts.IRI_SUBJECT_ATTR_NAME] = str(iri)

    def get(self, attr_name: str) -> IRIDict:
        return self.__getitem__(attr_name)

    def __setitem__(self, key, value):
        raise NotImplementedError('IRIManager is read-only. Use properties .name or .data to assign IRI to '
                                  'attribute name or data.')

    def __getitem__(self, item) -> IRIDict:
        return IRIDict({PREDICATE_KW: self._attr.get(consts.IRI_PREDICATE_ATTR_NAME, {}).get(item, None),
                        OBJECT_KW: self._attr.get(consts.IRI_OBJECT_ATTR_NAME, {}).get(item, None)},
                       self._attr, item)

    def __delitem__(self, attr_name: str):
        del_iri_entry(self._attr, attr_name)


class _IRIPO(str, abc.ABC):
    """Abstract class for predicate (P) and object (O)"""
    IRI_ATTR_NAME = None

    def __new__(cls, attr):
        instance = super().__new__(cls, '')
        instance._attr = attr
        return instance

    @abc.abstractmethod
    def __setiri__(self, key, value):
        """Set IRI to an attribute"""

    def get(self, item, default=None):
        attrs = self._attr.get(self.IRI_ATTR_NAME, None)
        if attrs is None:
            return default
        return attrs.get(item, default)

    def __getitem__(self, item) -> Union[URIRef, None]:
        return URIRef(self._attr[self.IRI_ATTR_NAME].get(item, None))

    def __setitem__(self, key, value: str):
        if key not in self._attr:
            raise KeyError(f'No attribute "{key}" found. Cannot assign an IRI to a non-existing attribute.')
        self.__setiri__(key, str(value))


class IRI_Predicate(_IRIPO):
    """IRI class attribute manager"""

    IRI_ATTR_NAME = consts.IRI_PREDICATE_ATTR_NAME

    def __setiri__(self, key, value):
        set_predicate(self._attr, key, value)


class IRI_OBJECT(_IRIPO):
    """IRI data attribute manager"""
    IRI_ATTR_NAME = consts.IRI_OBJECT_ATTR_NAME

    def __setiri__(self, key, value):
        set_object(self._attr, key, value)
