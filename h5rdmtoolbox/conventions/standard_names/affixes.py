"""module for constructors used as pre- or suffixes to standard names"""
import warnings
from typing import List, Union, Dict, Callable

from .transformation import Transformation, StandardName, errors


def _difference_of_X_and_Y_between_LOC1_and_LOC2(match, snt) -> StandardName:
    """Difference of X and Y between locations"""
    standard_name = match.string
    groups = match.groups()
    assert len(groups) == 4
    if groups[2] not in snt.affixes['location']:
        raise errors.AffixKeyError(f'StandardLocation "{groups[2]}" not found in registry of the standard name table. '
                                   f'Available locations are: {snt.affixes["location"].names}')
    if groups[3] not in snt.affixes['location']:
        raise errors.AffixKeyError(f'StandardLocation "{groups[3]}" not found in registry of the standard name table. '
                                   f'Available locations are: {snt.affixes["location"].names}')
    sn1, sn2 = snt[groups[0]], snt[groups[1]]
    if sn1.units != sn2.units:
        raise ValueError(f'Units of "{sn1.name}" and "{sn2.name}" are not compatible: "{sn1.units}" and '
                         f'"{sn2.units}".')
    new_description = f"Difference of {sn1.name} and {sn2.name} between {groups[2]} and {groups[3]}"
    return StandardName(standard_name, sn1.units, new_description)


between_LOC1_and_LOC2 = Transformation(
    r"^difference_of_(.*)_and_(.*)_between_(.*)_and_(.*)$",
    _difference_of_X_and_Y_between_LOC1_and_LOC2,
)


def _surface_(match, snt) -> StandardName:
    """Component of a standard name, e.g. x_velocity where velocity is the
    existing standard name and x is a registered component"""
    groups = match.groups()
    assert len(groups) == 2
    surface = groups[0]
    if surface not in snt.affixes['surface'].values:
        raise errors.AffixKeyError(f'Standard surface "{surface}" not found in registry of the standard name table. '
                                   f'Available surfaces are: {snt.affixes["surface"].names}')
    sn = snt[groups[1]]
    new_description = f'{sn.description} {snt.affixes["surface"].values[surface]}'
    return StandardName(match.string, sn.units, new_description)


surface_ = Transformation(r"^(.*?)_(.*)$", _surface_)


def _component_(match, snt) -> StandardName:
    """Component of a standard name, e.g. x_velocity where velocity is the
    existing standard name and x is a registered component"""
    groups = match.groups()
    component = groups[0]
    if component not in snt.affixes['component'].values:
        raise errors.AffixKeyError(f'"{component}" is not a registered component. '
                                   f'Available components are: {list(snt.affixes["component"].names)}')
    sn = snt[groups[1]]
    if not sn.is_vector():
        raise errors.StandardNameError(f'"{sn.name}" is not a vector quantity.')
    new_description = f'{sn.description} {snt.affixes["component"].values[component]}'
    return StandardName(match.string, sn.units, new_description)


component_ = Transformation(r"^(.*)_(.*)$", _component_)


# def _surface_or_component(match, snt) -> StandardName:
#     """combine both because no two transformations are allowed to have the same pattern!"""
#     groups = match.groups()
#     assert len(groups) == 2
#     sn = snt[groups[1]]
#
#     s_or_c = groups[0]
#     if s_or_c not in snt.affixes.get("surfaces", []):
#         if s_or_c not in snt.affixes.get("components", []):
#             raise KeyError(f'Neither a valid surface nor component: "{s_or_c}".'
#                            f'Available surfaces are: {snt.affixes["surfaces"]} '
#                            f'and available components are: {snt.affixes["components"]}')
#     new_description = f'{sn.description} {snt.affixes["surfaces"][s_or_c].description}'
#     return StandardName(match.string, sn.units, new_description)
#
#
# surface_or_component = Transformation(r"^(.*)_(.*)$", _surface_or_component)


def _difference_of_X_across_device(match, snt) -> Union[StandardName, bool]:
    """Difference of X across device"""
    groups = match.groups()
    assert len(groups) == 2
    if groups[1] not in snt.affixes['device']:
        raise errors.AffixKeyError(f'Device {groups[1]} not found in registry of the standard name table. '
                                   f'Available devices are: {snt.affixes["device"].names}.')
    sn = snt[groups[0]]
    new_description = f"Difference of {sn.name} across {groups[1]}"
    return StandardName(match.string, sn.units, new_description)


difference_of_X_across_device = Transformation(r"^difference_of_(.*)_across_(.*)$",
                                               _difference_of_X_across_device)


def _difference_of_X_and_Y_across_device(match, snt) -> StandardName:
    """Difference of X and Y across device"""
    groups = match.groups()
    assert len(groups) == 3
    device = groups[2]
    if device not in snt.affixes['device']:
        raise errors.AffixKeyError(f'Device {device} not found in registry of the standard name table. '
                                   f'Available devices are: {snt.affixes["device"].names}')
    sn1 = snt[groups[0]]
    sn2 = snt[groups[1]]
    if sn1.units != sn2.units:
        raise ValueError(f'Units of "{sn1.name}" and "{sn2.name}" are not compatible: "{sn1.units}" and '
                         f'"{sn2.units}".')
    if sn1.name == sn2.name:
        new_description = f"Difference of {sn1.name} and {sn2.name} across {device}. {sn1.name}: {sn1.description} " \
                          f"{device}: {snt.affixes['device'].values[device]}"
    else:
        new_description = f"Difference of {sn1.name} and {sn2.name} across {device}. {sn1.name}: {sn1.description} " \
                          f"{sn2.name}: {sn2.description} {device}: {snt.affixes['device'].values[device]}"
    return StandardName(match.string, sn1.units, new_description)


