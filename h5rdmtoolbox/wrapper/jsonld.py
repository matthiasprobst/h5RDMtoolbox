import h5py
import json
import pathlib
from typing import Dict


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
            if k != '@id':
                if isinstance(v, list):
                    if all([i in ids for i in v]):
                        _entries[_id][k] = [_entries.pop(i) for i in v]

                elif v in ids:
                    _entries[_id][k] = _entries.pop(v)
    if clean:
        for dc in delete_candidates:
            _entries.pop(dc, None)
    return _entries


def dumpd(grp,
          iri_only=False,
          file_url="",
          recursive: bool = True,
          compact: bool = False) -> Dict:
    """Dump a group or a dataset to to dict."""

    if isinstance(grp, (str, pathlib.Path)):
        from .core import File
        with File(grp) as h5:
            return dumpd(h5, iri_only, file_url, recursive=recursive, compact=compact)

    assert isinstance(grp, (h5py.Group, h5py.Dataset))

    def _get_id(_grp):
        return file_url + 'grp:' + _grp.name

    entries = {}

    def _get_dict(_name: str, node):
        _id = node.attrs.get('@id', None)
        if _id is None:
            _id = _get_id(node)
        j = {"@id": _id}
        s = node.iri.subject
        if s is not None:
            j["@type"] = str(s)
        for k in node.attrs.keys():
            if not k.isupper():
                v = node.attrs[k]
                if node.iri.predicate.get(k, None) is not None:
                    if node.iri.object.get(k, None) is not None:
                        value = str(node.iri.object[k])
                    else:
                        if isinstance(v, (h5py.Group, h5py.Dataset)):
                            if '@id' in v.attrs:
                                value = v.attrs['@id']
                            else:
                                value = _get_id(v)
                        else:
                            if isinstance(v, (list, tuple)):
                                value = [str(i) for i in v]
                            else:
                                value = str(v)
                    j[str(node.iri.predicate[k])] = value
                else:
                    if not iri_only:
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


def dumps(grp, iri_only=False,
          file_url="",
          recursive: bool = True,
          compact: bool = False,
          **kwargs) -> str:
    """Dump a group or a dataset to to string."""
    return json.dumps(dumpd(
        grp=grp, iri_only=iri_only, file_url=file_url, recursive=recursive, compact=compact),
        **kwargs
    )


def dump(grp,
         fp,
         iri_only=False,
         file_url="",
         recursive: bool = True,
         compact: bool = False,
         **kwargs):
    """Dump a group or a dataset to to file."""
    return json.dump(
        dumpd(
            grp, iri_only, file_url, recursive=recursive, compact=compact
        ),
        fp,
        **kwargs
    )
