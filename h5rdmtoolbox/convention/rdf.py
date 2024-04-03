"""RDF (Resource Description Framework) module for use with HDF5 files"""
import abc
import h5py
import pydantic
from pydantic import HttpUrl
from typing import Dict, Union, Optional, List

RDF_OBJECT_ATTR_NAME = 'RDF_OBJECT'
RDF_PREDICATE_ATTR_NAME = 'RDF_PREDICATE'
RDF_SUBJECT_ATTR_NAME = 'RDF_TYPE'


class RDFError(Exception):
    """Generic RDF error"""
    pass


class RDFAttribute:
    """Helper class for quick assignment of RDF attributes to the HDF5 file.

    Examples
    --------
    >>> import h5rdmtoolbox as h5tbx
    >>> from ontolutils import M4I
    >>> rdf_attr = h5tbx.RDFAttribute('0000-0001-8729-0482', rdf_predicate=M4I.orcidId,
    ...                                rdf_object='https://orcid.org/0000-0001-8729-0482')
    >>> with h5tbx.File('test.h5', 'w') as h5:
    ...     grp = h5.create_group('person')
    ...     grp.attrs['orcid'] = rdf_attr
    ...     # equal to:
    ...     # grp.attrs['orcid'] = '0000-0001-8729-0482'
    ...     # grp.rdf.predicate['orcid'] = str(M4I.orcidId)
    ...     # grp.rdf.object['orcid'] = 'https://orcid.org/0000-0001-8729-0482'
    """

    def __init__(self, value, rdf_predicate: str = None, rdf_object: str = None):
        self.value = value

        if rdf_predicate:
            try:
                str(HttpUrl(rdf_predicate))
            except pydantic.ValidationError as e:
                raise RDFError(f'Invalid predicate IRI: "{rdf_predicate}". '
                               f'Expecting a valid URL. This was validated with pydantic. Pydantic error: {e}')

        if rdf_object:
            try:
                str(HttpUrl(rdf_object))
            except pydantic.ValidationError as e:
                raise RDFError(f'Invalid object IRI: "{rdf_object}". '
                               f'Expecting a valid URL. This was validated with pydantic. Pydantic error: {e}')

        self.rdf_predicate = rdf_predicate
        self.rdf_object = rdf_object

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.value}, rdf_predicate={self.rdf_predicate}, rdf_object={self.rdf_object})'

    def __str__(self) -> str:
        return self.__repr__()


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
        raise RDFError(f'Invalid IRI: "{value}" for attr name "{attr_name}". '
                       f'Expecting a valid URL. This was validated with pydantic. Pydantic error: {e}')

    iri_name_data = attr.get(RDF_PREDICATE_ATTR_NAME, None)
    if iri_name_data is None:
        iri_name_data = {}
    iri_name_data.update({attr_name: value})
    attr[RDF_PREDICATE_ATTR_NAME] = iri_name_data


def set_object(attr: h5py.AttributeManager, attr_name: str, data: str) -> None:
    """Set the class of an attribute"""

    iri_data_data = attr.get(RDF_OBJECT_ATTR_NAME, None)

    if iri_data_data is None:
        iri_data_data = {}

    from ontolutils import Thing
    if isinstance(data, Thing):
        data = data.get_jsonld_dict(assign_bnode=False)
    else:
        try:
            data = str(HttpUrl(data))
        except pydantic.ValidationError as e:
            raise RDFError(f'Invalid IRI: "{data}" for attr name "{attr_name}". '
                           f'Expecting a valid URL. This was validated with pydantic. Pydantic error: {e}')

    iri_data_data.update({attr_name: data})
    attr[RDF_OBJECT_ATTR_NAME] = iri_data_data