difference_of_X_and_Y_across_device = Transformation(r"^difference_of_(.*)_and_(.*)_across_(.*)$",
                                                     _difference_of_X_and_Y_across_device)


def _X_at_LOC(match, snt) -> StandardName:
    groups = match.groups()
    assert len(groups) == 2
    sn = snt[groups[0]]
    loc = groups[1]
    if loc not in snt.affixes['location']:
        raise errors.AffixKeyError(f'StandardLocation "{loc}" not found in registry of the standard name table. '
                                   f'Available locations are: {snt.affixes["location"].names}')
    new_description = f"{sn} {snt.affixes['location'][loc]}"
    return StandardName(match.string, sn.units, new_description)


X_at_LOC = Transformation(r"^(.*)_at_(.*)$", _X_at_LOC)


def _in_reference_frame(match, snt) -> StandardName:
    """A standard name in a standard reference frame"""
    groups = match.groups()
    assert len(groups) == 2
    sn = snt[groups[0]]
    frame = groups[1]
    if frame not in snt.affixes['reference_frame']:
        raise errors.AffixKeyError(
            f'Reference Frame "{frame}" not found in registry of the standard name table. '
            f'Available reference frames are: {snt.affixes["reference_frame"].names}')
    new_description = f'{sn.description}. The quantity is relative to the reference frame "{frame}"'
    return StandardName(match.string, sn.units, new_description)


in_reference_frame = Transformation(r"^(.*)_in_(.*)$", _in_reference_frame)

affix_transformations = {'location': [between_LOC1_and_LOC2, X_at_LOC],
                         'component': [component_],
                         'surface': [surface_],
                         'device': [difference_of_X_and_Y_across_device, difference_of_X_across_device],
                         'reference_frame': [in_reference_frame]
                         }


def _get_transformation(name) -> List[Transformation]:
    t = affix_transformations.get(name, None)
    if t is None:
        raise KeyError(f'No transformation for affix "{name}". You may need to implement it first or check the '
                       f'spelling!')
    return t


class Affix:
    """Standard constructor is a prefix or suffix to a
    standard name, e.g. [x_]velocity, velocity[_in_rotating_frame]"""

    def __init__(self, name, description: str, values: Dict, transformation: Callable):
        self._name = name
        self._description = description
        self._values = values
        self._names = list(self._values.keys())
        self.transformation = transformation

    def __getitem__(self, item):
        return self._values[item]

    def __contains__(self, item):
        return item in self._values

    def __iter__(self):
        return iter(self._values)

    def to_dict(self) -> Dict:
        """Return the affix as a dictionary"""
        return {'description': self._description, **self._values}

    @staticmethod
    def from_dict(name, data: Dict):
        """Instantiate an Affix from a dictionary"""
        description = data.pop('description', None)
        if description is None:
            warnings.warn(f"Affix '{name}' has no description", UserWarning)
        return Affix(name, description, data, transformation=_get_transformation(name))

    @property
    def name(self):
        """Return the name of the standard item"""
        return self._name

    @property
    def description(self):
        """Return the description of the standard item"""
        return self._description

    @property
    def values(self):
        """Return the values of the standard item"""
        return self._values

    @property
    def names(self):
        """Return the names of the standard item"""
        return self._names

    def __repr__(self):
        return f'<{self.__class__.__name__}: name="{self._name}", description="{self.description}">'

    def __str__(self):
        return self.name

# currently not used but keep it:
# @dataclass
# class StandardReferenceFrame:
#     """Standard Reference Frame"""
#     name: str
#     type: str
#     origin: Tuple[float, float, float]
#     orientation: Dict
#     principle_axis: Union[str, Tuple[float, float, float], None] = None
#
#     def __post_init__(self):
#         if not isinstance(self.origin, (list, tuple)):
#             raise TypeError(f'Wrong type for "origin". Expecting tuple but got {type(self.origin)}')
#         self.origin = tuple(self.origin)
#         if isinstance(self.principle_axis, str):
#             self.principle_axis = self.orientation[self.principle_axis]
#
#     def to_dict(self):
#         return {self.name: dict(type=self.type,
#                                 origin=self.origin,
#                                 orientation=self.orientation,
#                                 principle_axis=self.principle_axis)}
#
#
# class StandardReferenceFrames:
#     """Collection of Standard Reference Frames"""
#
#     def __init__(self, standard_reference_frames: List[StandardReferenceFrame]):
#         self._standard_reference_frames = {srf.name: srf for srf in standard_reference_frames}
#         self._names = list(self._standard_reference_frames.keys())
#         self._index = 0
#
#     def __repr__(self):
#         return f'<StandardReferenceFrames: {self._names}>'
#
#     def __len__(self):
#         return len(self._names)
#
#     def __getitem__(self, item: Union[int, str]) -> StandardReferenceFrame:
#         if isinstance(item, int):
#             return self._standard_reference_frames[self._names[item]]
#         return self._standard_reference_frames[item]
#
#     def __contains__(self, item) -> bool:
#         return item in self._names
#
#     def __iter__(self):
#         return self
#
#     def __next__(self):
#         if self._index < len(self) - 1:
#             self._index += 1
#             return self._standard_reference_frames[self._names[self._index]]
#         self._index = -1
#         raise StopIteration
#
#     @property
#     def names(self):
#         """Return the names of the reference frames"""
#         return self._names
#
#     def to_dict(self) -> Dict:
#         """Return dictionary representation of StandardReferenceFrames"""
#         frames = [srf.to_dict() for srf in self._standard_reference_frames.values()]
#         srfdict = {'standard_reference_frames': {}}
#         for frame in frames:
#             for k, v in frame.items():
#                 srfdict['standard_reference_frames'][k] = v
#         return srfdict
