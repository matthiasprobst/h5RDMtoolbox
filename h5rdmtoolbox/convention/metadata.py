"""Code which is under development and is likely to go into a dedicated module later."""
import abc
import forge
import h5py
import importlib
import json
import pathlib
import pydantic
import re
import typing
import uuid
import warnings
from pydantic import __all__ as pydantic_all
from typing import Union, Dict, Optional, List, Tuple

import h5rdmtoolbox as h5tbx


class JLDDict(dict):
    """A subclass of dict which has the properties '_type' and '_context'.
    Moreover it is a 'frozen' dictionary, so it cannot be changed.
    """

    def __init__(self, data, metadata=None):
        super().__init__()
        self.update(data)
        self._metadata = metadata or {}

    def __setitem__(self, key: str, item: str) -> None:
        raise AttributeError(f"{self.__class__.__name__} is immutable.")

    def __delitem__(self, key: str) -> None:
        raise AttributeError(f"{self.__class__.__name__} is immutable.")

    @property
    def _type(self):
        return self.get('@type', None)

    @property
    def _context(self):
        return self.get('@context', None)


def is_list_of_dicts(data):
    """Check if data is a list of dicts"""
    if not isinstance(data, list):
        return False
    return all([isinstance(d, dict) for d in data])


def _h5dump(target, data, context, id: Optional[str] = None):
    context = context or {}
    if id:
        target.attrs['@id'] = id
    for k, v in data.items():
        if isinstance(v, dict):
            # group or dataset. depends on the keys
            if 'value' in v:
                new_obj = target.create_dataset(k, data=v['value'])
            else:
                new_obj = target.create_group(k)
            _h5dump(new_obj, v, context)
        elif is_list_of_dicts(v):
            # list of objects. each gets a new group
            n_items = len(v)
            for i, item in enumerate(v):
                _Xd = f'0{len(str(n_items))}d'
                new_group = target.create_group(f'{k}_{i:{_Xd}}')
                _h5dump(new_group, item, context)
        else:
            _type = data.get('@type', None)
            if _type:
                if _type in context:
                    target.iri.subject = context.get(_type).id
            _id = data.get('@id', None)
            if _id is None:
                _id = '_:' + str(uuid.uuid4())

            # for now assuming that it is a pure group. only if
            # value in keys, it is a dataset

            if isinstance(target, h5py.Dataset) and k == 'value':
                continue
            if not k.startswith('@'):
                if k in context:
                    predicate = context.get(k, None)
                    if predicate:
                        # TODO: context can be rdflib.Context or just a dict
                        if hasattr(predicate, 'id'):
                            target.attrs.create(k, v, predicate=predicate.id)
                        else:
                            target.attrs.create(k, v, predicate=predicate)
                    else:
                        target.attrs.create(k, v)
                else:
                    target.attrs.create(k, v)


class _Metadata(abc.ABC):

    @abc.abstractmethod
    def json_dump(self, **kwargs) -> str:
        """return json string"""


