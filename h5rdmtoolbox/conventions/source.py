"""Source module

Various source objects are defined and can be set to the HDF5 file:
* Software
"""
from dataclasses import dataclass
from enum import Enum
from packaging import version
from typing import Union, Dict

from .standard_attribute import StandardAttribute


class DataSourceType(Enum):
    """root attribute: data_source_type"""
    experimental = 1
    numerical = 2
    analytical = 3
    unknown = 4
    none = 5

    @staticmethod
    def get_attr_name():
        """Attribute name to be used in HDF5 files"""
        return 'data_source_type'


class DataSource(Enum):
    """root attribute: data_source"""
    particle_image_velocimetry = 1
    computational_fluid_dynamics = 2

    @staticmethod
    def get_attr_name():
        """Attribute name to be used in HDF5 files"""
        return 'data_source'


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

    def dumps(self) -> Dict:
        """Dict representation of the object"""
        return dict(name=self.name, version=str(self.version),
                    url=self.url, description=self.description)


class SourceAttribute(StandardAttribute):
    """Source attribute. Currently, only supports Software"""
    name = 'source'

    def setter(self, obj, source: Union[str, Software]):
        """Sets the attribute source to attribute 'source'"""
        if isinstance(source, Software):
            obj.attrs.create('source', source.dumps())
        else:
            obj.attrs.create('source', source)

    def getter(self, obj):
        """Return the source of the dataset. The attribute name is `source`.
        Returns `None` if it does not exist."""
        source = self.safe_getter(obj)
        if source is None:
            return None
        if isinstance(source, str):
            return source
        return Software.from_dict(source)
