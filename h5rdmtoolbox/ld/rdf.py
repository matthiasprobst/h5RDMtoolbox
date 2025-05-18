"""RDF (Resource Description Framework) module for use with HDF5 files"""
import abc
import json
import warnings
from typing import Dict, Union, Optional, List

import h5py
import pydantic
from ontolutils import Thing
from pydantic import HttpUrl

from h5rdmtoolbox.database import lazy
from h5rdmtoolbox.protocols import H5TbxAttributeManager

RDF_OBJECT_ATTR_NAME = 'RDF_OBJECT'
RDF_FILE_OBJECT_ATTR_NAME = 'RDF_FILE_OBJECT'
RDF_PREDICATE_ATTR_NAME = 'RDF_PREDICATE'
RDF_FILE_PREDICATE_ATTR_NAME = 'RDF_FILE_PREDICATE'
RDF_SUBJECT_ATTR_NAME = 'RDF_ID'  # equivalent to @ID in JSON-LD, thus can only be one value!!!
RDF_FILE_SUBJECT_ATTR_NAME = 'RDF_FILE_ID'  # equivalent to @ID in JSON-LD, thus can only be one value!!!
RDF_FILE_TYPE_ATTR_NAME = 'RDF_FILE_TYPE'  # equivalent to @type in JSON-LD, thus can be multiple values.
RDF_TYPE_ATTR_NAME = 'RDF_TYPE'  # equivalent to @type in JSON-LD, thus can be multiple values.

PROTECTED_ATTRIBUTE_NAMES = (
    RDF_OBJECT_ATTR_NAME,
    RDF_FILE_OBJECT_ATTR_NAME,
    RDF_PREDICATE_ATTR_NAME,
    RDF_FILE_PREDICATE_ATTR_NAME,
    RDF_SUBJECT_ATTR_NAME,
    RDF_FILE_TYPE_ATTR_NAME,
    RDF_TYPE_ATTR_NAME,
)

DEFINITION_ATTR_NAME = 'ATTR_DEFINITION'

KNOWN_NAMESPACES = {
    "owl": "http://www.w3.org/2002/07/owl#",
    "dct": "http://purl.org/dc/terms/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "xml": "http://www.w3.org/XML/1998/namespace",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "dcat": "http://www.w3.org/ns/dcat#",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "hdf5": "http://purl.allotrope.org/ontologies/hdf5/1.8#",
    "prov": "http://www.w3.org/ns/prov#",
    "qudt": "http://qudt.org/schema/qudt/",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "ssno": "https://matthiasprobst.github.io/ssno#",
    "vann": "http://purl.org/vocab/vann/",
    "schema": "https://schema.org/",
    "dcterms": "http://purl.org/dc/terms/",
}


class RDFError(Exception):
    """Generic RDF error"""
    pass


def validate_url(url: str) -> str:
    """validate the url with pydantic
    Raises
    ------
    RDFError
        If the URL is invalid, triggered by pydantic.ValidationError

    Returns
    -------
    str
        Returns the original string if the URL is valid. Thus, white spaces are not replaced
        by %20.
    """
    try:
        if not url.startswith("http"):
            if ":" in url:
                prefix, name = url.split(":")
                if prefix not in KNOWN_NAMESPACES:
                    raise RDFError(f'Invalid URL: "{url}". The prefix "{prefix}" is not known. Please provide a '
                                   f'valid and full IRI. Here are the known prefixes: {KNOWN_NAMESPACES}')
                url = KNOWN_NAMESPACES[prefix] + name
            else:
                raise RDFError(f'Invalid URL: "{url}".')
        HttpUrl(url)  # validate the URL, will raise an error if invalid
        return str(url)  # return the original string
    except pydantic.ValidationError as e:
        raise RDFError(f'Invalid URL: "{url}". Expecting a valid URL. This was validated with pydantic. '
                       f'Tested with pydantic: {e}')