class Metadata(_Metadata):
    """Interface class for metadata stored in a file.
    Currently, it can only be read from JSON or JSON-LD files.
    """

    def __init__(self, model: "PydanticBaseModel",
                 context: Dict,
                 ld_type: str = None,
                 extra_fields: Dict = None,
                 property_associations: Dict = None
                 # sub_field_model_types: Dict = None
                 ):
        self._model = model
        self._data = None
        self._extra_fields = extra_fields or {}
        self._property_associations = property_associations or {}
        # self._sub_field_model_types = sub_field_model_types or {}
        self._context = context
        self._type = str(ld_type) if ld_type else None  # jsonld type (@type)
        for k, v in self.get_data().items():
            setattr(self, k, v)

    def __repr__(self) -> str:
        return self.json_dump(indent=2)

    def __str__(self) -> str:
        return str(self.get_data())

    def get_data(self, exclude_none=True) -> JLDDict:
        """Get data as dict"""

        _context_entries = {}

        def _process_json_ld_meta(_data):
            """recursively run through nested dictionary and replace JSON_LD_TYPE key with @type if exists"""
            if isinstance(_data, dict):
                if 'JSON_LD_TYPE' in _data:
                    ld_type = _data.pop('JSON_LD_TYPE', None)
                    if ld_type:
                        _data['@type'] = ld_type
                if 'JSON_LD_CONTEXT' in _data:
                    _context = _data.pop('JSON_LD_CONTEXT', None)
                    if _context:
                        # _data['@context'] = _context
                        _context_entries.update(_context)
                for k in _data.keys():
                    if isinstance(_data[k], dict):
                        _process_json_ld_meta(_data[k])

        if self._data is None:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model_dict = json.loads(self._model.model_dump_json(exclude_none=exclude_none))

                _process_json_ld_meta(model_dict)
                # if self._type:
                #     model_dict.pop('JSON_LD_TYPE', None)
                # else:
                #     self._type = model_dict.pop('JSON_LD_TYPE', None)
                self._data = {
                    **model_dict,
                    **self._extra_fields}
        if _context_entries:
            self._data['@context'] = _context_entries
        return JLDDict(self._data, self)

    def jsonld_dump(self,
                    exclude_none=True,
                    exclude_context: bool = False,
                    indent: int = 2, **kwargs) -> str:
        """Generates a JSON-LD representation of the data"""
        _d = {}
        _type = self._type
        if _type:
            _d['@type'] = _type
        if not exclude_context:
            _d['@context'] = self._context
        data = self.get_data(exclude_none=exclude_none)
        prop_associations = data.pop('JSON_LD_IS_PROPERTY', None) or {}
        for k, v in data.items():
            if isinstance(v, str):
                _d[k] = v
            elif isinstance(v, dict):
                prop_association = prop_associations.get(k, None)
                if prop_association:
                    if prop_association not in _d:
                        _d[prop_association] = []
                    # make sure @type comes first
                    subdict = {}
                    subtype = v.pop('@type', None)
                    if subtype:
                        subdict['@type'] = subtype
                    subdict.update(v)
                    _d[prop_association].append(subdict)

        return json.dumps(_d, indent=indent, **kwargs)

    def json_dump(self, exclude_none=True, **kwargs) -> str:
        """Generates a JSON-LD representation of the data"""
        _d = {'@context': self._context,
              **self.get_data(exclude_none=exclude_none),
              **self._extra_fields}
        return json.dumps(_d, **kwargs)

    # @classmethod
    # def from_json(cls, filename: str) -> _Metadata:
    #     """Load metadata from JSON(-LD) file."""
    #
    #     CONTEXT = '@context'
    #     # it is better to do it manually
    #     # read context file from json:
    #     with open(filename, 'r') as f:
    #         data = json.load(f)
    #
    #     if isinstance(data, dict):
    #         # there can only be a context entry if data is a dict!
    #         # use rdflib.....Context
    #         from rdflib.plugins.shared.jsonld.context import Context
    #         # from rdflib.plugins.parsers.jsonld.Parser.parse():
    #         context: Context = Context(None)
    #         local_context = data.get(CONTEXT, None)
    #         # parse context
    #         if local_context:
    #             context.load(local_context, context.base)
    #             # find all terms here:
    #             # context.terms
    #     else:
    #         raise NotImplementedError('Only dict is supported for now.')
    #
    #     # if context is None:
    #     #     raise ValueError('No context is found in the JSON file.')
    #     return cls(data=data,
    #                context=context.terms)
    #
    #     # with open(filename) as f:
    #     #     jdict = json.load(f)
    #     # return cls(**jdict)

    def write(self, target: h5py.Group, id=None):
        """Write to target group

        Parameters
        ----------
        target: h5py.Group
            Target group to write to
        id: Optional[str]
            Metadata ID. Will create an attribute with key "@id" and value
            according to the input.
        """

        def _rpop(_data, keys=['JSON_LD_IS_PROPERTY', 'JSON_LD_CONTEXT', 'JSON_LD_TYPE', '@context']):
            for k, v in _data.copy().items():
                if k in keys:
                    _data.pop(k)
                if isinstance(v, dict):
                    _rpop(v)

        _data = self.get_data()
        _rpop(_data)
        if self._type:
            target.iri.subject = self._type
        _h5dump(target, _data, self._context, id=id)


