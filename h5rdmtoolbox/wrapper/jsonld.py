import json
import logging
import pathlib
import warnings
from itertools import count
from typing import Dict, List, Optional, Union, Iterable, Tuple, Any

import h5py
import numpy as np
import ontolutils
import rdflib
from ontolutils.classes.utils import split_URIRef
from rdflib import Graph, URIRef, BNode, XSD, RDF, SKOS
from rdflib.plugins.shared.jsonld.context import Context

from h5rdmtoolbox.convention import hdf_ontology
from .core import Dataset, File
from .rdf import RDF_TYPE_ATTR_NAME
from ..convention.ontology import HDF5

_bnode_counter = count()
logger = logging.getLogger('h5rdmtoolbox')

CONTEXT_PREFIXES = {
    'schema': 'https://schema.org/',
    'prov': 'http://www.w3.org/ns/prov#',
    'foaf': 'http://xmlns.com/foaf/0.1/',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
    'hdf5': str(HDF5._NS),
    "brick": "https://brickschema.org/schema/Brick#",
    "csvw": "http://www.w3.org/ns/csvw#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcat": "http://www.w3.org/ns/dcat#",
    "dcmitype": "http://purl.org/dc/dcmitype/",
    "dcterms": "http://purl.org/dc/terms/",
    "dcam": "http://purl.org/dc/dcam/",
    "doap": "http://usefulinc.com/ns/doap#",
    "geo": "http://www.opengis.net/ont/geosparql#",
    "odrl": "http://www.w3.org/ns/odrl/2/",
    "org": "http://www.w3.org/ns/org#",
    "prof": "http://www.w3.org/ns/dx/prof/",
    "qb": "http://purl.org/linked-data/cube#",
    "sh": "http://www.w3.org/ns/shacl#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "sosa": "http://www.w3.org/ns/sosa/",
    "ssn": "http://www.w3.org/ns/ssn/",
    "time": "http://www.w3.org/2006/time#",
    "vann": "http://purl.org/vocab/vann/",
    "void": "http://rdfs.org/ns/void#",
    "wgs": "https://www.w3.org/2003/01/geo/wgs84_pos#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "xml": "http://www.w3.org/XML/1998/namespace",
    "m4i": "http://w3id.org/nfdi4ing/metadata4ing#",
    "bibo": "http://purl.org/ontology/bibo/",
    "biro": "http://purl.org/spar/biro/",
    "dcc": "https://ptb.de/dcc/",
    "emmo": "http://emmo.info/emmo#",
    "obo": "http://purl.obolibrary.org/obo/",
    "pims-ii": "http://www.molmod.info/semantics/pims-ii.ttl#",
    "qudt": "http://qudt.org/schema/qudt/",
    "si": "https://ptb.de/si/",
}

CONTEXT_PREFIXES_INV = {v: k for k, v in CONTEXT_PREFIXES.items()}


def build_node_list(g: Graph, data: List, use_simple_bnode_value: bool = True) -> BNode:
    """Build an RDF List from a list of data"""
    # Create an RDF List for flag values
    # initial_node = rdflib.BNode()
    n = len(data)
    # assert n > 1, 'Expecting at least two element in the list'

    initial_node = rdflib.BNode(value=f'N{next(_bnode_counter)}') if use_simple_bnode_value else rdflib.BNode()

    flag_list = initial_node

    g.add((flag_list, RDF.type, RDF.List))

    # Add flag values to the RDF List
    for i in range(0, n):
        if isinstance(data[i], int):
            flag_node = rdflib.Literal(int(data[i]), datatype=XSD.integer)
        elif isinstance(data[i], str):
            flag_node = rdflib.Literal(str(data[i]), datatype=XSD.string)
        elif isinstance(data[i], float):
            flag_node = rdflib.Literal(float(data[i]), datatype=XSD.float)
        else:
            raise TypeError(f'Unsupported type: {type(data[i])}')

        g.add((flag_list, RDF.first, flag_node))
        if i == n - 1:
            flag_list_rest = RDF.nil
        else:
            flag_list_rest = rdflib.BNode(
                value=f'N{next(_bnode_counter)}') if use_simple_bnode_value else rdflib.BNode()
        g.add((flag_list, RDF.rest, flag_list_rest))
        flag_list = flag_list_rest

    # Add type information
    return initial_node