def set_predicate(attr: h5py.AttributeManager,
                  attr_name: str,
                  value: str,
                  rdf_predicate_attr_name=RDF_PREDICATE_ATTR_NAME) -> None:
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

    iri_name_data = attr.get(rdf_predicate_attr_name, None)
    if iri_name_data is None:
        iri_name_data = {}
    iri_name_data.update({attr_name: value})
    attr[rdf_predicate_attr_name] = iri_name_data


def set_object(attr: h5py.AttributeManager,
               attr_name: str,
               data: str,
               rdf_object_attr_name=RDF_OBJECT_ATTR_NAME) -> None:
    """Set the class of an attribute"""
    if isinstance(data, (list, tuple)):
        for d in data:
            set_object(attr, attr_name, d, rdf_object_attr_name)
        return

    iri_data_data = attr.get(rdf_object_attr_name, None)

    if iri_data_data is None:
        iri_data_data = {}

    if isinstance(data, Thing):
        data = data.get_jsonld_dict(assign_bnode=False)
    elif isinstance(data, dict):
        # assuming it is a JSON-LD dict
        if not "@type" in data:
            raise RDFError(f"The input data is interpreted as JSON-LD, but no @type is found: {data}")
    else:
        try:
            data = str(HttpUrl(data))
        except pydantic.ValidationError as e:
            raise RDFError(f'Invalid IRI: "{data}" for attr name "{attr_name}". '
                           f'Expecting a valid URL. This was validated with pydantic. Pydantic error: {e}')
    curr_data = iri_data_data.get(attr_name, None)
    if curr_data is None:
        iri_data_data.update({attr_name: data})
    else:
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
    attr[rdf_object_attr_name] = iri_data_data
    # iri_data_data.update({attr_name: data})
    # attr[rdf_object_attr_name] = iri_data_data


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
        if isinstance(o, str) and o.startswith("{"):
            """assuming, that it is a json string"""
            return json.loads(o)
        return o

    @object.setter
    def object(self, value):
        if isinstance(value, (list, tuple)):
            set_object(self._attr, self._attr_name, value[0])
            for v in value[1:]:
                append(self._attr, self._attr_name, v, RDF_OBJECT_ATTR_NAME)
        elif isinstance(value, str) and value.startswith("{"):
            """assuming, that it is a json string"""
            set_object(self._attr, self._attr_name, json.loads(value))
        else:
            set_object(self._attr, self._attr_name, value)

    @property
    def definition(self):
        """Return the definition of the attribute"""
        return self._attr.get(DEFINITION_ATTR_NAME, {}).get(self._attr_name, None)

    @definition.setter
    def definition(self, definition: str):
        """Define the attribute. JSON-LD export will interpret this as SKOS.definition."""
        attr_def = self._attr.get(DEFINITION_ATTR_NAME, {})
        attr_def.update({self._attr_name: definition})
        self._attr[DEFINITION_ATTR_NAME] = attr_def


