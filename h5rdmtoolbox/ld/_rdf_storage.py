"""Internal mutations of RDF attributes, independent of RDF validation.

The wrapper attribute manager owns HDF5 encoding. Keep using its assignment
operation so JSON formatting, attribute types, and convention hooks stay intact.
Each mapping instance is a short-lived read/modify/write operation, not a cache.
"""

import json


def _append_values(current, value):
    """Retain the scalar-to-list promotion and append order of stored values."""
    if isinstance(current, list):
        if isinstance(value, list):
            current.extend(value)
        else:
            current.append(value)
        return current
    if isinstance(value, list):
        return [current, *value]
    return [current, value]


def _merge_type_values(current, value):
    """Keep initial representation and the existing set-based update semantics."""
    if current is None:
        return value
    return list(set(_append_values(current, value)))


class _AttributeMapping:
    """One RDF mapping attribute accessed through its owning attribute manager.

    Only object mappings historically accept JSON strings from a backend that
    does not decode them. Callers opt into that behavior with ``decode_json``.
    Validation stays at the public entry point, before the mutation method.
    """

    def __init__(self, attributes, name, *, decode_json=False):
        self._attributes = attributes
        self._name = name
        self._mapping = attributes.get(name, None)
        if self._mapping is None:
            self._mapping = {}
        elif decode_json and isinstance(self._mapping, str) and self._mapping[0] == '{':
            self._mapping = json.loads(self._mapping)

    def set(self, key, value):
        """Replace one entry without replacing neighboring annotations."""
        self._mapping.update({key: value})
        self._attributes[self._name] = self._mapping

    def add(self, key, value):
        """Create an entry, or append without deduplicating existing objects."""
        current = self._mapping.get(key, None)
        self.set(key, value if current is None else _append_values(current, value))

    def append(self, key, value):
        """Append to an existing entry, preserving KeyError for missing entries."""
        self.set(key, _append_values(self._mapping[key], value))

    def remove(self, key):
        """Remove an entry, retaining an empty mapping attribute when exhausted."""
        self._mapping.pop(key, None)
        self._attributes[self._name] = self._mapping