def resolve_context(context: Dict) -> Dict:
    """The context dictionary may contain prefixes. This function resolves all IRI constructed
    with prefixes to full IRIs.

    Examples
    --------
    >>> context = {'foaf': 'http://xmlns.com/foaf/0.1/'
    >>>    'first_name': 'foaf:firstName'}
    >>> new_context = resolve_context(context)}
    >>> # new_context = {'first_name': 'http://xmlns.com/foaf/0.1/firstName'}
    """
    if context is None:
        return {}
    context_dict = context.copy()
    prefixes = {}
    for k, v in context_dict.copy().items():
        if not v.startswith('http'):
            # iri is constructed <prefix>:<name>
            prefix = v.split(':', 1)[0]  # e.g. foaf
            if prefix not in prefixes:
                prefix_iri = context_dict.get(prefix)  # e.g. http://xmlns.com/foaf/0.1/
                prefixes[prefix] = prefix_iri
                context_dict.pop(prefix)
            # elif v != prefixes.get(prefix):
            #     raise ValueError(f'Multiple prefix definitions seem to exist. {prefix} is invalid. Exisitng prefixes: {prefixes}')

    for k, v in context_dict.copy().items():
        if not v.startswith('http'):
            prefix, name = v.split(':', 1)
            prefix_iri = prefixes.get(prefix, None)
            if prefix_iri:
                context_dict[k] = f'{prefix_iri}{name}'
    return context_dict


