import h5py
import json
import pathlib
from typing import Dict


def dumpd(grp,
          iri_only=False,
          file_url="file://./",
          recursive: bool = False) -> Dict:
    """Dump a group or a dataset to to dict."""

    if isinstance(grp, (str, pathlib.Path)):
        from .core import File
        with File(grp) as h5:
            return dumpd(h5, iri_only, file_url, recursive=recursive)

    assert isinstance(grp, (h5py.Group, h5py.Dataset))

    def _get_id(_grp):
        stem = pathlib.Path(_grp.file.filename).stem
        return file_url + stem + _grp.name

    entries = []

    def _get_dict(_name: str, node):
        j = {"@id": _get_id(node)}
        s = node.iri.subject
        if s is not None:
            j["@type"] = str(s)
        for k, v in node.attrs.items():
            if not k.isupper():
                if node.iri.predicate.get(k, None) is not None:
                    if node.iri.object.get(k, None) is not None:
                        value = str(node.iri.object[k])
                    else:
                        if isinstance(v, h5py.Group):
                            value = _get_id(v)
                        else:
                            value = str(v)
                    j[str(node.iri.predicate[k])] = value
                else:
                    if not iri_only:
                        j[k] = str(v)
        entries.append(j)

    _get_dict(grp.name, grp)

    if recursive and isinstance(grp, h5py.Group):
        grp.visititems(_get_dict)
        # return grp.visititems(_get_dict)
    if len(entries) == 1:
        return {"@graph": entries[0]}
    return {"@graph": entries}


def dumps(grp, iri_only=False,
          file_url="file://./",
          recursive: bool = False,
          **kwargs):
    """Dump a group or a dataset to to string."""
    return json.dumps(dumpd(grp=grp, iri_only=iri_only, file_url=file_url, recursive=recursive), **kwargs)


def dump(grp,
         fp,
         iri_only=False,
         file_url="file://./",
         recursive: bool = False):
    """Dump a group or a dataset to to file."""
    return json.dump(dumpd(grp, iri_only, file_url, recursive), fp, indent=4)