def del_iri_entry(attr: h5py.AttributeManager, attr_name: str) -> None:
    """Delete the attribute name from name and data iri dicts"""
    iri_name_data = attr.get(RDF_PREDICATE_ATTR_NAME, None)
    iri_data_data = attr.get(RDF_PREDICATE_ATTR_NAME, None)
    if iri_name_data is None:
        iri_name_data = {}
    if iri_data_data is None:
        iri_data_data = {}
    iri_name_data.pop(attr_name, None)
    iri_data_data.pop(attr_name, None)
    attr[RDF_PREDICATE_ATTR_NAME] = iri_name_data
    attr[RDF_OBJECT_ATTR_NAME] = iri_data_data


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
        p = self[RDF_PREDICATE_ATTR_NAME]
        if p is not None:
            return p
        return p

    @predicate.setter
    def predicate(self, value):
        set_predicate(self._attr, self._attr_name, value)

    def append_object(self, value):
        """Append the object of an attribute"""
        append(self._attr, self._attr_name, value, RDF_OBJECT_ATTR_NAME)

    @property
    def object(self):
        """Returns the object of an attribute"""
        o = self[RDF_OBJECT_ATTR_NAME]
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
                append(self._attr, self._attr_name, v, RDF_OBJECT_ATTR_NAME)
        else:
            set_object(self._attr, self._attr_name, value)

    def __setitem__(self, key, value):
        if key == RDF_PREDICATE_ATTR_NAME:
            set_predicate(self._attr, self._attr_name, value)
        elif key == RDF_OBJECT_ATTR_NAME:
            set_object(self._attr, self._attr_name, value)
        else:
            raise KeyError(f'key must be "{RDF_PREDICATE_ATTR_NAME}" or "{RDF_OBJECT_ATTR_NAME}"')


class _RDFPO(abc.ABC):
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

    @property
    def parent(self):
        """Return the parent object"""
        return self._attr._parent

    def get(self, item, default=None):
        attrs = self._attr.get(self.IRI_ATTR_NAME, None)
        if attrs is None:
            return default
        return attrs.get(item, default)

    def __getitem__(self, item) -> Union[str, None]:
        return self.get(item, default=None)

    def __setitem__(self, key, value: str):
        if key not in self._attr:
            raise KeyError(f'No attribute "{key}" found. Cannot assign an IRI to a non-existing attribute.')
        self.__setiri__(key, value)

    def keys(self):
        """Return all attribute names assigned to the IRIs"""
        return self._attr.get(self.IRI_ATTR_NAME, {}).keys()

    def values(self):
        """Return all IRIs assigned to the attributes"""
        return self._attr.get(self.IRI_ATTR_NAME, {}).values()

    def items(self):
        """Return all attribute names and IRIs"""
        return self._attr.get(self.IRI_ATTR_NAME, {}).items()

    def __iter__(self):
        return iter(self.keys())


class RDF_Predicate(_RDFPO):
    """IRI class attribute manager"""

    IRI_ATTR_NAME = RDF_PREDICATE_ATTR_NAME

    def __setiri__(self, key, value):
        set_predicate(self._attr, key, value)


class RDF_OBJECT(_RDFPO):
    """IRI data attribute manager for objects"""
    IRI_ATTR_NAME = RDF_OBJECT_ATTR_NAME

    def __setiri__(self, key, value):
        set_object(self._attr, key, value)


