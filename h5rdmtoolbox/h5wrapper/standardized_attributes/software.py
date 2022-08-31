import json
from dataclasses import dataclass
from typing import Union, Dict

from packaging import version

from ..accessory import register_special_property
from ..h5file import H5Group


@dataclass
class Software:
    """Software class containing most relevant information about a software"""
    name: str
    version: Union[str, version.Version]
    url: str
    description: str

    def __post_init__(self):
        if isinstance(self.version, str):
            self.version = version.parse(self.version)

    @staticmethod
    def from_dict(dictdata):
        """Read from a dict"""
        return Software(**dictdata)

    def to_dict(self) -> Dict:
        """Dict representation of the object"""
        return dict(name=self.name, version=str(self.version), url=self.url, description=self.description)


@register_special_property(H5Group)
class software:
    """property attach to a H5Group"""

    def set(self, sftw: Union[Software, Dict]):
        """Get `software` as group attbute"""
        self.attrs.create('software', json.dumps(sftw.to_dict()))

    def get(self) -> Software:
        """Get `software` from group attbute"""
        return Software.from_dict(json.dumps(self.attrs.get('software', None)))

    def delete(self):
        """Delete the attribute 'software'"""
        self.attrs.__delitem__('software')
