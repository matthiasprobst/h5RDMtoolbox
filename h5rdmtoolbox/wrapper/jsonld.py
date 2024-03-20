import h5py
import json
import numpy as np
import pathlib
import rdflib
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import RDF
from typing import Dict, Optional, Union, List
from typing import Iterable, Tuple, Any

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import consts
from h5rdmtoolbox.convention import hdf_ontology
from ontolutils.classes.utils import split_URIRef


def _merge_entries(entries: Dict, clean: bool = True) -> Dict:
    _entries = entries.copy()

    ids = list(entries.keys())

    delete_candidates = []

    for _id, entry in entries.items():
        for k, v in entry.items():
            if clean and len(entry) == 1:
                # remove empty entry, Note, this could be a problem if the entry references elsewhere...
                delete_candidates.append(_id)
                continue
            if k not in ('@id', '@type'):
                if isinstance(v, list):
                    if all([i in ids for i in v]):
                        _entries[_id][k] = [_entries.pop(i) for i in v]

                elif v in ids:
                    _entries[_id][k] = _entries.pop(v)
    if clean:
        for dc in delete_candidates:
            _entries.pop(dc, None)
    return _entries


def _get_id_from_attr_value(_av, file_url):
    if isinstance(_av, (h5py.Dataset, h5py.Group)):
        return _get_id(_av, file_url)
    else:
        return Literal(_av)


def _get_id(_node, local=None) -> URIRef:
    """if an attribute in the node is called "@id", use that, otherwise use the node name"""
    _id = _node.attrs.get('@id', None)
    if local is not None:
        local = rf'file://{_node.hdf_filename.resolve().absolute()}'
        return URIRef(local + _node.name[1:])
    if _id is None:
        return BNode()
        # _id = _node.attrs.get(get_config('uuid_name'),
        #                       local + _node.name[1:])  # [1:] because the name starts with a "/"
    return URIRef(_id)


def is_list_of_dict(data) -> bool:
    """Check if a list is a list of dictionaries."""
    if not isinstance(data, list):
        return False
    if len(data) == 0:
        return False
    return all([isinstance(i, dict) for i in data])


def to_hdf(grp,
           *,
           data: Dict = None,
           source: Union[str, pathlib.Path] = None,
           predicate=None,
           context: Dict = None) -> None:
    """write json-ld data to group

    .. note::

        Either data (as dict) or source (as filename) must be given.

    Parameters
    ----------
    grp : h5py.Group
        The group to write to
    data : Dict = None
        The data to write
    source : Union[str, pathlib.Path] = None
        The source file to read from
    predicate : None
        The predicate to use for the group
    context : Dict = None
        The context to use. It may be given in the data or source file.
        The context dictionary translate the keys in the data to IRIs.

    Returns
    -------
    None
    """
    if data is None and source is None:
        raise ValueError('Either data or source must be given')
    if data is None:
        with open(source, 'r') as f:
            data = json.load(f)
    else:
        assert isinstance(data, dict), f'Expecting dict, got {type(data)}'

    if predicate:
        grp.rdf.predicate = predicate

    data_context = data.pop('@context', None)
    if data_context is None:
        data_context = {}
    if context is not None:
        data_context.update(context)
    data_context['rdfs'] = 'http://www.w3.org/2000/01/rdf-schema#'
    data_context['schema'] = 'https://schema.org/'

    for k, v in data.items():

        if k == '@id':
            rdf_predicate = None
            value_predicate = k
        else:
            # spit predicate:
            ns_predicate, value_predicate = split_URIRef(k)

            # ns_predicate can be something like None, "schema" or "https://schema.org/"
            if ns_predicate is None:
                rdf_predicate = data_context.get(k, None)
            elif ns_predicate.startswith('http'):
                rdf_predicate = k
            else:
                _ns = data_context.get(ns_predicate, None)
                if _ns is not None:
                    rdf_predicate = f'{_ns}{value_predicate}'
                else:
                    rdf_predicate = value_predicate

        if isinstance(v, dict):
            print(f'create group {k} in {grp.name}')
            if k not in grp:
                to_hdf(grp.create_group(value_predicate), data=v, predicate=rdf_predicate, context=data_context)
        elif isinstance(v, list):
            if is_list_of_dict(v):
                for i, entry in enumerate(v):
                    sub_grp_name = f'{k}{i + 1}'
                    if sub_grp_name in grp:
                        sub_grp = grp[sub_grp_name]
                    else:
                        sub_grp = grp.create_group(sub_grp_name)
                        sub_grp.rdf.predicate = data_context.get(k, None)
                    to_hdf(sub_grp, data=entry, context=data_context)
            else:
                grp.attrs[k, data_context.get(k, None)] = v
        else:
            # maybe value_object is a IRI?!
            ns_object, value_object = split_URIRef(v)

            if ns_object is None:
                rdf_object = data_context.get(k, None)
            elif value_object.startswith('http'):
                rdf_object = k
            else:
                _ns = data_context.get(ns_object, None)
                if _ns is not None:
                    rdf_object = f'{_ns}{value_object}'
                else:
                    rdf_object = value_object
            if k == '@type':
                grp.attrs.create(name=k, data=rdf_object)
            elif k == '@id':
                grp.attrs.create(name=k, data=v)
            else:
                grp.attrs.create(name=value_predicate, data=value_object, rdf_predicate=rdf_predicate)