def model_from_json(filename: Union[str, pathlib.Path],
                    name: str,
                    user_types: Optional[Dict[str, "MetadataModel"]] = None,
                    **kwargs):
    """

    Parameters
    ----------
    filename: Union[str, pathlib.Path]
        Path to JSON-LD file
    name: str
        Name of the model
    user_types: Optional[Dict[str, Metadata]]
        User defined types
    kwargs
        Keyword arguments passed to pydantic.BaseModel


    Returns
    -------
    model: pydantic.BaseModel
        Pydantic model
    context: Dict[str, str]
        Context of the model
    ld_type: str
        Type (not in a pythonic meaning but a JSON-LD type, e.g. an identifier) of the model
    """
    with open(filename) as f:
        try:
            model_def_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f'Could not parse {filename} as JSON. Please check the syntax of the file content.'
                             f'\nOrig. err: {e}') from e

    base_types = {
        'str': str,
        'int': int,
        'float': float,
        'bool': bool,
    }
    user_types = user_types or {}
    for k, v in user_types.copy().items():
        if isinstance(v, MetadataModel):
            user_types[k] = v._model_cls

    defined_types = {**base_types, **user_types}

    context = resolve_context(model_def_data.pop('@context', None))

    ld_type = model_def_data.pop('@type', None)
    model_description = model_def_data.pop('@model_description', None)

    def _convert_to_type(type_str):
        if type_str.startswith('List['):
            LIST_TYPE_REGEX = re.compile(r'^List\[(.*)\]$')
            list_match = LIST_TYPE_REGEX.match(type_str)
            if list_match:
                inner_type_str = list_match.group(1).strip()
                if inner_type_str in defined_types:
                    return typing.List[defined_types[inner_type_str]]
                return typing.List[_convert_to_type(inner_type_str)]
            else:
                return type_str
        elif type_str.startswith('Union['):
            LIST_TYPE_REGEX = re.compile(r'^Union\[(.*)\]$')
            union_match = LIST_TYPE_REGEX.match(type_str)
            if union_match:
                inner_type_str = union_match.group(1).strip()
                _inner = _convert_to_type(inner_type_str)
                if isinstance(_inner, list):
                    return typing.Union[tuple(_inner)]
                return typing.Union[_inner]
            else:
                return type_str

        # may be a list of types
        _types = type_str.split(',')
        if len(_types) > 1:
            return [_convert_to_type(_t.strip()) for _t in _types]
        return defined_types.get(type_str, type_str)

    _model_def_data = model_def_data.copy()

    def _parse_model_field(_field_data: Union[str, Dict, List[Dict]]) -> Tuple[str, str]:
        if isinstance(_field_data, dict):
            __type_hint = _field_data.get('type', None)
            if __type_hint is None:
                raise ValueError(f'No type hint is given for field {k} in filename {filename}.')
            __default_value = _field_data.get('default', Ellipsis)
        elif isinstance(_field_data, str):
            __type_hint = _field_data
            __default_value = Ellipsis
        elif isinstance(_field_data, list):
            pass  # TODO evaluated the type hint and default of the list entries
        else:
            raise TypeError(f'Invalid type for field {k} in filename {filename}. '
                            f'Expecting str, dict or list but not {type(_field_data)}')
        return __type_hint, __default_value

    def _parse_type_hint(th):
        if th in defined_types:
            return defined_types[th]
        elif th in pydantic_all:
            __pydantic_package = importlib.import_module("pydantic")
            pydantic_type = getattr(__pydantic_package, th, None)
            if pydantic_type is None:
                raise ValueError(f'pydantic.{th} is not found.')
            return pydantic_type
        else:
            return _convert_to_type(th)

    _is_property = {}  # collects all known properties
    _pop_keys = []
    for k, v in model_def_data.items():
        if isinstance(v, list):
            # fields with a known property IRI
            for _item in v:
                if not isinstance(_item, dict):
                    raise TypeError(f'A list of field definitions must be a list of dicts but got {type(_item)}.\n'
                                    f'Please check file {filename} for field "{k}".')
                for _k, _v in _item.items():
                    _type_hint, _default_value = _parse_model_field(_v)
                    _model_def_data[_k] = (_parse_type_hint(_type_hint), _default_value)
                    # if isinstance(_type_hint, str):
                    #     raise ValueError(f'Could not parse type hint: {_type_hint}. Make sure special (user) types '
                    #                      f'are provided in user_types.')
                    _is_property[_k] = k
                    _pop_keys.append(k)
        else:
            _type_hint, _default_value = _parse_model_field(v)
            _model_def_data[k] = (_parse_type_hint(_type_hint), _default_value)

    for _prop_key in _pop_keys:
        _model_def_data.pop(_prop_key, None)

    # for k, v in _model_def_data.items():
    #     if isinstance(v[0], str):
    #         raise TypeError(f'Unknown type: {k}. Make sure it is a type or defined in user_types.')

    if 'JSON_LD_TYPE' in model_def_data:
        raise ValueError(f'"JSON_LD_TYPE" is a reserved key. Please use @type instead.')

    if 'JSON_LD_CONTEXT' in model_def_data:
        raise ValueError(f'"JSON_LD_CONTEXT" is a reserved key. Please use @context instead.')

    if ld_type:
        _model_def_data['JSON_LD_TYPE'] = (str, ld_type)

    if context:
        _model_def_data['JSON_LD_CONTEXT'] = (Dict, context)

    if _is_property:
        _model_def_data['JSON_LD_IS_PROPERTY'] = (Dict, _is_property)

    model = pydantic.create_model(name,
                                  **_model_def_data,
                                  **kwargs)
    # from pydantic import BaseModel, ConfigDict
    # model.model_config['extra'] = 'allow'
    # model.model_config = ConfigDict(extra='allow')
    model.__doc__ = model_description
    return model, context, ld_type, _is_property


