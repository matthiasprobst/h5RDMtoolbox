import h5py
import json
import logging
import numpy as np
import pathlib
import rdflib
import warnings
from ontolutils.classes.thing import resolve_iri
from ontolutils.classes.utils import split_URIRef
from rdflib import Graph, URIRef, Literal, BNode, XSD, RDF
from typing import Dict, Optional, Union, List, Iterable, Tuple, Any

from h5rdmtoolbox.convention import hdf_ontology
from .core import Dataset, File
from ..convention.hdf_ontology import HDF5

logger = logging.getLogger('h5rdmtoolbox')


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


def _get_id(_node, local=None) -> Union[URIRef, BNode]:
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

        if k in ('@id', 'id'):
            grp.attrs.create(name="@id", data=v)
            continue
            # rdf_predicate = None
            # if v.startswith('http'):
            #     value_predicate = k
            # else:
            #     continue
        elif k == '@type':
            grp.rdf.subject = resolve_iri(v, data_context)
            continue
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
            if k not in grp:
                to_hdf(grp.create_group(value_predicate), data=v, predicate=rdf_predicate, context=data_context)

        elif isinstance(v, list):
            if is_list_of_dict(v):
                for i, entry in enumerate(v):
                    # figure out how to name the sub group
                    # best would be to take the label, if it exists
                    for label_identifier in ('rdfs:label', 'label', 'http://www.w3.org/2000/01/rdf-schema#'):
                        _label = entry.get(label_identifier, None)
                        break

                    if _label is None:
                        if len(v) > 1:
                            label = f'{k}{i + 1}'
                        else:
                            label = k
                    else:
                        ns, label = split_URIRef(_label)

                    if label in grp:
                        sub_h5obj = grp[label]
                    else:
                        ns_predicate, rdf_predicate = split_URIRef(k)
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

                        # create a group for non-numeric data or if it cannot be identified as such
                        sub_h5obj_type = entry.get('@type', None)

                        def _is_m4i_num_var(_type: str) -> bool:
                            ns, key = split_URIRef(_type)
                            if ns is None:
                                print(_type, 'is not a m4i:NumericalVariable')
                                return False
                            return 'm4i' in ns and key == 'NumericalVariable'

                        if sub_h5obj_type is None:
                            sub_h5obj = grp.create_group(label)
                        else:
                            if _is_m4i_num_var(sub_h5obj_type):
                                value = entry['value']
                                if isinstance(value, str):
                                    warnings.warn(
                                        'Found 4i:NumericalVariable with string value. ' \
                                        'Converting it to float by default. Better check the creation of you JSON-LD data',
                                        UserWarning)
                                    value = float(value)
                                sub_h5obj = grp.create_dataset(label, data=value)
                            else:
                                sub_h5obj = grp.create_group(label)

                    # sub_h5obj.rdf.predicate = rdf_predicate

                    to_hdf(sub_h5obj, data=entry, context=data_context, predicate=rdf_predicate)
            else:
                grp.attrs[k, data_context.get(k, None)] = v
        else:
            # maybe value_object is a IRI?!
            rdf_object = None
            if isinstance(v, str):
                if v.startswith('http'):
                    value_object = v
                else:
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
                            rdf_object = None
            else:
                value_object = v

            if k == '@type' and rdf_object is not None:
                grp.attrs.create(name=k, data=rdf_object)
            elif k == '@id':
                grp.attrs.create(name=k, data=v)
            else:
                grp.attrs.create(name=value_predicate, data=value_object, rdf_predicate=rdf_predicate)


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
    # global _context
    _context = {}
    context = context or {}
    _context.update(context)  # = context or {}
    _context['foaf'] = 'http://xmlns.com/foaf/0.1/'
    _context['prov'] = 'http://www.w3.org/ns/prov#'
    _context['schema'] = 'https://schema.org/'
    _context['rdfs'] = 'http://www.w3.org/2000/01/rdf-schema#'
    _context['hdf5'] = str(HDF5._NS)

    iri_dict = {}

    def _add_node(graph: rdflib.Graph, triple) -> rdflib.Graph:
        logger.debug(f'Add node: {triple}')
        graph.add(triple)
        return graph

    def _add_hdf_node(name, obj):
        obj_node = iri_dict.get(obj.name, None)
        if obj_node is None:
            obj_node = _get_id(obj, local=local)
            iri_dict[obj.name] = obj_node

        # node = rdflib.URIRef(f'_:{obj.name}')
        if isinstance(obj, h5py.File):
            _add_node(g, (obj_node, RDF.type, HDF5.Group))
            # rootGroupNode = rdflib.URIRef(_get_id(obj, local=local))
            # _add_node(g, (node, HDF5.rootGroup, rootGroupNode))
        elif isinstance(obj, h5py.Group):
            _add_node(g, (obj_node, RDF.type, HDF5.Group))
        elif isinstance(obj, h5py.Dataset):
            _add_node(g, (obj_node, RDF.type, HDF5.Dataset))
            obj_type = obj.rdf.subject
            if obj_type is not None:
                _add_node(g, (obj_node, RDF.type, rdflib.URIRef(obj_type)))
            _add_node(g, (obj_node, HDF5.name, rdflib.Literal(obj.name)))
            _add_node(g, (obj_node, HDF5.size, rdflib.Literal(obj.size, datatype=XSD.integer)))
            if obj.dtype.kind == 'S':
                _add_node(g, (obj_node, HDF5.datatype, rdflib.Literal('H5T_STRING')))
            elif obj.dtype.kind in ('i', 'u', 'f'):
                _add_node(g, (obj_node, HDF5.datatype, rdflib.Literal('H5T_INTEGER')))
            else:
                _add_node(g, (obj_node, HDF5.datatype, rdflib.Literal('H5T_FLOAT')))
        _add_node(g, (obj_node, HDF5.name, rdflib.Literal(obj.name)))

        for ak, av in obj.attrs.items():
            if not ak.isupper() and not ak.startswith('@'):
                attr_node = rdflib.BNode()

                _add_node(g, (attr_node, RDF.type, HDF5.Attribute))
                _add_node(g, (attr_node, HDF5.name, rdflib.Literal(ak)))

                if isinstance(av, str):
                    if av.startswith('http'):
                        attr_literal = rdflib.Literal(av, datatype=XSD.anyURI)
                    else:
                        attr_literal = rdflib.Literal(av, datatype=XSD.string)
                elif isinstance(av, (int, np.integer)):
                    attr_literal = rdflib.Literal(av, datatype=XSD.integer)
                elif isinstance(av, (float, np.floating)):
                    attr_literal = rdflib.Literal(av, datatype=XSD.float)
                else:
                    # unknown type --> dump it with json
                    if isinstance(av, np.ndarray):
                        attr_literal = rdflib.Literal(json.dumps(av.tolist()))
                    # elif isinstance(av, (h5py.Group, h5py.Dataset)):
                    #     attr_literal = rdflib.Literal(av.name)
                    else:
                        try:
                            attr_literal = rdflib.Literal(json.dumps(av))
                        except TypeError as e:
                            warnings.warn(f'Could not serialize {av} to JSON. Will apply str(). Error: {e}')
                            attr_literal = rdflib.Literal(str(av))

                # add node for attr value
                if attr_literal:
                    _add_node(g, (attr_node, HDF5.value, attr_literal))

                # attr type:
                _add_node(g, (obj_node, HDF5.attribute, attr_node))

                attr_predicate = obj.rdf.predicate.get(ak, None)
                attr_object = obj.rdf.object.get(ak, None)
                if attr_predicate is not None and attr_object is not None:
                    # predicate and object given
                    _add_node(g, (obj_node, rdflib.URIRef(attr_predicate), rdflib.URIRef(attr_object)))
                elif attr_predicate is None and attr_object is not None:
                    # only object given
                    _add_node(g, (obj_node, HDF5.value, rdflib.URIRef(attr_object)))
                elif attr_predicate is not None and attr_object is None:
                    # only predicate given
                    _add_node(g, (obj_node, rdflib.URIRef(attr_predicate), attr_literal))

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

                        g.add((obj_node, URIRef(predicate), new_node))

    g = Graph()

    _add_hdf_node(grp.name, grp)

    if recursive:
        grp.visititems(_add_hdf_node)

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
        if isinstance(node, Dataset):
            return _build_dataset_onto_class(node)
        return _build_group_onto_class(node)

    with File(filename, mode='r') as h5:
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