# def to_hdf(jsonld_filename, grp: h5py.Group) -> None:
#     """Takes a .jsonld file and writes it into a HDF5 group"""
#     if not isinstance(grp, h5py.Group):
#         raise TypeError(f'Expecting h5py.Group, got {type(grp)}')
#
#     if not isinstance(jsonld_filename, (str, pathlib.Path)):
#         raise TypeError(f'Expecting str or pathlib.Path, got {type(jsonld_filename)}')
#
#     def _to_hdf(_h5: h5py.Group, jdict: Dict):
#         """Takes a .jsonld file and writes it into a HDF5 group"""
#         for k, v in jdict.items():
#             if isinstance(v, dict):
#                 if k == 'has parameter':
#                     label = v.get('label', '@id')
#                     _h5.attrs[k] = v['@id']
#                     if v.get('has numerical value', None):
#                         ds = _h5.create_dataset(label, data=literal_eval(v['has numerical value']), track_order=True)
#                         for kk, vv in v.items():
#                             if kk != 'has numerical value':
#                                 ds.attrs[kk] = vv
#                     else:
#                         grp = _h5.create_group(label, track_order=True)
#                         _to_hdf(grp, v)
#                 else:
#                     grp = _h5.create_group(k, track_order=True)
#                     _to_hdf(grp, v)
#             elif isinstance(v, list):
#                 list_grp = _h5.create_group(k, track_order=True)
#                 for i, item in enumerate(v):
#                     # _h5[k] =
#                     obj_name = item.get('@id', str(i))
#                     if item.get('has numerical value', None):
#                         obj = list_grp.create_dataset(obj_name, data=literal_eval(item['has numerical value']),
#                                                       track_order=True)
#                         for kk, vv in item.items():
#                             if kk != 'has numerical value':
#                                 obj.attrs[kk] = vv
#                     else:
#                         obj = list_grp.create_group(obj_name, track_order=True)
#                     _to_hdf(obj, item)
#             else:
#                 _h5.attrs[k] = v
#
#     with open(jsonld_filename, 'r') as f:
#         return _to_hdf(grp, json.load(f))


