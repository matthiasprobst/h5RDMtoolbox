import h5py
import json
import pathlib
import rdflib
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import RDF
from typing import Dict, Optional, Union, List

from h5rdmtoolbox.convention.hdf_ontology import HDF5


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
        grp.iri.predicate = predicate
    data_context = data.pop('@context', None)
    if data_context is None:
        data_context = {}
    if context is not None:
        data_context.update(context)

    for k, v in data.items():
        if isinstance(v, dict):
            predicate = data_context.get(k, None)
            print(f'create group {k} in {grp.name}')
            if k not in grp:
                to_hdf(grp.create_group(k), data=v, predicate=predicate, context=data_context)
        elif isinstance(v, list):
            if is_list_of_dict(v):
                for i, entry in enumerate(v):
                    sub_grp_name = f'{k}{i + 1}'
                    if sub_grp_name in grp:
                        sub_grp = grp[sub_grp_name]
                    else:
                        sub_grp = grp.create_group(sub_grp_name)
                        sub_grp.iri.predicate = data_context.get(k, None)
                    to_hdf(sub_grp, data=entry, context=data_context)
            else:
                grp.attrs[k, data_context.get(k, None)] = v
        else:
            if isinstance(v, str) and not v.startswith('http'):
                v_split = v.split(':', 1)
                if len(v_split) == 2:
                    v_prefix, v_value = v_split
                    if v_prefix in data_context:
                        v = data_context[v_prefix] + v_value
            grp.attrs[k, data_context.get(k, None)] = v


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
    _context = {'hdf': str(HDF5._NS)}
    context = context or {}
    _context.update(context)  # = context or {}

    def add_node(name, obj):
        node = rdflib.URIRef(_get_id(obj, local=local))
        # node = rdflib.URIRef(f'_:{obj.name}')
        if isinstance(obj, h5py.File):
            g.add(
                (node,
                 RDF.type,
                 HDF5.rootGroup  # this is a root group!
                 )
            )
        else:
            node_type = obj.iri.subject
            if node_type:
                g.add((node, RDF.type, rdflib.URIRef(obj.iri.subject)))
        if isinstance(obj, h5py.Dataset):
            # node is Parameter
            g.add((node, RDF.type, URIRef("http://www.molmod.info/semantics/pims-ii.ttl#Variable")))
            g.add((node, RDF.type, URIRef("hdf:Dataset")))
            # parent gets "hasParameter"
            # parent_node = f'_:{obj.parent.name}'# _get_id(obj.parent, local)
            parent_node = _get_id(obj.parent, local)
            g.add((parent_node, hasParameter, node))

        for ak, av in obj.attrs.items():
            if not ak.isupper() and not ak.startswith('@'):
                if isinstance(av, (list, tuple)):
                    value = [_get_id_from_attr_value(_av, local) for _av in av]
                else:
                    value = _get_id_from_attr_value(av, local)

                # g.add((node, URIRef(ak), Literal(av)))
                predicate = obj.iri.predicate.get(ak, None)

                # only add if not defined in context:
                if predicate and predicate not in _context:
                    # irikey = str(obj.iri.predicate[ak])
                    if isinstance(value, (list, tuple)):
                        for v in value:
                            g.add((node, URIRef(predicate), v))
                    else:
                        g.add((node, URIRef(predicate), value))

                # context_iri = context.get(ak, None)
                # if context_iri:
                #     g.add((node, URIRef(context_iri), value))

                if predicate is None and not iri_only:
                    g.add((node, URIRef(ak), value))
        # if isinstance(obj, h5py.Group):
        #     for name, sub_obj in obj.items():
        #         add_node(sub_obj, graph)
        # else:
        #     # has parameter
        #     graph.add((node, hasParameter, node))

    g = Graph()

    g.add(
        (URIRef(f'file://{grp.filename}'),
         RDF.type,
         HDF5.File)
    )

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


# def depr_dumpd(grp,
#                iri_only=False,
#                local="https://www.example.org/",
#                recursive: bool = True,
#                compact: bool = False) -> Dict:
#     """Dump a group or a dataset to to dict."""
#
#     if isinstance(grp, (str, pathlib.Path)):
#         from .core import File
#         with File(grp) as h5:
#             return dumpd(h5, iri_only, local, recursive=recursive, compact=compact)
#
#     assert isinstance(grp, (h5py.Group, h5py.Dataset))
#
#     def _get_id(_grp):
#         return local + 'grp:' + _grp.name
#
#     entries = {}
#
#     def _get_dict(_name: str, node):
#         _id = node.attrs.get('@id', None)
#         if _id is None:
#             _id = _get_id(node)
#         j = {"@id": _id}
#         s = node.iri.subject
#         if s is not None:
#             j["@type"] = str(s)
#
#         if isinstance(node, h5py.Dataset):
#             if node.ndim == 0:
#                 # only write value if it is a scalar
#                 if node.dtype.kind == 'S':
#                     j["http://www.molmod.info/semantics/pims-ii.ttl#Value"] = str(node.values[()])
#                 data = node.values[()]
#                 if isinstance(data, (int, np.integer)):
#                     j["http://www.molmod.info/semantics/pims-ii.ttl#Value"] = int(data)
#                 elif data.dtype.kind == 'S':
#                     j["http://www.molmod.info/semantics/pims-ii.ttl#Value"] = str(data)
#                 else:
#                     j["http://www.molmod.info/semantics/pims-ii.ttl#Value"] = float(data)
#
#         for k in node.attrs.keys():
#             if not k.isupper():
#                 v = node.attrs[k]
#                 if node.iri.predicate.get(k, None) is not None:
#                     irikey = str(node.iri.predicate[k])
#                     if node.iri.object.get(k, None) is not None:
#                         # value = str(node.iri.object[k])
#                         if isinstance(v, (list, tuple)):
#                             value = [str(i) for i in v]
#                         else:
#                             value = str(v)
#                         j[irikey] = [str(node.iri.object[k]), value]
#                     else:
#                         if isinstance(v, (h5py.Group, h5py.Dataset)):
#                             if '@id' in v.attrs:
#                                 iri_value = v.attrs['@id']
#                             else:
#                                 iri_value = _get_id(v)
#                             j[irikey] = [v.name, iri_value]
#                         else:
#                             if isinstance(v, (list, tuple)):
#                                 value = [str(i) for i in v]
#                             else:
#                                 value = str(v)
#                         j[irikey] = value
#                 else:
#                     if not iri_only:
#                         if isinstance(v, (h5py.Group, h5py.Dataset)):
#                             j[k] = v.name
#                         else:
#                             j[k] = str(v)
#         entries[_id] = j
#         # entries.append(j)
#
#     _get_dict(grp.name, grp)
#
#     if recursive and isinstance(grp, h5py.Group):
#         grp.visititems(_get_dict)
#         # return grp.visititems(_get_dict)
#
#     # merge entries. e.g. {"@id": "foo", "author": "gro:/123"} and {"@id": "grp:/123", "name": "MP"}
#     # -> {"@id": "foo", "author": {"name": "MP"}}
#     entries = _merge_entries(entries, clean=True)
#
#     if len(entries) == 1:
#         keys = list(entries.keys())
#         jsonld_dict = {"@graph": entries[keys[0]]}
#     else:
#         jsonld_dict = {"@graph": list(entries.values())}
#
#     if compact:
#         from rdflib import Graph
#         g = Graph().parse(data=json.dumps(jsonld_dict), format='json-ld')
#         return json.loads(g.serialize(format='json-ld', indent=2, compact=True))
#
#     return jsonld_dict


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

# def create_from_jsonld
