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
        return dict(name=self.name, version=str(self.version),
                    url=self.url, description=self.description)


@register_special_property(H5Group)
class software:
    """property attach to a H5Group"""

    def set(self, sftw: Union[Software, Dict]):
        """Get `software` as group attbute"""
        if isinstance(sftw, (tuple, list)):
            raise TypeError('Software infomration must be provided as dictionary '
                            f'or object of class Softare, not {type(sftw)}')
        if isinstance(sftw, dict):
            # init the Software to check for errors
            self.attrs.create('software', json.dumps(Software(**sftw).to_dict()))
        else:
            self.attrs.create('software', json.dumps(sftw.to_dict()))

    def get(self) -> Software:
        """Get `software` from group attbute. The value is expected
        to be a dictionary-string that can be decoded by json.
        However, if it is a real string it is expected that it contains
        name, version url and description separated by a comma.
        """
        raw = self.attrs.get('software', None)
        if raw is None:
            return Software(None, None, None, None)
        if isinstance(raw, dict):
            return Software(**raw)
        try:
            datadict = json.loads(raw)
        except json.JSONDecodeError:
            # try figuring out from a string. assuming order and sep=','
            keys = ('name', 'version', 'url', 'description')
            datadict = {}
            raw_split = raw.split(',')
            n_split = len(raw_split)
            for i in range(4):
                if i >= n_split:
                    datadict[keys[i]] = None
                else:
                    datadict[keys[i]] = raw_split[i].strip()

        return Software.from_dict(datadict)

    def delete(self):
        """Delete the attribute 'software'"""
        self.attrs.__delitem__('software')
