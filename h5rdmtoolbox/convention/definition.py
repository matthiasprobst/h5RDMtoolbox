from typing import Optional

import h5py

DEFINITION_ATTR_NAME = 'ATTR_DEFINITION'


class DefinitionManager:
    """Definition manager"""

    def __init__(self, attr: h5py.AttributeManager = None):
        self._attr = attr

    @property
    def parent(self):
        """Return the parent object"""
        return self._attr._parent

    def __getitem__(self, item) -> Optional[str]:
        """Get the definition of the attribute"""
        return self.get(item)

    def __setitem__(self, key, value):
        if DEFINITION_ATTR_NAME not in self._attr:
            attrdef = self._attr.get(DEFINITION_ATTR_NAME, {})
        attrdef.update({key: value})
        self._attr[DEFINITION_ATTR_NAME] = attrdef

    def get(self, item, default=None) -> Optional[str]:
        if DEFINITION_ATTR_NAME not in self._attr:
            return default
        return self._attr[DEFINITION_ATTR_NAME].get(item, default)