class _RDFPO(abc.ABC):
    """Abstract class for predicate (P) and object (O)"""
    IRI_ATTR_NAME = None

    def __init__(self, attr):
        self._attr = attr

    @abc.abstractmethod
    def __setiri__(self, key, value):
        """Set IRI to an attribute"""

    # @property
    # def parent(self):
    #     """Return the parent object"""
    #     return self._attr._parent

    def get(self, item, default=None):
        attrs = self._attr.get(self.IRI_ATTR_NAME, None)
        if attrs is None:
            return default
        if item is None:
            return attrs.get('SELF', default)
        if isinstance(attrs, dict):
            return attrs.get(item, default)
        assert isinstance(attrs, str)
        return json.loads(attrs).get(item, default)

    def __getitem__(self, item) -> Union[str, None]:
        return self.get(item, default=None)

    # def __delitem__(self, key):
    #     iri_data_data = self._attr.get(self.IRI_ATTR_NAME, None)
    #     if iri_data_data is None:
    #         iri_data_data = {}
    #     iri_data_data.pop(key, None)
    #     self._attr[self.IRI_ATTR_NAME] = iri_data_data

    def __setitem__(self, key, value: str):
        if key not in self._attr:
            raise KeyError(f'No attribute "{key}" found. Cannot assign an IRI to a non-existing attribute.')
        self.__setiri__(key, value)

    def __delitem__(self, key):
        iri_data_data = self._attr.get(self.IRI_ATTR_NAME, None)
        if iri_data_data is None:
            iri_data_data = {}
        iri_data_data.pop(key, None)
        self._attr[self.IRI_ATTR_NAME] = iri_data_data

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

    def __str__(self) -> str:
        return f'{self.__class__.__name__} ({self.parent.name})'

    def __repr__(self) -> str:
        return self.__str__()

    def __setattr__(self, key, value):
        if key not in ('_attr',
                       'subject',
                       'predicate',
                       'type'):
            raise KeyError(f"Cannot set {key}. Only subject, predicate and type can be set!")
        super().__setattr__(key, value)

    @property
    def parent(self):
        """Return the parent object"""
        return self._attr._parent

    def find(self,
             *,
             rdf_subject: Optional[str] = None,
             rdf_type: Optional[str] = None,
             rdf_predicate: Optional[str] = None,
             rdf_object: Optional[str] = None,
             recursive: bool = True) -> List:
        """Find the common objects that have the subject, predicate and object

        Parameters
        ----------
        rdf_subject : str
            The subject to search for (@id in JSON-LD syntax)
        rdf_type : str
            The type to search for (@type in JSON-LD syntax)
        rdf_predicate : str
            The predicate to search for
        rdf_object : str
            The object to search for
        recursive : bool
            If True, search recursively in the parent group

        Returns
        -------
        List
            A list of objects (h5tbx.Dataset or h5tbx.Group) that have the subject, predicate and object
        """
        res_subject = []
        res_types = []
        res_predicate = []
        res_object = []

        def _find_subject(name, node):
            rdfm = RDFManager(node.attrs)
            _subject: str = rdfm.subject
            if _subject == str(rdf_subject):
                res_subject.append(node)

        def _find_type(name, node):
            rdfm = RDFManager(node.attrs)
            if not isinstance(rdfm.type, list):
                types = [rdfm.type]
            else:
                types = rdfm.type
            if str(rdf_type) in types:
                res_types.append(node)

        def _find_predicate(name, node):
            rdfm = RDFManager(node.attrs)
            for k in rdfm.predicate.values():
                if k == str(rdf_predicate):
                    res_predicate.append(node)

        def _find_object(name, node):
            rdfm = RDFManager(node.attrs)
            if str(rdf_object) in rdfm.object.values():
                res_object.append(node)
            if str(rdf_object) in [s for s in list(node.attrs.values()) if isinstance(s, str)]:
                res_object.append(node)

        if rdf_object:
            _find_object(self.parent.name, self.parent)
            if recursive and isinstance(self.parent, h5py.Group):
                self.parent.visititems(_find_object)

        if rdf_type is not None:
            _find_type(self.parent.name, self.parent)
            if recursive and isinstance(self.parent, h5py.Group):
                self.parent.visititems(_find_type)

        if rdf_predicate:
            _find_predicate(self.parent.name, self.parent)
            if recursive and isinstance(self.parent, h5py.Group):
                self.parent.visititems(_find_predicate)

        if rdf_subject:
            _find_subject(self.parent.name, self.parent)
            if recursive:
                if isinstance(self.parent, h5py.Group):
                    self.parent.visititems(_find_subject)

        common_objects = []
        res = [res_subject, res_types, res_predicate, res_object]

        for flag, item in zip([rdf_subject, res_types, rdf_predicate, rdf_object], res):
            if flag:
                item_set = set(item)
                if not common_objects:
                    common_objects = item_set
                else:
                    common_objects = common_objects.intersection(item_set)
        return [lazy.lazy(c) for c in list(common_objects)]

    @property
    def type(self) -> Union[str, List[str], None]:
        """Returns the RDF subject (@type in JSON-LD syntax) of the group or dataset.
        Note, that it can be None, if no type is set and a list if multiple types are set.
        Else it will return a string.

        Returns
        -------
        Union[str, List[str], None]
        """
        if '@TYPE' in self._attr:
            warnings.warn('The attribute @TYPE is deprecated. Use RDF_TYPE instead.', DeprecationWarning)
            s = self._attr.get("@TYPE", None)
        else:
            s = self._attr.get(RDF_TYPE_ATTR_NAME, None)
        if s is None:
            return
        return s

    @type.setter
    def type(self, rdf_type: Union[str, List[str]]):
        """Add a rdf type (@type in JSON-LD syntax) to the group or dataset.
        If the subject already exists, it will not be added again."""
        if isinstance(rdf_type, list):
            data = [validate_url(str(i)) for i in rdf_type]
        else:
            data = validate_url(str(rdf_type))

        # get the attribute
        if '@TYPE' in self._attr:
            warnings.warn('The attribute @TYPE is deprecated. Use RDF_TYPE instead.', DeprecationWarning)
            iri_sbj_data = self._attr.get('@TYPE', None)
        else:
            iri_sbj_data = self._attr.get(RDF_TYPE_ATTR_NAME, None)

        if iri_sbj_data is None:
            self._attr[RDF_TYPE_ATTR_NAME] = data
            return

        if isinstance(iri_sbj_data, list):
            if isinstance(data, list):
                iri_sbj_data.extend(data)
            else:
                iri_sbj_data.append(data)
        else:
            iri_sbj_data = [iri_sbj_data, ]
            if isinstance(data, list):
                iri_sbj_data.extend(data)
            else:
                iri_sbj_data.append(data)

        # ensure, that the list contains unique values:
        self._attr[RDF_TYPE_ATTR_NAME] = list(set(iri_sbj_data))

    @type.deleter
    def type(self):
        """Delete all (!) types of the group or dataset"""
        if '@TYPE' in self._attr:
            warnings.warn('The attribute @TYPE is deprecated. Use RDF_TYPE instead.', DeprecationWarning)
            del self._attr['@TYPE']
        del self._attr[RDF_TYPE_ATTR_NAME]

    def pop_type(self, rdf_type: str):
        """Remove a type from the list of types"""
        rdf_type = str(rdf_type)
        iri_type_data = self._attr.get(RDF_TYPE_ATTR_NAME, None)
        if iri_type_data is None:
            return
        if isinstance(iri_type_data, list):
            iri_type_data.remove(rdf_type)
        else:
            if iri_type_data == rdf_type:
                del self._attr[RDF_TYPE_ATTR_NAME]
                return
        if len(iri_type_data) == 1:
            self._attr[RDF_TYPE_ATTR_NAME] = iri_type_data[0]
        else:
            self._attr[RDF_TYPE_ATTR_NAME] = iri_type_data

    @property
    def predicate(self) -> RDF_Predicate:
        """Return the RDF predicate manager"""
        return RDF_Predicate(self._attr)

    @predicate.setter
    def predicate(self, predicate: str):
        """Setting the predicate for a group or dataset, not for an attribute."""
        if not isinstance(predicate, str):
            raise TypeError(f'Expecting a string or URL. Got {type(predicate)}. Note, that a predicate of '
                            'a group or dataset can only be one value. If you meant to set one or multiple RDF types, '
                            'use .type instead.')
        iri_predicate_data = self._attr.get(RDF_PREDICATE_ATTR_NAME, None)
        if iri_predicate_data is None:
            iri_predicate_data = {}
        iri_predicate_data.update({'SELF': predicate})
        self._attr[RDF_PREDICATE_ATTR_NAME] = iri_predicate_data

    @predicate.deleter
    def predicate(self):
        """Delete the predicate of the group or dataset. It does not delete the predicate of the attributes.
        Use `del h5.rdf.predicate[<attr_name>]` instead."""
        iri_predicate_data = self._attr.get(RDF_PREDICATE_ATTR_NAME, None)
        if 'SELF' in iri_predicate_data:
            del iri_predicate_data['SELF']
        self._attr[RDF_PREDICATE_ATTR_NAME] = iri_predicate_data

    @property
    def object(self):
        """Return the RDF object manager"""
        return RDF_OBJECT(self._attr)

    @property
    def subject(self) -> Optional[str]:
        """Return the RDF subject (a URL), which is equivalent to the @ID in JSON-LD syntax"""
        if RDF_SUBJECT_ATTR_NAME not in self._attr:
            return
        return self._attr[RDF_SUBJECT_ATTR_NAME]

    @subject.deleter
    def subject(self):
        """Delete the subject (the @ID in JSON-LD syntax)"""
        del self._attr[RDF_SUBJECT_ATTR_NAME]

    @subject.setter
    def subject(self, jsonld_id: Union[str, HttpUrl]):
        """Set the RDF subject, which is the @ID in JSON-LD syntax.
        Hence, a valdi URL is required. This is validated by pydantic!

        Raises
        ------
        TypeError
            If the subject is not a string or URL
        RDFError
            If the URL is invalid
        """
        if not isinstance(jsonld_id, str):
            raise TypeError(f'Expecting a string or URL. Got {type(jsonld_id)}. Note, that a subject '
                            'can only be one value. If you meant to set one or multiple RDF types, '
                            'use .type instead.')
        self._attr[RDF_SUBJECT_ATTR_NAME] = validate_url(jsonld_id)

    # aliases:
    rdf_object = object
    rdf_predicate = predicate
    rdf_subject = subject

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
        if item not in self._attr:
            raise KeyError(f'Attribute "{item}" not found in {self.parent.name}.')
        return IRIDict({RDF_PREDICATE_ATTR_NAME: self._attr.get(RDF_PREDICATE_ATTR_NAME, {}).get(item, None),
                        RDF_OBJECT_ATTR_NAME: self._attr.get(RDF_OBJECT_ATTR_NAME, {}).get(item, None)},
                       self._attr, item)

    def delete(self, name):
        """Deleting RDF associated to name"""
        if name in self.predicate:
            del self.predicate[name]
        if name in self.object:
            del self.object[name]