def serialize(grp,
              iri_only=False,
              local=None,
              recursive: bool = True,
              compact: bool = False,
              context: Dict = None
              ) -> Dict:
    """using rdflib graph"""
    if isinstance(grp, (str, pathlib.Path)):
        from .core import File
        with File(grp) as h5:
            return serialize(h5,
                             iri_only,
                             local,
                             recursive=recursive,
                             compact=compact,
                             context=context)

    hasParameter = URIRef('http://w3id.org/nfdi4ing/metadata4ing#hasParameter')

    # global _context
    _context = {}
    context = context or {}
    _context.update(context)  # = context or {}
    _context['foaf'] = 'http://xmlns.com/foaf/0.1/'
    _context['prov'] = 'http://www.w3.org/ns/prov#'
    _context['schema'] = 'https://schema.org/'
    _context['rdfs'] = 'http://www.w3.org/2000/01/rdf-schema#'

    iri_dict = {}

    def add_node(name, obj):
        node = iri_dict.get(obj.name, None)
        if node is None:
            node = rdflib.URIRef(_get_id(obj, local=local))
            iri_dict[obj.name] = node

        # node = rdflib.URIRef(f'_:{obj.name}')
        if isinstance(obj, h5py.File):
            return

        node_type = obj.rdf.subject
        # if the node_type is None, attributes could still have RDF types. In this case, consider the node as a
        # NumericalVariable or TextVariable

        if node_type is None:
            rdf_predicate_dict = obj.attrs.get(consts.RDF_PREDICATE_ATTR_NAME, None)
            if rdf_predicate_dict and len(rdf_predicate_dict) > 0:
                if isinstance(obj, h5py.Dataset):
                    if obj.dtype.kind == 'S':
                        node_type = "http://w3id.org/nfdi4ing/metadata4ing#TextVariable"
                    elif obj.dtype.kind in ('i', 'u', 'f'):
                        node_type = "http://w3id.org/nfdi4ing/metadata4ing#NumericalVariable"
                    else:
                        node_type = "http://www.molmod.info/semantics/pims-ii.ttl#Variable"
                else:
                    node_type = "http://schema.org/Thing"  # schema:Thing (The most generic type of item.)
        if node_type:
            g.add((node, RDF.type, rdflib.URIRef(node_type)))
            # if isinstance(obj, h5py.Dataset):
            #     # node is Parameter
            #     g.add((node, RDF.type, URIRef("http://www.molmod.info/semantics/pims-ii.ttl#Variable")))
            #     # g.add((node, RDF.type, URIRef("hdf:Dataset")))
            #     # parent gets "hasParameter"
            #     # parent_node = f'_:{obj.parent.name}'# _get_id(obj.parent, local)
            #     parent_node = _get_id(obj.parent, local)
            #     g.add((parent_node, hasParameter, node))

            # only go through attributes if the parent object is a RDF type
            for ak, av in obj.attrs.items():
                if not ak.isupper() and not ak.startswith('@'):
                    if isinstance(av, (list, tuple)):
                        value = [_get_id_from_attr_value(_av, local) for _av in av]
                    else:
                        value = _get_id_from_attr_value(av, local)

                    # g.add((node, URIRef(ak), Literal(av)))
                    predicate = obj.rdf.predicate.get(ak, None)

                    # only add if not defined in context:
                    if predicate and predicate not in _context:
                        # irikey = str(obj.rdf.predicate[ak])
                        if isinstance(value, (list, tuple)):
                            for v in value:
                                g.add((node, URIRef(predicate), v))
                        else:
                            g.add((node, URIRef(predicate), value))

                    if predicate is None and not iri_only:
                        g.add((node, URIRef(ak), value))

        # now check if any of the groups in obj is associated with a predicate
        if isinstance(obj, h5py.Group):
            for grp_name, grp in obj.items():
                if isinstance(grp, h5py.Group):
                    predicate = grp.rdf.predicate['SELF']
                    if predicate:
                        new_node = iri_dict.get(grp.name, None)
                        if new_node is None:
                            new_node = rdflib.URIRef(_get_id(grp, local=local))
                            iri_dict[obj.name] = new_node

                        g.add((node, URIRef(predicate), new_node))

    g = Graph()

    # g.add(
    #     (URIRef(f'file://{grp.filename}'),
    #      RDF.type,
    #      HDF5.File)
    # )

    add_node(grp.name, grp)

    if recursive:
        grp.visititems(add_node)

    return g.serialize(
        format='json-ld',
        context=_context,
        compact=compact
    )


def dumpd(grp,
          iri_only=False,
          local=None,
          recursive: bool = True,
          compact: bool = False,
          context: Dict = None
          ) -> Union[List, Dict]:
    """If context is missing, return will be a List"""
    s = serialize(grp,
                  iri_only,
                  local,
                  recursive=recursive,
                  compact=compact,
                  context=context)
    return json.loads(s)


def dumps(grp,
          iri_only=False,
          local=None,
          recursive: bool = True,
          compact: bool = False,
          context: Optional[Dict] = None,
          **kwargs) -> str:
    """Dump a group or a dataset to to string."""
    return json.dumps(dumpd(
        grp=grp,
        iri_only=iri_only,
        local=local,
        recursive=recursive,
        compact=compact,
        context=context),
        **kwargs
    )


h5dumps = dumps  # alias, use this in future


def dump(grp,
         fp,
         iri_only=False,
         local=None,
         recursive: bool = True,
         compact: bool = False,
         context: Optional[Dict] = None,
         **kwargs):
    """Dump a group or a dataset to to file."""
    return json.dump(
        dumpd(
            grp, iri_only,
            local,
            recursive=recursive,
            compact=compact,
            context=context
        ),
        fp,
        **kwargs
    )


h5dump = dump  # alias, use this in future


