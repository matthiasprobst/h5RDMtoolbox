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
from typing import Union, Dict, Optional

import h5rdmtoolbox as h5tbx


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

    def __init__(self, model: "PydanticBaseModel", context: Dict, ld_type: str = None,
                 extra_fields: Dict = None):
        self._model = model
        self._data = None
        self._extra_fields = extra_fields or {}
        self._context = context
        self._ld_type = str(ld_type) if ld_type else None  # jsonld type (@type)
        for k, v in self.get_data().items():
            setattr(self, k, v)

    def __repr__(self) -> str:
        return self.get_data().__repr__()

    def __str__(self) -> str:
        return str(self.get_data())

    def get_data(self, exclude_none=True) -> Dict:
        """Get data as dict"""
        if self._data is None:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self._data = {**json.loads(self._model.model_dump_json(exclude_none=exclude_none)),
                              **self._extra_fields}
        return self._data

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
        if self._ld_type:
            target.iri.subject = self._ld_type
        _h5dump(target, self.get_data(), self._context, id=id)
        # data = self.data
        # for k, v in data.items():
        #     if isinstance(v, dict):
        #
        #     _type = data.get('@type', None)
        #     if _type:
        #         if _type in self.context:
        #             target.iri.subject = self.context.get(_type).id
        #     _id = data.get('@id', None)
        #     if _id is None:
        #         _id = '_:' + str(uuid.uuid4())
        #
        #     # for now assuming that it is a pure group. only if
        #     # value in keys, it is a dataset
        #     if not k.startswith('@'):
        #         if k in self.context:
        #             target.attrs.create(k, v, predicate=self.context.get(k).id)
        #         else:
        #             target.attrs.create(k, v)
        # if k == '@id':
        #     _id = v
        # creating a new node (group) in the h5 file


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
        model_def_data = json.load(f)

    base_types = {
        'str': str,
        'int': int,
        'float': float,
        'bool': bool,
    }
    user_types = user_types or {}
    for k, v in user_types.copy().items():
        # print(f'parsing {k} with {v}')
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
    for k, v in model_def_data.items():
        if isinstance(v, dict):
            raise TypeError(f'Nested dictionaries are not supported: {k}: {v}')
        if not isinstance(v, (tuple, list)):
            _model_def_data[k] = (v, ...)
        if isinstance(v, list):
            if v[1] == '...':
                v[1] = Ellipsis
            _model_def_data[k] = (v[0], v[1])
        _type, _default = _model_def_data[k]
        if _type in defined_types:
            _model_def_data[k] = (defined_types[_type], _default)
        elif _type in pydantic_all:
            pd = importlib.import_module("pydantic")
            pydatnic_type = getattr(pd, _type, None)
            if pydatnic_type is None:
                raise ValueError(f'pydantic.{_type} is not found.')
            _model_def_data[k] = (pydatnic_type, _default)
        else:
            _model_def_data[k] = (_convert_to_type(_type), _default)

    for k, v in _model_def_data.items():
        if isinstance(v[0], str):
            raise TypeError(f'Unknown type: {k}. Make sure it is a type or defined in user_types.')
    model = pydantic.create_model(name,
                                  **_model_def_data,
                                  **kwargs)
    # from pydantic import BaseModel, ConfigDict
    # model.model_config['extra'] = 'allow'
    # model.model_config = ConfigDict(extra='allow')
    model.__doc__ = model_description
    return model, context, ld_type


class MetadataModel:
    """Interface to metadata models defined via a pydantic.BaseModel class"""

    def __init__(self, model_cls, context, ld_type):
        self._model_cls = model_cls
        self.context = context
        self.ld_type = ld_type

    def __call__(self, **kwargs) -> Metadata:
        exclude_none = kwargs.pop('exclude_none', True)

        extra_fields = {k: v for k, v in kwargs.items() if k not in self.model_fields}

        # parse kwargs:
        def _parse(_name, _data):
            if isinstance(_data, Metadata):
                return _data._model
            return _data

        pkwargs = {k: _parse(k, v) for k, v in kwargs.items()}

        model_instance = self._model_cls(**pkwargs)
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

    # Organization = model_from_json('organization_model_definition.json', name='Organization')
    # LaserModel = model_from_json('my_laser_model.json', name='laser',
    #                              user_types={'Organization': Organization})
    #
    # Organization(name='Quantel', url='https://www.quantel-laser.com/')
    #
    # # print(MyModel.schema_json(indent=2))
    #
    # LaserModel(
    #     model='TwinBSL',
    #     manufacturer={'name': 'Quantel', 'url': 'https://www.quantel-laser.com/'}
    # )


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