def resolve_iri(key_or_iri: str, context: Context) -> str:
    """Resolve a key or IRI to a full IRI using the context."""
    assert isinstance(context, Context), f'Expecting Context, got {type(context)}'
    if key_or_iri.startswith('http'):
        return str(key_or_iri)
    if ':' in key_or_iri:
        return context.resolve(key_or_iri)
    try:
        return context.terms.get(key_or_iri).id
    except AttributeError:
        if key_or_iri == 'label':
            return 'http://www.w3.org/2000/01/rdf-schema#label'


# def _merge_entries(entries: Dict, clean: bool = True) -> Dict:
#     _entries = entries.copy()
#
#     ids = list(entries.keys())
#
#     delete_candidates = []
#
#     for _id, entry in entries.items():
#         for k, v in entry.items():
#             if clean and len(entry) == 1:
#                 # remove empty entry, Note, this could be a problem if the entry references elsewhere...
#                 delete_candidates.append(_id)
#                 continue
#             if k not in ('@id', '@type'):
#                 if isinstance(v, list):
#                     if all([i in ids for i in v]):
#                         _entries[_id][k] = [_entries.pop(i) for i in v]
#
#                 elif v in ids:
#                     _entries[_id][k] = _entries.pop(v)
#     if clean:
#         for dc in delete_candidates:
#             _entries.pop(dc, None)
#     return _entries


# def _get_id_from_attr_value(_av, file_url):
#     if isinstance(_av, (h5py.Dataset, h5py.Group)):
#         return _get_id(_av, file_url)
#     else:
#         return Literal(_av)


def _get_id(_node, use_simple_bnode_value: bool = True) -> Union[URIRef, BNode]:
    """if an attribute in the node is called "@id", use that, otherwise use the node name"""
    _id = _node.rdf.subject  # _node.attrs.get('@id', None)
    # if local is not None:
    #     local = rf'file://{_node.hdf_filename.resolve().absolute()}'
    #     return URIRef(local + _node.name[1:])
    if _id is None:
        return rdflib.BNode(value=f'N{next(_bnode_counter)}') if use_simple_bnode_value else rdflib.BNode()
        # _id = _node.attrs.get(get_config('uuid_name'),
        #                       local + _node.name[1:])  # [1:] because the name starts with a "/"
    return URIRef(_id)


def is_list_of_dict(data) -> bool:
    """Check if a list is a list of dictionaries."""
    return all([isinstance(i, dict) for i in data])


def _get_iri_from_prefix(ns: str, context: Union[Dict, Tuple[Dict]]) -> Tuple[Optional[str], Optional[str]]:
    """searches for the IRI of a certain prefix in a context dictionary"""
    if isinstance(context, dict):
        context = [context, ]
    for ctx in context:
        assert isinstance(ctx, dict), f'Expecting dict, got {type(ctx)}'
        if ns.startswith('http'):
            for p, iri in ctx.items():
                if iri == ns:
                    return p, iri
        else:
            iri = ctx.get(ns, None)
            if iri is not None:
                return ns, iri

    # check in known prefix dict:
    if ns.startswith('http'):
        prefix = CONTEXT_PREFIXES_INV.get(ns, None)
    else:
        nsiri = CONTEXT_PREFIXES.get(ns, None)
        if nsiri is None:
            return None, None
        else:
            return ns, nsiri

    if prefix is None:
        return None, None
    return prefix, ns