def dump_file(filename: Union[str, pathlib.Path], skipND) -> str:
    """Dump an HDF5 file to a JSON-LD file."""
    data = {}
    if skipND is None:
        skipND = 10000

    def _build_attributes(attrs: Iterable[Tuple[str, Any]]):
        def _parse_dtype(v):
            if isinstance(v, np.int32):
                return int(v)
            if isinstance(v, np.int64):
                return int(v)
            if isinstance(v, np.float32):
                return float(v)
            if isinstance(v, np.float64):
                return float(v)
            if isinstance(v, np.ndarray):
                return [_parse_dtype(value) for value in v.tolist()]
            if isinstance(v, str):
                return v
            if v is None:
                return None
            return str(v)

        attrs = [hdf_ontology.Attribute(name=k, value=_parse_dtype(v)) for k, v in attrs.items() if not k.isupper()]
        return attrs

    def _build_dataset_onto_class(ds):
        attrs = _build_attributes(ds.attrs)
        params = dict(name=ds.name, size=ds.size, attribute=attrs)
        ndim = ds.ndim
        if ndim < skipND:
            if ndim > 0:
                value = ds.values[()].tolist()
            else:
                value = ds.values[()]
            params['value'] = value

        if not attrs:
            params.pop('attribute')
        _id = ds.attrs.get('@id', None)
        if _id:
            params['id'] = _id

        dtype_dict = {'u': 'H5T_INTEGER',
                      'i': 'H5T_INTEGER',
                      'f': 'H5T_FLOAT',
                      'S': 'H5T_STRING',
                      }

        # dtype_dict = {'u<8': {'class': 'H5T_INTEGER', 'base': 'H5T_STD_U8LE'},
        #               'u<16': {'class': 'H5T_INTEGER', 'base': 'H5T_STD_U16LE'},
        #               'u<32': {'class': 'H5T_INTEGER', 'base': 'H5T_STD_U32LE'},
        #               'u<64': {'class': 'H5T_INTEGER', 'base': 'H5T_STD_U64LE'},
        #               'u>8': {'class': 'H5T_INTEGER', 'base': 'H5T_STD_U8BE'},
        #               'u>16': {'class': 'H5T_INTEGER', 'base': 'H5T_STD_U16BE'},
        #               'u>32': {'class': 'H5T_INTEGER', 'base': 'H5T_STD_U32BE'},
        #               'u>64': {'class': 'H5T_INTEGER', 'base': 'H5T_STD_U64BE'},
        #               'i<8': {'class': 'H5T_INTEGER', 'base': 'H5T_STD_I8LE'},
        #               'i<16': {'class': 'H5T_INTEGER', 'base': 'H5T_STD_I16LE'},
        #               'i<32': {'class': 'H5T_INTEGER', 'base': 'H5T_STD_I32LE'},
        #               'i<64': {'class': 'H5T_INTEGER', 'base': 'H5T_STD_I64LE'},
        #               'i>8': {'class': 'H5T_INTEGER', 'base': 'H5T_STD_I8BE'},
        #               'i>16': {'class': 'H5T_INTEGER', 'base': 'H5T_STD_I16BE'},
        #               'i>32': {'class': 'H5T_INTEGER', 'base': 'H5T_STD_I32BE'},
        #               'i>64': {'class': 'H5T_INTEGER', 'base': 'H5T_STD_I64BE'},
        #               'f<32': {'class': 'H5T_FLOAT', 'base': 'H5T_IEEE_F32LE'},
        #               'f<64': {'class': 'H5T_FLOAT', 'base': 'H5T_IEEE_F64LE'},
        #               }

        # datatype = dtype_dict.get(f'{ds.dtype.kind}{ds.dtype.byteorder}{ds.dtype.alignment}', None)
        datatype = dtype_dict.get(ds.dtype.kind, None)
        if datatype:
            params['datatype'] = datatype

        ontods = hdf_ontology.Dataset(**params)

        if ds.parent.name not in data:
            data[ds.parent.name] = [ontods, ]
        else:
            data[ds.parent.name].append(ontods)

    def _build_group_onto_class(grp):
        attrs = _build_attributes(grp.attrs)
        params = dict(name=grp.name, attribute=attrs)
        if not attrs:
            params.pop('attribute')
        _id = grp.attrs.get('@id', None)
        if _id:
            params['id'] = _id
        ontogrp = hdf_ontology.Group(**params)
        if grp.parent.name not in data:
            data[grp.parent.name] = [ontogrp, ]
        else:
            data[grp.parent.name].append(ontogrp)

    def _build_onto_classes(name, node):
        if isinstance(node, h5tbx.Dataset):
            return _build_dataset_onto_class(node)
        return _build_group_onto_class(node)

    with h5tbx.File(filename, mode='r') as h5:
        root = hdf_ontology.Group(name='/', attribute=_build_attributes(h5.attrs))
        data['/'] = []

        h5.visititems(_build_onto_classes)

    latest_grp = root
    for k, v in data.items():
        if k != latest_grp.name:
            for m in latest_grp.member:
                if m.name == k:
                    latest_grp = m
                    break
        for obj in v:
            if latest_grp.member is None:
                latest_grp.member = [obj, ]
            else:
                latest_grp.member.append(obj)

    file = hdf_ontology.File(rootGroup=root)

    return file.model_dump_jsonld()