class MetadataModel:
    """Interface to metadata models defined via a pydantic.BaseModel class"""

    def __init__(self, model_cls, context, ld_type, property_association=None):
        self._model_cls = model_cls
        self.context = context
        self.ld_type = ld_type
        self.property_association = property_association or {}

    def __call__(self, **kwargs) -> Metadata:
        exclude_none = kwargs.pop('exclude_none', True)

        extra_fields = {k: v for k, v in kwargs.items() if k not in self.model_fields}

        # sub_field_model_types = {}  # e.g. "manufacturer" in "m4i:tool"

        # parse kwargs:
        def _parse(_name, _data):
            if isinstance(_data, Metadata):
                # sub_field_model_types[_name] = _data._type
                # return _data._model
                return _data._data
            return _data

        pkwargs = {k: _parse(k, v) for k, v in kwargs.items()}

        try:
            model_instance = self._model_cls(**pkwargs)
        except AttributeError as e:
            # try to find the missing type
            import re

            pattern = r"ForwardRef\('([^']*)'\)"
            missing_type_classes = []

            def _get_missing_type(_field):
                annotation = _field.annotation
                matches = re.findall(pattern, str(annotation))

                if matches:
                    missing_type_classes.extend([extracted_string for extracted_string in matches])

                if hasattr(annotation, 'model_fields'):
                    for _sub_field in annotation.model_fields.values():
                        _get_missing_type(_sub_field)

            for field in self._model_cls.__fields__.values():
                _get_missing_type(field)

            if missing_type_classes:
                raise RuntimeError('The model could not be validated because the following types are missing: '
                                   f'{missing_type_classes}. \nThe reason is, that they types were not passed '
                                   'during model creation via the parameter user_types.')
            raise AttributeError(e)

            # str(_model_def_data['quantum_efficiency'][0].model_fields['standard_name'].annotation)
        # model_dict = json.loads(model_instance.model_dump_json())
        return Metadata(
            model=model_instance,
            context=self.context,
            ld_type=self.ld_type,
            extra_fields=extra_fields)

    @property
    def model_fields(self):
        """Return fields of the model"""
        return self._model_cls.__fields__

    @classmethod
    def from_json(cls,
                  filename: Union[str, pathlib.Path],
                  name: str,
                  user_types: Optional[Dict[str, "MetadataModel"]] = None,
                  **kwargs):
        """Create a MetadataMode instance from a JSON file

        Parameters
        ----------
        filename : Union[str, pathlib.Path]
            JSON file containing the model definition
        name : str
            Name of the model
        user_types : Optional[Dict]
            User-defined types, e.g. {'Organization': Organization,
                                      'url': pydantic.HttpUrl}
        kwargs : dict
            Additional keyword arguments passed to pydantic.create_model (Expert
            users only)

        Returns
        -------
        MetadataModel
            MetadataModel instance

        """
        mm = MetadataModel(*model_from_json(filename, name, user_types, **kwargs))
        # now add the metadata fields as arguments of the mm.__call__() method:
        # for k, v in mm.model_fields.items():

        req = {k: v for k, v in mm.model_fields.items() if v.is_required()}
        opt = {k: v for k, v in mm.model_fields.items() if not v.is_required()}

        for name, field in req.items():
            setattr(mm, '__call__', forge.insert(
                forge.arg(name,
                          type=field.annotation),
                before='kwargs')(mm.__call__)
                    )

        for name, field in opt.items():
            setattr(mm, '__call__', forge.insert(
                forge.arg(name,
                          default=field.default,
                          type=field.annotation),
                before='kwargs')(mm.__call__)
                    )
        return mm


if __name__ == '__main__':
    person_model = model_from_json('person_model.json', name='Person')

    codemeta_model = model_from_json('codemeta_model.json', name='CodeMeta',
                                     user_types={'Person': person_model})
    # print(codemeta_model.model_cls.schema_json(indent=2))

    codemeta_model.model_cls(
        codeRepository="git+https://github.com/matthiasprobst/h5RDMtoolbox.git",
        programmingLanguage=['123'],
        name='dawd',
        version='dawd',
        author=[
            {'firstName': 'Matthias', 'lastName': 'Probst'}
        ]
    )

    codemeta_model(
        codeRepository="git+https://github.com/matthiasprobst/h5RDMtoolbox.git",
        programmingLanguage=['123'],
        name='dawd',
        version='dawd',
        author={
            'firstName': 'Matthias', 'lastName': 'Probst'
        }
    )

    from h5rdmtoolbox.utils import download_file

    codemeta_url = 'https://raw.githubusercontent.com/matthiasprobst/h5RDMtoolbox/main/codemeta.json'
    m = Metadata.from_json(filename=download_file(codemeta_url, None))

    with h5tbx.File() as h5:
        codemeta_grp = h5.create_group('codemeta')
        m.write(codemeta_grp)
        h5.dumps()