def process_rdf_key(rdf_name, rdf_value, context, resolve_keys) -> Tuple[URIRef, Dict]:
    """

    Parameters
    ----------
    rdf_name: str
        The name of the object
    rdf_value: str
        subject, predicate or object key
    context: Dict
        The context
    resolve_keys: bool
        If True, the key will be resolved to a full IRI and the prefix is
        added to the context. If False, no context is added.
    """
    # if there is @import in the context, the key might be defined in there, which make resolving the
    # key unnecessary.
    import_context = context.get('@import', None)
    if import_context is not None:
        import_context = {}

    def _process_attr_predicate(_attr_predicate) -> Tuple[URIRef, Dict]:
        ns, _key = split_URIRef(_attr_predicate)

        if rdf_name != _key:
            if resolve_keys:
                _prefix, _prefix_iri = _get_iri_from_prefix(ns, context)
                if _prefix:
                    context[_prefix] = _prefix_iri
                    predicate_uri = rdflib.URIRef(f'{_prefix_iri}{_key}')
                else:
                    # maybe the implemented context prefix dict can help
                    known_prefix = CONTEXT_PREFIXES_INV.get(ns, None)
                    if known_prefix:
                        context[known_prefix] = ns
                        predicate_uri = rdflib.URIRef(f'{ns}{_key}')
                    else:
                        context[rdf_name] = _attr_predicate
                        predicate_uri = rdflib.URIRef(rdf_name)
            else:
                # use the attr name as jsonld key and put its key with the uri
                # in the context
                context[rdf_name] = _attr_predicate
                predicate_uri = rdflib.URIRef(rdf_name)
        else:
            predicate_uri = rdflib.URIRef(_attr_predicate)
        return predicate_uri, context

    if not import_context:
        return _process_attr_predicate(rdf_value)

    for idata in import_context.values():
        # check if the attribute name is defined in the import context
        iri_candidate = idata.get(rdf_name, None)
        if iri_candidate is None:
            break  # check the next import dict

        # the attr name IS DEFINED in the external import file
        # now, resolve the iri:

        if isinstance(iri_candidate, dict):
            iri_candidate = iri_candidate['@id']
        else:
            assert isinstance(iri_candidate, str), f'Expecting str, got {type(iri_candidate)}'

        # the candidate may already be a full IRI
        # we need to guess the prefix:
        ns_prefix, key = split_URIRef(iri_candidate)
        # search for ns_prefix in context
        # attr_predicate_uri = _get_iri_from_prefix(ns_prefix, context)  # prefix, prefix_iri
        prefix, prefix_iri = _get_iri_from_prefix(ns_prefix, context)  # prefix, prefix_iri

        if prefix is None:
            attr_predicate_uri = rdflib.URIRef(rdf_value)
        else:
            if resolve_keys:
                context[prefix] = prefix_iri
                attr_predicate_uri = rdflib.URIRef(f'{prefix_iri}{key}')
            else:
                context[rdf_name] = f'{prefix_iri}{key}'
                attr_predicate_uri = rdflib.URIRef(rdf_name)

        return attr_predicate_uri, context

    # the attr name is not defined in the external import file
    return _process_attr_predicate(rdf_value)


