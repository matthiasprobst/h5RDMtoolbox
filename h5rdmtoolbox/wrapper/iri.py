import abc
import h5py
import pydantic
import warnings
from pydantic import HttpUrl
from typing import Dict, Union
from typing import List

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
    try:
        HttpUrl(value)
    except pydantic.ValidationError as e:
        warnings.warn(f'Invalid IRI. Expecting a valid URL. This was validated with pydantic. Pydantic error: {e}',
                      UserWarning)

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


def append(attr: h5py.AttributeManager,
           attr_name: str,
           data: Union[str, List[str]],
           attr_identifier: str) -> None:
    """Append the class, predicate or subject of an attribute"""
    iri_data_data = attr.get(attr_identifier, None)
    if iri_data_data is None:
        iri_data_data = {}

    curr_data = iri_data_data[attr_name]
    if isinstance(curr_data, list):
        if isinstance(data, list):
            curr_data.extend(data)
        else:
            curr_data.append(data)
            iri_data_data.update({attr_name: curr_data})
    else:
        if isinstance(data, list):
            iri_data_data.update({attr_name: [curr_data, *data]})
        else:
            iri_data_data.update({attr_name: [curr_data, data]})
    attr[attr_identifier] = iri_data_data


class IRIDict(Dict):

    def __init__(self, _dict: Dict, attr: h5py.AttributeManager = None, attr_name: str = None):
        super().__init__(_dict)
        self._attr = attr
        self._attr_name = attr_name

    @property
    def predicate(self):
        p = self[PREDICATE_KW]
        if p is not None:
            return p
        return p

    @predicate.setter
    def predicate(self, value):
        set_predicate(self._attr, self._attr_name, value)

    def append_object(self, value):
        """Append the object of an attribute"""
        append(self._attr, self._attr_name, value, consts.IRI_OBJECT_ATTR_NAME)

    @property
    def object(self):
        """Returns the object of an attribute"""
        o = self[OBJECT_KW]
        if o is None:
            return o
        # if isinstance(o, list):
        #     return [i for i in o]
        return o

    @object.setter
    def object(self, value):
        if isinstance(value, (list, tuple)):
            set_object(self._attr, self._attr_name, value[0])
            for v in value[1:]:
                append(self._attr, self._attr_name, v, consts.IRI_OBJECT_ATTR_NAME)
        else:
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

    # @property
    # def type(self):
    #     """Returns the type, the group describes"""
    #     _type = self._attr.get('@type', None)
    #     if _type is None:
    #         return _type
    #     return URIRef(_type)
    #
    # @type.setter
    # def type(self, type: Union[URIRef, str]) -> None:
    #     """Sets the type, the group describes"""
    #     self._attr['@type'] = str(type)

    @property
    def subject(self) -> Union[str, None]:
        """Returns the subject of the group or dataset"""
        s = self._attr.get(consts.IRI_SUBJECT_ATTR_NAME, None)
        if s is None:
            return
        # if isinstance(s, list):
        #     return [i for i in s]
        return s

    def add_subject(self, subject: Union[str, List[str]]):
        if isinstance(subject, list):
            data = [str(i) for i in subject]
        else:
            data = str(subject)
        iri_sbj_data = self._attr.get(consts.IRI_SUBJECT_ATTR_NAME, None)
        if iri_sbj_data is None:
            self._attr[consts.IRI_SUBJECT_ATTR_NAME] = data
            return
        if isinstance(iri_sbj_data, list):
            iri_sbj_data.extend(data)
        else:
            iri_sbj_data = [iri_sbj_data, ]
            iri_sbj_data.append(data)
        self._attr[consts.IRI_SUBJECT_ATTR_NAME] = list(set(iri_sbj_data))

    @subject.setter
    def subject(self, iri_type: Union[str, List[str]]):
        """Sets the subject of the group or dataset. Will overwrite existing subjects.
        If you want to add (append), use add_subject() instead."""
        if isinstance(iri_type, list):
            data = [str(i) for i in iri_type]
        else:
            data = str(iri_type)

        self._attr[consts.IRI_SUBJECT_ATTR_NAME] = data

    def append_subject(self, subject: str):
        """Append the subject"""
        curr_subjects = self._attr.get(consts.IRI_SUBJECT_ATTR_NAME, [])
        if isinstance(curr_subjects, list):
            if isinstance(subject, list):
                curr_subjects.extend(subject)
            else:
                curr_subjects.append(subject)
            self._attr[consts.IRI_SUBJECT_ATTR_NAME] = curr_subjects
        else:
            if isinstance(subject, list):
                self._attr[consts.IRI_SUBJECT_ATTR_NAME] = [curr_subjects, *subject]
            else:
                self._attr[consts.IRI_SUBJECT_ATTR_NAME] = [curr_subjects, subject]

    @property
    def predicate(self):
        return IRI_Predicate(self._attr)

    @predicate.setter
    def predicate(self, predicate: str):
        iri_sbj_data = self._attr.get(consts.IRI_PREDICATE_ATTR_NAME, None)
        if iri_sbj_data is None:
            iri_sbj_data = {}
        iri_sbj_data.update({'SELF': predicate})
        self._attr[consts.IRI_PREDICATE_ATTR_NAME] = iri_sbj_data

    @property
    def object(self):
        return IRI_OBJECT(self._attr)

    def __eq__(self, other: str):
        return str(self.subject) == str(other)

    def __contains__(self, item):
        return item in self._attr.get(consts.IRI_SUBJECT_ATTR_NAME, list())

    def set_subject(self, iri):
        """Assign iri to an HDF5 object (group or dataset)"""
        if iri is not None:
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


class _IRIPO(abc.ABC):
    """Abstract class for predicate (P) and object (O)"""
    IRI_ATTR_NAME = None

    def __init__(self, attr):
        self._attr = attr

    # def __new__(cls, attr):
    #     instance = super().__new__(cls, '')
    #     instance._attr = attr
    #     return instance

    @abc.abstractmethod
    def __setiri__(self, key, value):
        """Set IRI to an attribute"""

    def get(self, item, default=None):
        attrs = self._attr.get(self.IRI_ATTR_NAME, None)
        if attrs is None:
            return default
        return attrs.get(item, default)

    def __getitem__(self, item) -> Union[str, None]:
        return self._attr[self.IRI_ATTR_NAME].get(item, None)

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