class FileIRIDict(Dict):

    def __init__(self, _dict: Dict, attr: h5py.AttributeManager = None, attr_name: str = None):
        super().__init__(_dict)
        self._attr = attr
        self._attr_name = attr_name

    @property
    def predicate(self):
        p = self[RDF_FILE_PREDICATE_ATTR_NAME]
        if p is not None:
            return p
        return p

    @predicate.setter
    def predicate(self, value):
        set_predicate(self._attr,
                      self._attr_name,
                      value,
                      rdf_predicate_attr_name=RDF_FILE_PREDICATE_ATTR_NAME)

    @property
    def object(self):
        p = self[RDF_FILE_OBJECT_ATTR_NAME]
        if p is not None:
            return p
        return p

    @object.setter
    def object(self, value):
        set_object(self._attr,
                   self._attr_name, value,
                   rdf_object_attr_name=RDF_FILE_OBJECT_ATTR_NAME)


class File_RDF_Predicate(_RDFPO):
    """IRI class attribute manager"""

    IRI_ATTR_NAME = RDF_FILE_PREDICATE_ATTR_NAME

    def __setiri__(self, key, value):
        set_predicate(self._attr, key, value)


class File_RDF_Object(_RDFPO):
    """IRI class attribute manager"""

    IRI_ATTR_NAME = RDF_FILE_OBJECT_ATTR_NAME

    def __setiri__(self, key, value):
        set_object(self._attr, key, value, rdf_object_attr_name=RDF_FILE_OBJECT_ATTR_NAME)