def to_hdf(grp,
           *,
           data: Union[Dict, str] = None,
           source: Union[str, pathlib.Path, ontolutils.Thing] = None,
           predicate: Optional[str] = None,
           context: Dict = None,
           resolve_keys: bool = False) -> None:
    """write json-ld data to group

    .. note::

        Either data (as dict or json string) or source (as filename or ontolutils.Thing) must be given.

    Parameters
    ----------
    grp : h5py.Group
        The group to write to
    data : Union[Dict, str] = None
        The data to write either as dictionary or json string
    source : Union[str, pathlib.Path, ontolutils.Thing] = None
        The source file to read from or a Thing object from ontolutils.
    predicate : None
        The predicate to use for the group
    context : Dict = None
        The context to use. It may be given in the data or source file.
        The context dictionary translate the keys in the data to IRIs.
    resolve_keys : bool = False
        If True, the keys in the data are resolved to IRIs using the context.

    Returns
    -------
    None
    """
    if data is None and source is None:
        raise ValueError('Either data or source must be given')

    if data is None:
        if isinstance(source, ontolutils.Thing):
            data = json.loads(source.model_dump_jsonld(resolve_keys=resolve_keys))
        else:
            with open(source, 'r') as f:
                data = json.load(f)
    else:
        if isinstance(data, str):
            data = json.loads(data)
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
    # data_context['schema'] = 'https://schema.org/'

    ctx = Context(source=data_context)

    if '@graph' in data:
        for graph_entry in data.pop('@graph'):
            # figure out if there's a label:
            label = graph_entry.get('label', None)
            if label is None:
                for k in graph_entry:
                    if k.endswith(':label'):
                        label = graph_entry[k]
                        break

                if label is None:  # still None...
                    _type = graph_entry.get('@type', None)
                    ns, label = split_URIRef(_type)

            i = 1
            while label in grp:
                i += 1
                label = f'{label}{i}'

            _grp = grp.create_group(label)

            to_hdf(_grp, data=graph_entry, context=data_context)

    for k, v in data.items():
        rdf_predicate = None

        if k in ('@id', 'id'):
            if v.startswith('http'):  # blank nodes should not be written to an HDF5 file!
                grp.rdf.subject = resolve_iri(v, ctx)
                # grp.attrs.create(name="@id", data=v)
            continue
        elif k == '@type':
            grp.rdf.type = resolve_iri(v, ctx)
            continue
        else:
            # spit predicate:
            ns_predicate, value_predicate = split_URIRef(k)

            # ns_predicate can be something like None, "schema" or "https://schema.org/"
            if ns_predicate is None:
                _iri = ctx.expand(k)
                if _iri and _iri.startswith('http'):
                    rdf_predicate = _iri
                # rdf_predicate = resolve_iri(k, data_context)  # data_context.get(k, None)
            elif ns_predicate.startswith('http'):
                rdf_predicate = k
            else:
                _iri = ctx.expand(k)
                if _iri and _iri.startswith('http'):
                    rdf_predicate = _iri
                else:
                    rdf_predicate = value_predicate

        if isinstance(v, dict):
            if k not in grp:
                to_hdf(grp.create_group(value_predicate), data=v, predicate=rdf_predicate, context=data_context)

        elif isinstance(v, list):
            if is_list_of_dict(v):
                for i, entry in enumerate(v):
                    # figure out how to name the subgroup
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
                                return False
                            return 'm4i' in ns and key == 'NumericalVariable'

                        if sub_h5obj_type is None:
                            sub_h5obj = grp.create_group(label)
                        else:
                            if _is_m4i_num_var(sub_h5obj_type):
                                # get value with sparql query
                                g = rdflib.Graph().parse(data={'@context': data_context, **entry},
                                                         format='json-ld')
                                q = f"""
                                PREFIX m4i: <http://w3id.org/nfdi4ing/metadata4ing#>
                                SELECT ?value
                                WHERE {{
                                    ?s m4i:hasNumericalValue ?value
                                }}
                                """
                                entry.pop('@context', None)
                                qres = g.query(q)
                                assert len(qres) == 1, f'Expecting one result, got {len(qres)}'
                                value_key: str = str(list(qres.bindings[0])[0])
                                value = qres.bindings[0][value_key].value
                                entry.pop(value_key, None)

                                if isinstance(value, str):
                                    warnings.warn(
                                        'Found 4i:NumericalVariable with string value. '
                                        'Converting it to float by default. Better check the creation of you '
                                        'JSON-LD data',
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
                        term = ctx.find_term(ctx.expand(v))
                        if term:
                            rdf_object = term.id
                        # rdf_object = data_context.get(k, None)
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
                grp.rdf.type = rdf_object
                # grp.attrs.create(name=k, data=rdf_object)
            elif k == '@id':
                grp.rdf.subject = v
                # grp.attrs.create(name=k, data=v)
            else:
                grp.attrs.create(name=value_predicate, data=value_object, rdf_predicate=rdf_predicate)


def get_rdflib_graph(source: Union[str, pathlib.Path, h5py.File],
                     iri_only=False,
                     recursive: bool = True,
                     compact: bool = True,
                     context: Dict = None,
                     structural: bool = True,
                     resolve_keys: bool = True,
                     use_simple_bnode_value: bool = True) -> Tuple[Graph, Dict]:
    """using rdflib graph. This will not write HDF5 dataset data to the graph. Impossible and
     not reasonable as potentially multidimensional"""
    if isinstance(source, (str, pathlib.Path)):
        from .core import File
        with File(source) as h5:
            return get_rdflib_graph(h5,
                                    iri_only,
                                    recursive=recursive,
                                    compact=compact,
                                    context=context)

    grp = source

    _context = {}
    if structural:
        _context['hdf5'] = str(HDF5._NS)
    _context.update(context or {})  # = context or {}

    assert isinstance(_context, dict)

    # download jsonld files provided via "@import" in the context:
    at_import = _context.get("@import", None)
    _import_context_dat = {}  # here, context data from "@import" entries is stored
    if at_import is not None:
        from ..utils import download_context
        if isinstance(at_import, str):
            at_import = [at_import]
        for c in at_import:
            for k, v in download_context(c)._context_cache.items():
                _import_context_dat[c] = v['@context']
                # _context.update(v['@context'])
            # with open(context_filename, 'r') as f:
            #     data_context.update(json.load(f)['@context'])
        _context["@import"] = _import_context_dat

    iri_dict = {}

    def _add_node(graph: rdflib.Graph, triple) -> rdflib.Graph:
        logger.debug(f'Add node: {triple}')
        graph.add(triple)
        return graph

    def _add_hdf_node(name, obj, ctx) -> Dict:
        # node = rdflib.URIRef(f'_:{obj.name}')
        if isinstance(obj, h5py.File):
            root_group = rdflib.BNode(value=f'N{next(_bnode_counter)}') if use_simple_bnode_value else rdflib.BNode()
            iri_dict[name] = root_group
            if structural:
                file_node = rdflib.BNode(value=f'N{next(_bnode_counter)}') if use_simple_bnode_value else rdflib.BNode()
                _add_node(g, (file_node, RDF.type, HDF5.File))
                _add_node(g, (file_node, HDF5.rootGroup, root_group))
                # _add_node(g, (root_group, RDF.type, HDF5.Group))
                # _add_node(g, (root_group, HDF5.name, rdflib.Literal(name)))

        obj_node = iri_dict.get(obj.name, None)
        if obj_node is None:
            obj_node = _get_id(obj)
            iri_dict[obj.name] = obj_node

        if structural and name != '/':
            parent_name = obj.parent.name
            parent_node = iri_dict.get(parent_name, None)
            if parent_node is not None:
                _add_node(g, (parent_node, HDF5.member, obj_node))

        if isinstance(obj, h5py.Group):
            if structural:
                _add_node(g, (obj_node, RDF.type, HDF5.Group))
                _add_node(g, (obj_node, HDF5.name, rdflib.Literal(obj.name)))
            h5_rdf_type = obj.attrs.get(RDF_TYPE_ATTR_NAME, None)
            if h5_rdf_type:
                _add_node(g, (obj_node, RDF.type, rdflib.URIRef(h5_rdf_type)))
            group_type = obj.rdf.type
            if isinstance(group_type, list):
                for gs in group_type:
                    nsp, key = split_URIRef(gs)
                    ns_prefix, ns_iri = _get_iri_from_prefix(nsp, _context.get('@import', {}).values())
                    if ns_iri is not None:
                        _context.update({ns_prefix: ns_iri})
                    _add_node(g, (obj_node, RDF.type, rdflib.URIRef(gs)))
            elif group_type is not None:
                nsp, key = split_URIRef(group_type)
                ns_prefix, ns_iri = _get_iri_from_prefix(nsp, _context.get('@import', {}).values())
                if ns_iri is not None:
                    _context.update({ns_prefix: ns_iri})
                _add_node(g, (obj_node, RDF.type, rdflib.URIRef(group_type)))

        elif isinstance(obj, h5py.Dataset):
            if structural:
                _add_node(g, (obj_node, RDF.type, HDF5.Dataset))
                _add_node(g, (obj_node, HDF5.name, rdflib.Literal(obj.name)))
                _add_node(g, (obj_node, HDF5.size, rdflib.Literal(obj.size, datatype=XSD.integer)))
                _add_node(g, (obj_node, HDF5.dimension, rdflib.Literal(obj.ndim, datatype=XSD.integer)))

                if obj.dtype.kind == 'S':
                    _add_node(g, (obj_node, HDF5.datatype, rdflib.Literal('H5T_STRING')))
                elif obj.dtype.kind in ('i', 'u'):
                    _add_node(g, (obj_node, HDF5.datatype, rdflib.Literal('H5T_INTEGER')))
                else:
                    _add_node(g, (obj_node, HDF5.datatype, rdflib.Literal('H5T_FLOAT')))

            h5_rdf_type = obj.attrs.get(RDF_TYPE_ATTR_NAME, None)
            if h5_rdf_type:
                _add_node(g, (obj_node, RDF.type, rdflib.URIRef(h5_rdf_type)))

            obj_type = obj.rdf.subject
            if obj_type is not None:
                _add_node(g, (obj_node, RDF.type, rdflib.URIRef(obj_type)))

        for ak, av in obj.attrs.items():
            logger.debug(f'Processing attribute "{ak}" with value "{av}"')
            if ak.isupper() or ak.startswith('@'):
                logger.debug(f'Skip attribute "{ak}" because it is upper or starts with "@"')
                continue

            # create a new node for the attribute
            attr_node = rdflib.BNode(value=f'N{next(_bnode_counter)}') if use_simple_bnode_value else rdflib.BNode()
            logger.debug(f'Create new node for attribute "{ak}": {attr_node}')

            if structural:  # add hdf type and name nodes
                _add_node(g, (attr_node, RDF.type, HDF5.Attribute))
                attr_def: str = obj.rdf[ak].definition
                if attr_def:
                    _add_node(g, (attr_node, HDF5.name, rdflib.Literal(ak)))
                    _add_node(g, (attr_node, SKOS.definition, rdflib.Literal(attr_def)))
                    if 'skos' not in ctx:
                        ctx['skos'] = 'http://www.w3.org/2004/02/skos/core#'
                else:
                    _add_node(g, (attr_node, HDF5.name, rdflib.Literal(ak)))

            list_node = None
            attr_literal = None
            # determine the attribute type and select respective RDF literal type
            if isinstance(av, str):
                if av.startswith('http'):
                    attr_literal = rdflib.Literal(av, datatype=XSD.anyURI)
                else:
                    attr_literal = rdflib.Literal(av, datatype=XSD.string)
            elif isinstance(av, (int, np.integer)):
                attr_literal = rdflib.Literal(int(av), datatype=XSD.integer)
            elif isinstance(av, (float, np.floating)):
                attr_literal = rdflib.Literal(float(av), datatype=XSD.float)
            elif isinstance(av, list) or isinstance(av, np.ndarray):
                if isinstance(av, np.ndarray):
                    list_node = build_node_list(g, av.tolist())
                else:
                    list_node = build_node_list(g, av)
            elif isinstance(av, (h5py.Dataset, h5py.Group)):
                attr_literal = rdflib.Literal(av.name)
            else:
                try:
                    attr_literal = rdflib.Literal(json.dumps(av))
                except TypeError as e:
                    logger.debug(f'Could not serialize {av} to JSON. Will apply str(). Error: {e}')
                    attr_literal = rdflib.Literal(str(av))

            if attr_literal:
                logger.debug(f'Literal for attribute "{ak}": {attr_literal}')

            # add node for attr value
            if attr_literal and structural:
                _add_node(g, (attr_node, HDF5.value, attr_literal))

            # attr type:
            if structural:
                _add_node(g, (obj_node, HDF5.attribute, attr_node))

            # no process the predicate:
            attr_predicate = obj.rdf.predicate.get(ak, None)
            logger.debug(f'Predicate for attribute "{ak}": "{attr_predicate}"')

            if attr_predicate is not None:
                predicate_uri, ctx = process_rdf_key(
                    rdf_name=ak,
                    rdf_value=attr_predicate,
                    resolve_keys=resolve_keys,
                    context=ctx)
                assert isinstance(ctx, dict)

            attr_object = obj.rdf.object.get(ak, None)

            if isinstance(attr_object, dict):

                def _create_obj_node(_node, _pred, _val):
                    """RDF obj is a thing. create and assign nodes"""
                    _type = _val.pop('@type', None)
                    _id = _val.pop('@id', None)

                    # init new node:
                    _sub_obj_node = rdflib.BNode(
                        value=f'N{next(_bnode_counter)}') if use_simple_bnode_value else rdflib.BNode()

                    _add_node(g, (_sub_obj_node, RDF.type, rdflib.URIRef(resolve_iri(_type, context=attr_context))))
                    # the new node is a member of the object node
                    _add_node(g, (_node, _pred, _sub_obj_node))

                    # there might be graph...better not... not covered at the moment...
                    def _parse_val(_k, _v):
                        if isinstance(_v, dict):
                            _create_obj_node(_sub_obj_node, rdflib.URIRef(resolve_iri(_k, context=attr_context)),
                                             _v)
                        else:
                            _k_pred = resolve_iri(_k, context=attr_context)
                            if _k_pred:
                                _add_node(g, (_sub_obj_node, rdflib.URIRef(_k_pred), rdflib.Literal(_v)))

                    for k, v in _val.items():
                        if isinstance(v, list):
                            for __v in v:
                                _parse_val(k, __v)
                        else:
                            _parse_val(k, v)

                _attr_context: Optional[dict] = attr_object.pop('@context', None)
                attr_context: Context = Context(source=_attr_context)
                _context.update(_attr_context)

                _create_obj_node(obj_node, predicate_uri, attr_object)

                attr_object = None

            # attr_def = obj.attrsdef.get(ak, None)
            attr_def = obj.rdf[ak].definition  # .get(ak, None)
            if attr_def:
                _add_node(g, (attr_node, SKOS.definition, rdflib.Literal(attr_def)))

            if structural:
                if attr_object:
                    _add_node(g, (obj_node, HDF5.value, rdflib.URIRef(attr_object)))
                if list_node:
                    _add_node(g, (attr_node, HDF5.value, list_node))

            if attr_predicate is not None and attr_object is not None:
                # predicate and object given
                _add_node(g, (obj_node, predicate_uri, rdflib.URIRef(attr_object)))
            # elif attr_predicate is None and attr_object is not None and structural:
            #     # only object given
            #     _add_node(g, (obj_node, HDF5.value, rdflib.URIRef(attr_object)))
            elif attr_predicate is not None and attr_object is None:
                # only predicate given
                if attr_literal:
                    _add_node(g, (obj_node, predicate_uri, attr_literal))
                elif list_node:
                    _add_node(g, (obj_node, predicate_uri, list_node))

        return _context

    g = Graph()

    _add_hdf_node(grp.name, grp, _context)

    class HDFVisitor:

        def __init__(self, ctx):
            self.ctx = ctx

        def __call__(self, name, obj):
            logger.debug(f'Visiting {name} ({obj})')
            self.ctx = _add_hdf_node(name, obj, self.ctx)

    visitor = HDFVisitor(_context)

    if recursive:
        grp.visititems(visitor)

    _context = visitor.ctx
    _context.pop('@import', None)

    return g, _context


def serialize(source: Union[str, pathlib.Path, h5py.File],
              iri_only=False,
              recursive: bool = True,
              compact: bool = True,
              context: Dict = None,
              structural: bool = True,
              resolve_keys: bool = True) -> str:
    g, ctx = get_rdflib_graph(source, iri_only, recursive, compact, context, structural, resolve_keys)
    return g.serialize(
        format='json-ld',
        context=ctx,
        compact=compact
    )


def dumpd(grp,
          iri_only=False,
          recursive: bool = True,
          compact: bool = True,
          context: Dict = None,
          structural: bool = True,
          resolve_keys: bool = False
          ) -> Union[List, Dict]:
    """If context is missing, return will be a List"""
    s = serialize(grp,
                  iri_only,
                  recursive=recursive,
                  compact=compact,
                  context=context,
                  structural=structural,
                  resolve_keys=resolve_keys)
    jsonld_dict = json.loads(s)
    if compact and '@graph' in jsonld_dict:
        compact_graph = make_graph_compact(jsonld_dict['@graph'])
        return {'@context': jsonld_dict.get('@context', {}), '@graph': compact_graph}
    return jsonld_dict


def dumps(grp,
          iri_only=False,
          recursive: bool = True,
          compact: bool = True,
          context: Optional[Dict] = None,
          structural: bool = True,
          resolve_keys: bool = False,
          **kwargs) -> str:
    """Dump a group or a dataset to string."""
    return json.dumps(dumpd(
        grp=grp,
        iri_only=iri_only,
        recursive=recursive,
        compact=compact,
        context=context,
        structural=structural,
        resolve_keys=resolve_keys),
        **kwargs
    )


h5dumps = dumps  # alias, use this in future


def dump(grp,
         fp,
         iri_only=False,
         recursive: bool = True,
         compact: bool = True,
         context: Optional[Dict] = None,
         **kwargs):
    """Dump a group or a dataset to to file."""
    return json.dump(
        dumpd(
            grp, iri_only,
            recursive=recursive,
            compact=compact,
            context=context
        ),
        fp,
        **kwargs
    )


h5dump = dump  # alias, use this in future


def dump_file(filename: Union[str, pathlib.Path], skipND) -> str:
    """Dump an HDF5 file to a JSON-LD file.

    Parameter
    ---------
    filename: Union[str, pathlib.Path]
        The HDF5 file to read from.
    skipND: int
        The number of dimensions to skip when reading a dataset.

    Returns
    -------
    str
        Dumped json-ld data as string
    """
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
                      'S': 'H5T_STRING'}

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


