"""module for constructors used as pre- or suffixes to standard names"""
from dataclasses import dataclass
from typing import List, Union, Dict, Tuple


class StandardConstructor:
    """Standard constructor is a prefix or suffix to a
    standard name, e.g. [x_]velocity, velocity[_in_rotating_frame]"""

    def __init__(self, name, description, **kwargs):
        self._name = name
        self._description = description
        self._list_of_user_properties = list(kwargs.keys())
        for k, v in kwargs.items():
            setattr(self, k, v)

    @property
    def name(self):
        """Return the name of the standard item"""
        return self._name

    @property
    def description(self):
        """Return the description of the standard item"""
        return self._description

    def __repr__(self):
        user_props = ', '.join([f'{k}="{getattr(self, k)}"' for k in self._list_of_user_properties])
        if user_props:
            return f'<{self.__class__.__name__}: name="{self._name}", description="{self.description}", {user_props}>'
        return f'<{self.__class__.__name__}: name="{self._name}", description="{self.description}">'

    def __str__(self):
        return self.name


@dataclass(frozen=True)
class StandardConstructors:
    """Collection of StandardConstructor objects"""
    items: List[StandardConstructor]

    def __iter__(self):
        return iter(self.items)

    def __contains__(self, item):
        return item in self.names

    def __getitem__(self, item: Union[str, int]):
        if isinstance(item, int):
            return self.items[item]
        for _item in self.items:
            if _item.name == item:
                return _item
        raise KeyError(f"Item '{item}' not found")

    @property
    def names(self):
        """Return the names of the locations"""
        return [d.name for d in self.items]

    def to_dict(self) -> Dict:
        """Return dictionary representation of StandardLocations"""
        return {item.name: item.description for item in self.items}


@dataclass
class StandardReferenceFrame:
    """Standard Reference Frame"""
    name: str
    type: str
    origin: Tuple[float, float, float]
    orientation: Dict
    principle_axis: Union[str, Tuple[float, float, float], None] = None

    def __post_init__(self):
        if not isinstance(self.origin, (list, tuple)):
            raise TypeError(f'Wrong type for "origin". Expecting tuple but got {type(self.origin)}')
        self.origin = tuple(self.origin)
        if isinstance(self.principle_axis, str):
            self.principle_axis = self.orientation[self.principle_axis]

    def to_dict(self):
        return {self.name: dict(type=self.type,
                                origin=self.origin,
                                orientation=self.orientation,
                                principle_axis=self.principle_axis)}


class StandardReferenceFrames:
    """Collection of Standard Reference Frames"""

    def __init__(self, standard_reference_frames: List[StandardReferenceFrame]):
        self._standard_reference_frames = {srf.name: srf for srf in standard_reference_frames}
        self._names = list(self._standard_reference_frames.keys())
        self._index = 0

    def __repr__(self):
        return f'<StandardReferenceFrames: {self._names}>'

    def __len__(self):
        return len(self._names)

    def __getitem__(self, item: Union[int, str]) -> StandardReferenceFrame:
        if isinstance(item, int):
            return self._standard_reference_frames[self._names[item]]
        return self._standard_reference_frames[item]

    def __contains__(self, item) -> bool:
        return item in self._names

    def __iter__(self):
        return self

    def __next__(self):
        if self._index < len(self) - 1:
            self._index += 1
            return self._standard_reference_frames[self._names[self._index]]
        self._index = -1
        raise StopIteration

    @property
    def names(self):
        """Return the names of the reference frames"""
        return self._names

    def to_dict(self) -> Dict:
        """Return dictionary representation of StandardReferenceFrames"""
        frames = [srf.to_dict() for srf in self._standard_reference_frames.values()]
        srfdict = {'standard_reference_frames': {}}
        for frame in frames:
            for k, v in frame.items():
                srfdict['standard_reference_frames'][k] = v
        return srfdict
