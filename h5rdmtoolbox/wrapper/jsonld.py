import h5py
import json
import numpy as np
import pathlib
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF
from typing import Optional, Union, Dict, List

from h5rdmtoolbox import get_config


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


def _get_id(_node, local) -> URIRef:
    """if an attribute in the node is called "@id", use that, otherwise use the node name"""
    _id = _node.attrs.get('@id', None)
    if not local:
        local = rf'file://{_node.hdf_filename.resolve().absolute()}'
    if _id is None:
        _id = _node.attrs.get(get_config('uuid_name'),
                              local + ':' + _node.name)
    return URIRef(_id)


def serialize(grp,
              iri_only=False,
              local="https://www.example.org",
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
    _context = context or {}

    def add_node(name, obj):
        node = _get_id(obj, local=local)
        node_type = obj.iri.subject
        if node_type:
            g.add((node, RDF.type, node_type))
        if isinstance(obj, h5py.Dataset):
            # node is Parameter
            g.add((node, RDF.type, URIRef("http://www.molmod.info/semantics/pims-ii.ttl#Variable")))
            # parent gets "hasParameter"
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
          local="https://www.example.org",
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


def depr_dumpd(grp,
               iri_only=False,
               local="https://www.example.org",
               recursive: bool = True,
               compact: bool = False) -> Dict:
    """Dump a group or a dataset to to dict."""

    if isinstance(grp, (str, pathlib.Path)):
        from .core import File
        with File(grp) as h5:
            return dumpd(h5, iri_only, local, recursive=recursive, compact=compact)

    assert isinstance(grp, (h5py.Group, h5py.Dataset))

    def _get_id(_grp):
        return local + 'grp:' + _grp.name

    entries = {}

    def _get_dict(_name: str, node):
        _id = node.attrs.get('@id', None)
        if _id is None:
            _id = _get_id(node)
        j = {"@id": _id}
        s = node.iri.subject
        if s is not None:
            j["@type"] = str(s)

        if isinstance(node, h5py.Dataset):
            if node.ndim == 0:
                # only write value if it is a scalar
                if node.dtype.kind == 'S':
                    j["http://www.molmod.info/semantics/pims-ii.ttl#Value"] = str(node.values[()])
                data = node.values[()]
                if isinstance(data, (int, np.integer)):
                    j["http://www.molmod.info/semantics/pims-ii.ttl#Value"] = int(data)
                elif data.dtype.kind == 'S':
                    j["http://www.molmod.info/semantics/pims-ii.ttl#Value"] = str(data)
                else:
                    j["http://www.molmod.info/semantics/pims-ii.ttl#Value"] = float(data)

        for k in node.attrs.keys():
            if not k.isupper():
                v = node.attrs[k]
                if node.iri.predicate.get(k, None) is not None:
                    irikey = str(node.iri.predicate[k])
                    if node.iri.object.get(k, None) is not None:
                        # value = str(node.iri.object[k])
                        if isinstance(v, (list, tuple)):
                            value = [str(i) for i in v]
                        else:
                            value = str(v)
                        j[irikey] = [str(node.iri.object[k]), value]
                    else:
                        if isinstance(v, (h5py.Group, h5py.Dataset)):
                            if '@id' in v.attrs:
                                iri_value = v.attrs['@id']
                            else:
                                iri_value = _get_id(v)
                            j[irikey] = [v.name, iri_value]
                        else:
                            if isinstance(v, (list, tuple)):
                                value = [str(i) for i in v]
                            else:
                                value = str(v)
                        j[irikey] = value
                else:
                    if not iri_only:
                        if isinstance(v, (h5py.Group, h5py.Dataset)):
                            j[k] = v.name
                        else:
                            j[k] = str(v)
        entries[_id] = j
        # entries.append(j)

    _get_dict(grp.name, grp)

    if recursive and isinstance(grp, h5py.Group):
        grp.visititems(_get_dict)
        # return grp.visititems(_get_dict)

    # merge entries. e.g. {"@id": "foo", "author": "gro:/123"} and {"@id": "grp:/123", "name": "MP"}
    # -> {"@id": "foo", "author": {"name": "MP"}}
    entries = _merge_entries(entries, clean=True)

    if len(entries) == 1:
        keys = list(entries.keys())
        jsonld_dict = {"@graph": entries[keys[0]]}
    else:
        jsonld_dict = {"@graph": list(entries.values())}

    if compact:
        from rdflib import Graph
        g = Graph().parse(data=json.dumps(jsonld_dict), format='json-ld')
        return json.loads(g.serialize(format='json-ld', indent=2, compact=True))

    return jsonld_dict


def dumps(grp,
          iri_only=False,
          local="https://www.example.org",
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


def dump(grp,
         fp,
         iri_only=False,
         local="https://www.example.org",
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

# def create_from_jsonld
