"""Source module

Various source objects are defined and can be set to the HDF5 file:
* Software
"""
import abc
import json
import packaging.version
import re
from dataclasses import dataclass
from typing import Union, Dict

from .standard_attribute import StandardAttribute
from .utils import check_url


@dataclass
class SourceBase(abc.ABC):
    """Base class for all source types."""

    @staticmethod
    @abc.abstractmethod
    def loads(sdict) -> "SourceBase":
        pass

    @abc.abstractmethod
    def dumps(self) -> str:
        pass


class Hardware(SourceBase):
    """Hardware class containing most relevant information about a hardware.

    Parameters
    ----------
    device : str
        Name of the device
    manufacturer : str
        Name of the manufacturer
    serial_number : str
        Serial number of the device
    **kwargs
        Additional attributes
    """

    def __init__(self, device, manufacturer, serial_number, **kwargs):
        self.device = device
        self.manufacturer = manufacturer
        self.serial_number = serial_number
        self.additional_attributes = kwargs
        self._pattern = '^[0-9].*'
        self.check()

    def __getattr__(self, item):
        if item in self.additional_attributes:
            return self.additional_attributes[item]
        super().__getattribute__(item)

    def __str__(self):
        """Return a string representation of the hardware"""
        output = f"Device: {self.device}\nManufacturer: {self.manufacturer}\nSerial number: {self.serial_number}\n"

        for key, value in self.additional_attributes.items():
            output += f"{key.capitalize()}: {value}\n"

        return output

    def check(self):
        """Check"""
        for k, v in self.required_items():
            if v is None:
                raise ValueError(f'Obligatory value of field "{k}" is None which is not allowed.')
        for k, v in self.items():
            if k != 'serial_number':
                if isinstance(v, str):
                    if re.match(self._pattern, v):
                        raise ValueError(f'Value "{v}" of field "{k}" does not match the pattern {self._pattern}')

    def items(self):
        """Return a view on the hardware's fields"""
        return dict(device=self.device, manufacturer=self.manufacturer, serial_number=self.serial_number,
                    **self.additional_attributes).items()

    def required_items(self):
        """Return a view on the hardware's required fields"""
        return dict(device=self.device, manufacturer=self.manufacturer, serial_number=self.serial_number).items()

    def optional_items(self):
        """Return a view on the hardware's optional fields"""
        return dict(**self.additional_attributes).items()

    @staticmethod
    def loads(sdict: str) -> "Hardware":
        """Read from a json string"""
        return Hardware.from_dict(json.loads(sdict))

    def dumps(self) -> str:
        """Calls json.dumps() on the dict representation of the object"""
        return json.dumps({'hardware': dict(device=self.device,
                                            manufacturer=self.manufacturer,
                                            serial_number=self.serial_number,
                                            **self.additional_attributes)})


class Software(SourceBase):
    """Software class containing most relevant information about a software

    Parameters
    ----------
    name : str
        Name of the software
    version : Union[str, packaging.version.Version]
        Version of the software. Will be transformed to a packaging.version.Version object.
    description : str
        Description of the software
    url : str
        URL of the software. Will be checked if it is valid.
    author : str, optional
        Author of the software, by default None
    license : str, optional
        License of the software, by default None
    language : str, optional
        Language of the software, by default None
    platform : str, optional
        Platform of the software, by default None
    **kwargs
        Additional keyword arguments (user-defined)
    """

    def __init__(self,
                 name: str,
                 version: Union[str, packaging.version.Version],
                 description: str,
                 url: str,
                 author: str = None,
                 license: str = None,
                 language: str = None,
                 platform: str = None,
                 **kwargs):
        self.name = name
        self.version = packaging.version.Version(version)
        self.description = description
        self.url = url
        self.author = author
        self.license = license
        self.language = language
        self.platform = platform
        self.additional_attributes = kwargs
        self._pattern = '^[0-9].*'
        self.check()

    def __getattr__(self, item):
        if item in self.additional_attributes:
            return self.additional_attributes[item]
        super().__getattribute__(item)

    def __str__(self):
        """Return a string representation of the software"""
        output = f"Name: {self.name}\nVersion: {self.version}\nDescription: {self.description}\nAuthor: {self.author}\nURL: {self.url}\n"

        for key, value in self.additional_attributes.items():
            output += f"{key.capitalize()}: {value}\n"

        return output

    def required_items(self):
        """Return all required items of the software"""
        return dict(name=self.name,
                    version=self.version,
                    description=self.description,
                    url=self.url).items()

    def optional_items(self):
        """Return all required items of the software"""
        return dict(author=self.author,
                    license=self.license,
                    language=self.language,
                    platform=self.platform,
                    **self.additional_attributes).items()

    def items(self):
        """Return a view on the software's fields"""
        return dict(name=self.name,
                    version=self.version,
                    description=self.description,
                    author=self.author,
                    url=self.url,
                    license=self.license,
                    language=self.language,
                    platform=self.platform,
                    **self.additional_attributes).items()

    def check(self) -> bool:
        """Check if the software is valid. Currently, only checks if the URL is valid."""
        check_url(self.url, raise_error=True)
        for k, v in self.required_items():
            if v is None:
                raise ValueError(f'Obligatory value of field "{k}" is None which is not allowed.')
        for k, v in self.items():
            if k not in ('url', 'version') and v is not None:
                if isinstance(v, str):
                    if re.match(self._pattern, v):
                        raise ValueError(f'Value "{v}" of field "{k}" does not match the pattern {self._pattern}')
        return True

    @staticmethod
    def loads(sdict: str):
        """Read from a json string"""
        return Software.from_dict(json.loads(sdict))

    def dumps(self) -> str:
        """Calls json.dumps() on the dict representation of the object"""
        return json.dumps({'software': dict(name=self.name, version=str(self.version),
                                            url=self.url, description=self.description,
                                            author=self.author, license=self.license,
                                            language=self.language, platform=self.platform,
                                            **self.additional_attributes)})


class Source:
    """Source class. Interface to Software and Hardware classes.

    Parameters
    ----------
    source : Dict
        Dictionary containing either a software or hardware source

    """

    @staticmethod
    def loads(sdict) -> Union[Software, Hardware]:
        """Read from a json string"""
        source = json.loads(sdict)
        if 'software' in source:
            return Software(**source['software'])
        if 'hardware' in source:
            return Hardware(**source['hardware'])
        raise ValueError('Expected either "software" or "hardware" as keys in the source dictionary.')


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
            try:
                return Source.loads(source)
            except json.decoder.JSONDecodeError as e:
                raise RuntimeError(
                    'It seems that the source attribute is not a string representation of a '
                    f'dictionary. Original error: {e}'
                )
        raise RuntimeError(f'Could not parse source string: {source}')

    def set(self, source: Union[str, Software]):
        """Sets the attribute source to attribute 'source'"""
        if isinstance(source, (Software, Hardware)):
            return super().set(source.dumps())
        super().set(source)