class FileRDFManager:
    """Similar to RDFManager, but to assign semantic data to the file rather than to a group or dataset"""

    def __init__(self, attr: H5TbxAttributeManager = None):
        self._attr = attr

    def __getitem__(self, item) -> FileIRIDict:
        """Overwrite parent implementation, because other attr name is used"""
        ret = self.get(item, None)
        if ret is None:
            raise KeyError(f'Attribute "{item}" not found in "{self._attr._parent.name}".')
        return ret

    def get(self, item, default=None):
        if item not in self._attr:
            return default
        return FileIRIDict(
            {
                RDF_FILE_PREDICATE_ATTR_NAME: self._attr.get(RDF_FILE_PREDICATE_ATTR_NAME, {}).get(item, None),
                RDF_FILE_OBJECT_ATTR_NAME: self._attr.get(RDF_FILE_OBJECT_ATTR_NAME, {}).get(item, None)},
            self._attr, item)

    @property
    def subject(self) -> Optional[str]:
        """Return the RDF subject (a URL), which is equivalent to the @ID in JSON-LD syntax"""
        if RDF_FILE_SUBJECT_ATTR_NAME not in self._attr:
            return
        return self._attr[RDF_FILE_SUBJECT_ATTR_NAME]

    @subject.setter
    def subject(self, identifier: Union[str, HttpUrl]):
        """Set the RDF subject, which is the @ID in JSON-LD syntax.
        Hence, a valdi URL is required. This is validated by pydantic!

        Raises
        ------
        TypeError
            If the subject is not a string or URL
        RDFError
            If the URL is invalid
        """
        if not isinstance(identifier, str):
            raise TypeError(f'Expecting a string or URL. Got {type(identifier)}. Note, that a subject '
                            'can only be one value. If you meant to set one or multiple RDF types, '
                            'use .type instead.')
        self._attr[RDF_FILE_SUBJECT_ATTR_NAME] = validate_url(identifier)

    @subject.deleter
    def subject(self):
        """Delete the subject (the @ID in JSON-LD syntax)"""
        del self._attr[RDF_FILE_SUBJECT_ATTR_NAME]

    @property
    def predicate(self) -> File_RDF_Predicate:
        """Return the RDF predicate manager"""
        rdf_pred = File_RDF_Predicate(self._attr)
        rdf_pred.IRI_ATTR_NAME = RDF_FILE_PREDICATE_ATTR_NAME
        return rdf_pred

    @predicate.setter
    def predicate(self, value):
        set_predicate(self._attr, self._attr_name, value, rdf_predicate_attr_name=RDF_FILE_PREDICATE_ATTR_NAME)

    @property
    def object(self) -> File_RDF_Object:
        """Return the RDF predicate manager"""
        rdf_obj = File_RDF_Object(self._attr)
        rdf_obj.IRI_ATTR_NAME = RDF_FILE_OBJECT_ATTR_NAME
        return rdf_obj

    @object.setter
    def object(self, value):
        set_object(self._attr, self._attr_name, value, rdf_predicate_attr_name=RDF_FILE_OBJECT_ATTR_NAME)

    @property
    def type(self) -> Union[str, List[str], None]:
        """Returns the RDF subject (@type in JSON-LD syntax) of the HDF5 file (not the root group!)
        If nothing has been set before, hdf5:File is returned.

        Returns
        -------
        Union[str, List[str], None]
        """
        return self._attr.get(RDF_FILE_TYPE_ATTR_NAME, None)

    @type.setter
    def type(self, rdf_type: Union[str, List[str]]):
        """Add a rdf type (@type in JSON-LD syntax) to the hdf5 file (not the root group!)"""
        if isinstance(rdf_type, list):
            data = [validate_url(str(i)) for i in rdf_type]
        else:
            data = validate_url(str(rdf_type))

        # get the attribute
        iri_sbj_data = self._attr.get(RDF_FILE_TYPE_ATTR_NAME, None)

        if iri_sbj_data is None:
            self._attr[RDF_FILE_TYPE_ATTR_NAME] = data
            return

        if isinstance(iri_sbj_data, list):
            if isinstance(data, list):
                iri_sbj_data.extend(data)
            else:
                iri_sbj_data.append(data)
        else:
            iri_sbj_data = [iri_sbj_data, ]
            if isinstance(data, list):
                iri_sbj_data.extend(data)
            else:
                iri_sbj_data.append(data)

        # ensure, that the list contains unique values:
        self._attr[RDF_FILE_TYPE_ATTR_NAME] = list(set(iri_sbj_data))