class RDFManager:
    """IRI attribute manager"""

    def __init__(self, attr: h5py.AttributeManager = None):
        self._attr = attr

    @property
    def parent(self):
        """Return the parent object"""
        return self._attr._parent

    def find(self, subject: Optional[str] = None, predicate: Optional[str] = None, object: Optional[str] = None,
             recursive: bool = True) -> List:
        """Find the common objects that have the subject, predicate and object

        Parameters
        ----------
        subject : str
            The subject to search for
        predicate : str
            The predicate to search for
        object : str
            The object to search for
        recursive : bool
            If True, search recursively in the parent group

        Returns
        -------
        List
            A list of objects (h5tbx.Dataset or h5tbx.Group) that have the subject, predicate and object
        """
        res_subject = []
        res_predicate = []
        res_object = []

        def _find_subject(name, node):
            rdfm = RDFManager(node.attrs)
            if not isinstance(rdfm.subject, list):
                subjects = [rdfm.subject]
            else:
                subjects = rdfm.subject
            if str(subject) in subjects:
                res_subject.append(node)

        def _find_predicate(name, node):
            rdfm = RDFManager(node.attrs)
            for k in rdfm.predicate.values():
                if k == str(predicate):
                    res_predicate.append(node)

        def _find_object(name, node):
            rdfm = RDFManager(node.attrs)
            for k in rdfm.object.values():
                if k == str(object):
                    res_object.append(node)

        if object:
            if recursive:
                if isinstance(self.parent, h5py.Group):
                    self.parent.visititems(_find_object)
            else:
                _find_object(self.parent.name, self.parent)
        if predicate:
            if recursive:
                if isinstance(self.parent, h5py.Group):
                    self.parent.visititems(_find_predicate)
            else:
                _find_predicate(self.parent.name, self.parent)

        if subject:
            if recursive:
                if isinstance(self.parent, h5py.Group):
                    self.parent.visititems(_find_subject)
            else:
                _find_subject(self.parent.name, self.parent)

        common_objects = []
        res = [res_subject, res_predicate, res_object]

        for flag, item in zip([subject, predicate, object], res):
            if flag is not None:
                item_set = set(item)
                if not common_objects:
                    common_objects = item_set
                else:
                    common_objects = common_objects.intersection(item_set)
        return list(common_objects)
        # return list(set(res_subject).intersection(set(res_predicate), set(res_object)))

    @property
    def subject(self) -> Union[str, None]:
        """Returns the subject of the group or dataset"""
        s = self._attr.get(RDF_SUBJECT_ATTR_NAME, None)
        if s is None:
            return
        return s

    def add_subject(self, subject: Union[str, List[str]]):
        """Add a subject to the group or dataset. If the subject already exists, it will not be added again."""
        if isinstance(subject, list):
            data = [str(i) for i in subject]
        else:
            data = str(subject)
        iri_sbj_data = self._attr.get(RDF_SUBJECT_ATTR_NAME, None)
        if iri_sbj_data is None:
            self._attr[RDF_SUBJECT_ATTR_NAME] = data
            return
        if isinstance(iri_sbj_data, list):
            iri_sbj_data.extend(data)
        else:
            iri_sbj_data = [iri_sbj_data, ]
            iri_sbj_data.append(data)
        self._attr[RDF_SUBJECT_ATTR_NAME] = list(set(iri_sbj_data))

    @subject.setter
    def subject(self, rdf_type: Union[str, List[str]]):
        """Sets the subject of the group or dataset. Will overwrite existing subjects.
        If you want to add (append), use add_subject() instead."""
        if isinstance(rdf_type, list):
            rdf_type = [str(i) for i in rdf_type]
            for iri in rdf_type:
                try:
                    HttpUrl(iri)
                except pydantic.ValidationError as e:
                    raise RDFError(f'Invalid IRI: "{iri}" for subject "{self._attr._parent.name}". '
                                   f'Expecting a valid URL. This was validated with pydantic. Pydantic error: {e}')
        else:
            rdf_type = str(rdf_type)
            try:
                HttpUrl(rdf_type)
            except pydantic.ValidationError as e:
                raise RDFError(f'Invalid IRI: "{rdf_type}" for subject "{self._attr._parent.name}". '
                               f'Expecting a valid URL. This was validated with pydantic. Pydantic error: {e}')

        self._attr[RDF_SUBJECT_ATTR_NAME] = rdf_type

    def append_subject(self, subject: str):
        """Append the subject"""
        curr_subjects = self._attr.get(RDF_SUBJECT_ATTR_NAME, [])
        if isinstance(curr_subjects, list):
            if isinstance(subject, list):
                curr_subjects.extend(subject)
            else:
                curr_subjects.append(subject)
            self._attr[RDF_SUBJECT_ATTR_NAME] = curr_subjects
        else:
            if isinstance(subject, list):
                self._attr[RDF_SUBJECT_ATTR_NAME] = [curr_subjects, *subject]
            else:
                self._attr[RDF_SUBJECT_ATTR_NAME] = [curr_subjects, subject]

    @property
    def predicate(self) -> RDF_Predicate:
        """Return the RDF predicate manager"""
        return RDF_Predicate(self._attr)

    @predicate.setter
    def predicate(self, predicate: str):
        iri_sbj_data = self._attr.get(RDF_PREDICATE_ATTR_NAME, None)
        if iri_sbj_data is None:
            iri_sbj_data = {}
        iri_sbj_data.update({'SELF': predicate})
        self._attr[RDF_PREDICATE_ATTR_NAME] = iri_sbj_data

    @property
    def object(self):
        """Return the RDF object manager"""
        return RDF_OBJECT(self._attr)

    def __eq__(self, other: str):
        return str(self.subject) == str(other)

    def __contains__(self, item):
        return item in self._attr.get(RDF_SUBJECT_ATTR_NAME, list())

    def get(self, attr_name: str) -> IRIDict:
        return self.__getitem__(attr_name)

    def __setitem__(self, key, value):
        raise NotImplementedError('RDFManager is read-only. Use properties .name or .data to assign IRI to '
                                  'attribute name or data.')

    def __getitem__(self, item) -> IRIDict:
        return IRIDict({RDF_PREDICATE_ATTR_NAME: self._attr.get(RDF_PREDICATE_ATTR_NAME, {}).get(item, None),
                        RDF_OBJECT_ATTR_NAME: self._attr.get(RDF_OBJECT_ATTR_NAME, {}).get(item, None)},
                       self._attr, item)

    def __delitem__(self, attr_name: str):
        del_iri_entry(self._attr, attr_name)
