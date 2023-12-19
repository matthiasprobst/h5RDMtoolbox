"""standard attribute module"""
import abc
import enum
import json
import pydantic
import warnings
from typing import Dict, List, Union

from . import errors, logger
from . import warnings as convention_warnings
from .consts import DefaultValue
from .. import get_config
from ..utils import DocStringParser
from ..wrapper.core import File, Group, Dataset

__doc_string_parser__ = {File: {'__init__': DocStringParser(File)},
                         Group: {'create_group': DocStringParser(Group.create_group),
                                 'create_dataset': DocStringParser(Group.create_dataset)}}

__all__ = ['StandardAttribute', ]


class StandardAttribute(abc.ABC):
    """StandardAttribute class for the standardized attributes

    Parameters
    ----------
    name: str
        The name of the attribute
    validator: str | dict
        The validator for the attribute. If the validator takes a parameter, pass it as dict.
        Examples for no-parameter validator: "$pintunits", "$standard_name", "$orcid", "$url"
        Examples for validator with parameter: {"$regex": "^[a-z0-9_]*$"}, {"$in": ["a", "b", "c"]}
    description: str
        The description of the attribute
    target_method: str
        The method to which the attribute belongs, e.g. "create_group". Valid values are
        "create_group", "create_dataset", "__init__".
    default_value: any, optional=DefaultValue.EMPTY
        If the attribute is positional, it has no default value, then pass DefaultValue.EMPTY (the default).
        Otherwise, pass the default value. The default value applies to all methods to which the attribute applies.
    alternative_standard_attribute; str, optional=None
        The name of the alternative standard attribute. If the attribute is not present, the alternative standard
        attribute is used. If None (default), no alternative standard attribute is defined.
    position: int, optional=None
        The position of the attribute. None puts it at the end.
    requirements: List[str] = None,
        The requirements for the attribute. Values are other standard names used in the convention.
        If None (default), no requirements are defined.
    """
    EMPTY = DefaultValue.EMPTY  # quasi positional
    NONE = DefaultValue.NONE  # keyword argument is None. None will not be written to the file

    VALID_TARGET_METHODS = ('__init__', 'create_group', 'create_dataset')
    METHOD_CLS_ASSIGNMENT = {'__init__': File,
                             'create_group': Group,
                             'create_dataset': Group,
                             'create_string_dataset': Group}
    PROPERTY_CLS_ASSIGNMENT = {'__init__': File,
                               'create_group': Group,
                               'create_dataset': Dataset,
                               'create_string_dataset': Dataset}

    def __init__(self,
                 name,
                 *,  # force keyword arguments
                 description,
                 validator,
                 target_method: str = None,
                 default_value=DefaultValue.EMPTY,
                 alternative_standard_attribute: str = None,
                 position: Union[None, Dict[str, str]] = None,
                 requirements: List[str] = None,
                 type_hint: str = None,
                 **kwargs):
        """

        Parameters
        ----------
        name: str
            The name of the attribute. The name is cut if it includes "-" and only the first part is taken,
            e.g. "comment-file" will be "comment". This is needed to define multiple attributes in a YAML file
            with the same "basename" ("basename" refers to the part before the "-", thus "comment" in the example).
        validator
        description
        default_value
        target_method: str
            The method to which the attribute belongs. Only one method can be specified.

            Note: In earlier versions multiple methods could be specified. This is not supported anymore because (a)
            it facilitates the code and makes it better to read and (b) the description of the attribute should be
            different depending on the method.
        alternative_standard_attribute
        position
        return_type
        requirements
        kwargs
        """
        # name of attribute:
        self.name = name.split('-', 1)[0]  # the attrs key

        try:
            validator.model_validate
        except AttributeError:
            raise TypeError(f'validator must be a pydantic.BaseModel and therefore have a "model_validate" method. '
                            f'Got {type(validator)} instead.')
        self.validator = validator
        # assert isinstance(self.validator, StandardAttributeValidator)

        # the human readable description of the attribute:
        if description[-1] != '.':
            description += '.'
        self.description = description

        # the attribute is associated with a method:
        if not isinstance(target_method, str):
            raise TypeError(f'target_method must be a string. Got {type(target_method)} instead.')
        if target_method not in self.VALID_TARGET_METHODS:
            raise ValueError(f'Invalid target method: "{target_method}".from '
                             f'Valid target methods are: {self.VALID_TARGET_METHODS}.')
        self.target_method = target_method

        # The default value
        if isinstance(default_value, str):
            _default_value = default_value.lower()
            if _default_value == '$none':
                default_value = DefaultValue.NONE
            elif _default_value == '$empty':
                default_value = DefaultValue.EMPTY
            elif _default_value == 'none':
                default_value = None
            else:
                default_value = DefaultValue(default_value)

        if alternative_standard_attribute is not None and default_value is self.EMPTY:
            # an alternative standard name is given but no default value. Set default value to the alternative
            default_value = DefaultValue.EMPTY
        self.default_value = default_value

        # an alternative attribute can be set, which means, that if this attribute is not present, the alternative
        # attribute is required instead:
        self.alternative_standard_attribute = alternative_standard_attribute

        # the position of the attribute within the method signature:
        self.position = position

        # The attribute may require other attributes to be present:
        if isinstance(requirements, str):
            requirements = [requirements]
        self.requirements = requirements

        # the type hint of the attribute shown in the method signature:
        if type_hint is None:
            type_hint = 'str'
        self.type_hint = type_hint

        # --- process the input:
        self.target_cls = self.PROPERTY_CLS_ASSIGNMENT[target_method]

        # check for unexpected entries:
        for _k in kwargs:
            logger.error(f'Unexpected entry "{_k}" for StandardAttribute, which is ignored.')

    def __repr__(self):
        if self.is_positional():
            return f'<{self.__class__.__name__}[positional/obligatory]("{self.name}"): "{self.description}">'
        return f'<{self.__class__.__name__} [keyword/optional]("{self.name}"): default_value="{self.default_value}" | "{self.description}">'

    def is_positional(self):
        """has no default value"""
        return self.default_value == DefaultValue.EMPTY

    # alias:
    is_optional = is_positional

    def is_obligatory(self):
        """is an obligatory attribute"""
        return self.default_value == DefaultValue.NONE

    def make_optional(self):
        """make this standard attribute optional by setting the default value to Default.NONE"""
        self.default_value = DefaultValue.NONE
        # disable and enable the convention to make the change effective:
        import h5rdmtoolbox as h5tbx
        _cache_cv = h5tbx.convention.get_current_convention()
        h5tbx.use(None)
        h5tbx.use(_cache_cv)

    def set(self, parent, value, attrs=None):
        """Write `value` to attribute of `parent`

        Parameters
        ----------
        parent: h5py.File, h5py.Group, h5py.Dataset
            The parent object to which the attribute is written
        value: any
            The value to write to the attribute. The value is validated before it is written.
        attrs: dict, optional=None
            Other attributes to be set. This is used during dataset creation only.
        """
        # first call the validator on the value:
        try:
            if value is None:
                return
                # if self.validator.allow_None:
                #     validated_value = self.validator(value, parent, attrs)
                # else:
                #     # None is passed. this is ignored
                #     return
            else:
                if isinstance(value, dict):
                    try:
                        # if a dict, we must fix some entries if there are nested standard validators:
                        for k in value.keys():
                            if hasattr(self.validator.model_fields[k].annotation, 'model_fields'):
                                value[k] = {'value': value[k]}
                        _value = self.validator.model_validate(value, context={'parent': parent, 'attrs': attrs})
                    except pydantic.ValidationError as err:
                        raise errors.StandardAttributeError(
                            f'Validation of "{value}" for standard attribute "{self.name}" failed.\n'
                            f'Expected fields: {self.validator.model_fields}\nPydantic error: {err}')
                    validated_value = json.dumps(value)
                else:
                    _value = self.validator.model_validate(dict(value=value),
                                                           context={'parent': parent, 'attrs': attrs})
                    if isinstance(_value.value, enum.Enum):
                        validated_value = _value.value.value
                    else:
                        if hasattr(_value.value, '__to_h5attrs__'):
                            validated_value = _value.value.__to_h5attrs__()
                        else:
                            # TODO why set str here?
                            # validated_value = str(_value.value)  # self.validator(value, parent, attrs)
                            if isinstance(_value.value, dict):
                                validated_value = json.dumps(_value.value)
                            elif isinstance(_value.value, (int, float, List)):
                                validated_value = _value.value  # self.validator(value, parent, attrs)
                            else:
                                validated_value = str(_value.value)  # self.validator(value, parent, attrs)
        except Exception as e:
            if get_config('ignore_standard_attribute_errors'):
                logger.warning(f'Setting "{value}" for standard attribute "{self.name}" failed. '
                               f'Original error: {e}')
                validated_value = value
            else:
                raise errors.StandardAttributeError(f'The value "{value}" for standard attribute "{self.name}" '
                                                    f'could not be set. Please check the convention file wrt. the '
                                                    f'rule for this attribute. The following error message might '
                                                    f'not always explain the origin of the problem:\n{e}') from e
        super(type(parent.attrs), parent.attrs).__setitem__(self.name, validated_value)

    def get(self, parent):
        """Read the attribute from `parent`

        Parameters
        ----------
        parent: h5py.File, h5py.Group, h5py.Dataset
            The parent object from which the attribute is read

        Returns
        -------
        any
            The value of the attribute. The validator has a get method that is called on the return
            The type of the return value is thus dependent the validator. If the get method is not
            implemented, the return value is the same as the value stored in the attribute.

        Raises
        ------
        KeyError
            If the attribute name does not exist

        StandardAttributeValidationWarning
            If the attribute could not be validated during reading. The raw value is returned though.
        """
        try:
            ret_val = super(type(parent.attrs), parent.attrs).__getitem__(self.name)
        except KeyError:
            ret_val = self.default_value
            if ret_val is self.NONE:
                return None
        # is there a return value associated with the validator?
        return self.validate(ret_val, parent=parent)
        # try:
        #     ret_val = self.validate(ret_val, parent=parent)
        # except pydantic.ValidationError as e:
        #     errors.StandardAttributeError(f'The convention "{parent.convention.name}" detected an invalid attribute: '
        #                                   f'Value "{ret_val}" for "{self.name}" is invalid.')
        # finally:
        #     return ret_val

    def to_dict(self):
        """return a dict representation of the standard attribute"""

        if self.default_value is DefaultValue.NONE:
            default_value_str = '$optional'
        elif self.default_value is DefaultValue.EMPTY:
            default_value_str = '$obligatory'
        else:
            default_value_str = self.default_value

        return dict(description=self.description,
                    target_method=self.target_method,
                    validator=f'${self.validator.__name__}',
                    default_value=default_value_str)

    def validate(self, value, parent, attrs=None):
        """validate"""
        if value is not None:
            if isinstance(value, str) and value.startswith('{') and value.endswith('}'):
                value = json.loads(value)
            if isinstance(value, dict):
                try:
                    model_fields = self.validator.model_fields
                    if 'value' in model_fields and 'typing.Dict' in str(model_fields['value'].annotation):
                        return self.validator.model_validate(dict(value=value),
                                                             context=dict(attrs=attrs, parent=parent)).value
                    else:
                        _value = value.copy()
                        for k, v in value.items():
                            if self.validator.model_fields[k].annotation not in (int, str, float, bool):
                                if not isinstance(v, dict):
                                    _value[k] = {'value': v}
                        return self.validator.model_validate(_value, context=dict(attrs=attrs, parent=parent))
                except pydantic.ValidationError as err:
                    warnings.warn(f'The attribute "{self.name}" could not be validated due to: {err}',
                                  convention_warnings.StandardAttributeValidationWarning)
                    return value

        try:
            _value = self.validator.model_validate(dict(value=value),
                                                   context=dict(attrs=attrs, parent=parent)).value
            if isinstance(_value, enum.Enum):
                return _value.value
            return _value
        except pydantic.ValidationError as err:
            warnings.warn(f'The attribute "{self.name}" could not be validated by the convention '
                          f'"{parent.convention.name}".\nPydantic error: \n{err}',
                          convention_warnings.StandardAttributeValidationWarning)
        return value
        # return self.validator.model_validate(dict(value=self.default_value),
        #                                      context=dict(attrs=attrs, parent=parent))
