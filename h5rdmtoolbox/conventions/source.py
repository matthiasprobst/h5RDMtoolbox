"""Source module

Various source objects are defined and can be set to the HDF5 file:
* Software
"""
import abc
import json
from dataclasses import dataclass
from packaging import version
from typing import Union, Dict

from .standard_attribute import StandardAttribute


@dataclass
class Source:
    """Source class containing most relevant information about a source"""

    @staticmethod
    def from_dict(source_dict: Dict):
        """Read from a dict"""
        if 'source_type' in source_dict:
            if source_dict['source_type'] == 'software':
                return Software.from_dict(source_dict)
        raise RuntimeError(f'Could not identify source type from: {source_dict}')

    @staticmethod
    def loads(sdict: str):
        """Read from a json string"""
        return Source.from_dict(json.loads(sdict))


@dataclass
class SourceBase(abc.ABC):
    """Base class for all source types."""

    @abc.abstractmethod
    def from_dict(self) -> str:
        pass

    @abc.abstractmethod
    def loads(self) -> str:
        pass

    @abc.abstractmethod
    def dumps(self) -> str:
        pass


@dataclass
class Software(SourceBase):
    """Software class containing most relevant information about a software"""
    name: str
    version: Union[str, version.Version]
    url: str
    description: str

    def __post_init__(self):
        if isinstance(self.version, str):
            self.version = version.parse(self.version)

    @staticmethod
    def from_dict(software_dict: Dict):
        """Read from a dict"""
        if 'source_type' in software_dict:
            if software_dict['source_type'] != 'software':
                raise ValueError('Seems not to be a software dict. source_type is not "software"')
            software_dict.pop('source_type')
        return Software(**software_dict)

    def loads(self, sdict: str):
        """Read from a json string"""
        return Software.from_dict(json.loads(sdict))

    def dumps(self) -> Dict:
        """Calls json.dumps() on the dict representation of the object"""
        return json.dumps(dict(source_type='software', name=self.name, version=str(self.version),
                               url=self.url, description=self.description))


class SourceAttribute(StandardAttribute):
    """Source attribute. Currently, only supports Software"""
    name = 'source'

    def get(self):
        """Return the source of the dataset. The attribute name is `source`.
        Returns `None` if it does not exist."""
        source = super().get(src=self.parent, name=self.name)
        if source is None:
            return None
        if isinstance(source, str):
            return Source.loads(source)
        raise RuntimeError(f'Could not parse source string: {source}')

    def set(self, source: Union[str, Software]):
        """Sets the attribute source to attribute 'source'"""
        if isinstance(source, Software):
            return super().set(source.dumps())
        super().set(source)