def hdf2jsonld(filename: Union[str, pathlib.Path],
               skipND: int,
               metadata_filename: Optional[Union[str, pathlib.Path]] = None) -> pathlib.Path:
    """Dumps the metadata (not only attributes but also structure and possible RDF tripels...) to
    a target filename.

    Parameter
    ---------
    filename: Union[str, pathlib.Path]
        The HDF5 file to read from.
    skipND: int
        The number of dimensions to skip when reading a dataset.
    metadata_filename: Optional[Union[str, pathlib.Path]]
        The target filename to write to. If None, the target filename will be the filename with
        the suffix ".jsonld" (using this suffix over '.json' due to recommendation:
        https://www.w3.org/TR/json-ld/#iana-considerations).

    Returns
    -------
    metadata_filename: pathlib.Path
        The metadata filename
    """
    if metadata_filename is None:
        metadata_filename = pathlib.Path(filename).with_suffix('.jsonld')  # recommended suffix for JSON-LD is .jsonld!
    else:
        metadata_filename = pathlib.Path(metadata_filename)

    with open(metadata_filename, 'w', encoding='utf-8') as f:
        f.write(dump_file(filename, skipND))

    return metadata_filename


def make_graph_compact(graph: List[Dict]) -> List[Dict]:
    """make a graph compact, which makes readability better"""

    def resolve_references(item):
        if isinstance(item, dict):
            for key, value in item.items():
                if isinstance(value, dict) and '@id' in value:
                    reference_id = value['@id']
                    for sub_item in graph:
                        if sub_item.get('@id') == reference_id:
                            item[key] = sub_item
                            graph.remove(sub_item)
                            resolve_references(sub_item)
                            break
                elif isinstance(value, list):
                    for i, v in enumerate(value):
                        if isinstance(v, dict) and '@id' in v:
                            reference_id = v['@id']
                            for sub_item in graph:
                                if sub_item.get('@id') == reference_id:
                                    value[i] = sub_item
                                    graph.remove(sub_item)
                                    resolve_references(sub_item)
                                    break
        elif isinstance(item, list):
            for i, value in enumerate(item):
                if isinstance(value, dict):
                    resolve_references(value)

    # Resolve references in each item of the graph
    for item in graph:
        resolve_references(item)
    return graph
