from dataclasses import dataclass
from packaging import version
from typing import Union, Dict


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
        return dict(name=self.name, version=str(self.version),
                    url=self.url, description=self.description)
