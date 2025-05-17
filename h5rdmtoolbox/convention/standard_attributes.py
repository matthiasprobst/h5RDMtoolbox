"""standard attribute module"""
import json
import logging
import warnings
from typing import Dict, List, Union

import h5py
import pydantic
import typing_extensions
from pydantic import HttpUrl

from . import errors
from .consts import DefaultValue
from .. import get_config
from ..utils import DocStringParser, parse_object_for_attribute_setting
from ..wrapper.core import File, Group, Dataset

logger = logging.getLogger('h5rdmtoolbox')

__doc_string_parser__ = {File: {'__init__': DocStringParser(File)},
                         Group: {'create_group': DocStringParser(Group.create_group),
                                 'create_dataset': DocStringParser(Group.create_dataset)}}

__all__ = ['StandardAttribute', ]


class StandardAttribute:
    """StandardAttribute class for the standardized attributes

    Parameters
    ----------
    name: str
        The name of the attribute
    validator: Union[pydantic.BaseModel, typing_extensions._AnnotatedAlias]
        The validator for the attribute. If the validator takes a parameter, pass it as dict.
        Examples for no-parameter validator: "$pintunits", "$standard_name", "$orcid", "$url"
        Examples for validator with parameter: {"$regex": r"^[a-z0-9_]*$"}, {"$in": ["a", "b", "c"]}
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
                 validator: Union[pydantic.BaseModel, typing_extensions._AnnotatedAlias],
                 target_method: str = None,
                 default_value=DefaultValue.EMPTY,
                 alternative_standard_attribute: str = None,
                 position: Union[None, Dict[str, str]] = None,
                 requirements: List[str] = None,
                 type_hint: str = None,
                 rdf_predicate: str = None,
                 frdf_predicate: str = None,
                 **kwargs):
        # name of attribute:
        self.name = name.split('-', 1)[0]  # the attrs key

        # if not isinstance(validator, typing_extensions._AnnotatedAlias):
        #     if not issubclass(validator, pydantic.BaseModel):
        #         raise TypeError(f'validator must be a pydantic.BaseModel or a typing_extensions._AnnotatedAlias. '
        #                         f'Got {type(validator)} instead.')
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

        if rdf_predicate is not None:
            try:
                HttpUrl(rdf_predicate)
            except pydantic.ValidationError:
                raise TypeError(f'rdf_predicate must be a valid URL. Got {rdf_predicate} instead.')
        if frdf_predicate is not None:
            try:
                HttpUrl(frdf_predicate)
            except pydantic.ValidationError:
                raise TypeError(f'rdf_predicate must be a valid URL. Got {frdf_predicate} instead.')
        self.rdf_predicate = rdf_predicate
        self.frdf_predicate = frdf_predicate
        if frdf_predicate is not None and target_method != "__init__":
            raise ValueError(
                f'frdf_predicate is only supported for the __init__ method. Got {target_method} instead.'
            )

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
            return f'<{self.__class__.__name__}@{self.target_method}[positional/obligatory]("{self.name}"): "{self.description}">'
        return f'<{self.__class__.__name__}@{self.target_method}[keyword/optional]("{self.name}"): default_value="{self.default_value}" | "{self.description}">'

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
                    key0 = list(self.validator.model_fields.keys())[0]
                    logger.debug(f'validating standard attribute "{self.name}" with '
                                 f'"{self.validator.model_fields[key0]}"="{value}"')
                    self.validator.model_validate({key0: value}, context={'parent': parent, 'attrs': attrs})
                    return super(type(parent.attrs), parent.attrs).__setitem__(self.name, json.dumps(value))
                except pydantic.ValidationError as err:
                    raise errors.StandardAttributeError(
                        f'Validation of "{value}" for standard attribute "{self.name}" failed.\n'
                        f'Expected fields: {self.validator.model_fields}\nPydantic error: {err}')
            else:
                try:
                    model_fields = list(self.validator.model_fields.keys())
                except AttributeError:
                    tmp_model = pydantic.create_model(self.name, value=(self.validator, ...))
                    try:
                        _validated_value = tmp_model.model_validate({'value': value},
                                                                    context={'parent': parent, 'attrs': attrs})
                    except pydantic.ValidationError as err:
                        raise errors.StandardAttributeError(
                            f'Validation of "{value}" for standard attribute "{self.name}" failed.'
                            f'\nPydantic error: {err}')
                    validated_value = _validated_value.value
                else:
                    key0 = model_fields[0]  # ==self.name!
                    try:
                        _validated_value = self.validator.model_validate({key0: value},
                                                                         context={'parent': parent, 'attrs': attrs})
                    except pydantic.ValidationError as err:
                        raise errors.StandardAttributeError(
                            f'Validation of "{value}" for standard attribute "{self.name}" failed.\n'
                            f'Expected fields: {self.validator.model_fields}\nPydantic error: {err}')
                    validated_value = getattr(_validated_value, key0)

                ret = super(type(parent.attrs), parent.attrs).__setitem__(
                    self.name,
                    parse_object_for_attribute_setting(validated_value)
                )
                if self.rdf_predicate is not None:
                    parent.rdf[self.name].predicate = self.rdf_predicate
                if self.frdf_predicate is not None:
                    parent.frdf[self.name].predicate = self.frdf_predicate
                return ret

    def get(self, parent: Union[h5py.File, h5py.Group, h5py.Dataset]):
        """Read the attribute from `parent`

        Parameters
        ----------
        parent: Union[h5py.File, h5py.Group, h5py.Dataset]
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
        # validate:
        if isinstance(ret_val, str):
            if ret_val.startswith('{') and ret_val.endswith('}'):
                ret_val = json.loads(ret_val)
            # this is a reference to another attribute

        ignore_get_std_attr_err = get_config('ignore_get_std_attr_err')
        try:
            model_fields = list(self.validator.model_fields.keys())
        except AttributeError:
            tmp_model = pydantic.create_model(self.name, value=(self.validator, ...))
            try:
                _validated_value = tmp_model.model_validate({'value': ret_val},
                                                            context={'parent': parent, 'attrs': None})
            except pydantic.ValidationError as err:
                if ignore_get_std_attr_err:
                    warnings.warn(f'Validation of "{ret_val}" for standard attribute "{self.name}" failed.\n'
                                  f'Pydantic error: {err}',
                                  errors.StandardAttributeValidationWarning)
                else:
                    raise errors.StandardAttributeError(
                        f'Validation of "{ret_val}" for standard attribute "{self.name}" failed.\n'
                        f'Pydantic error: {err}')
            else:
                ret_val = _validated_value.value
        else:
            key0 = model_fields[0]
            try:
                ret_val = getattr(
                    self.validator.model_validate({key0: ret_val}, context=dict(attrs=None, parent=parent)),
                    key0)
            except pydantic.ValidationError as e:
                if ignore_get_std_attr_err:
                    warnings.warn(
                        f'Validation of "{ret_val}" for standard attribute "{self.name}" failed.\n'
                        f'Expected fields: {self.validator.model_fields}\nPydantic error: {e}',
                        errors.StandardAttributeValidationWarning)
                else:
                    raise errors.StandardAttributeError(
                        f'Validation of "{ret_val}" for standard attribute "{self.name}" failed.\n'
                        f'Expected fields: {self.validator.model_fields}\nPydantic error: {e}')
        return ret_val

        # return self.validate(ret_val, parent=parent)
        # try:
        #     ret_val = self.validate(ret_val, parent=parent)
        # except pydantic.ValidationError as e:
        #     errors.StandardAttributeError(f'The convention "{parent.convention.name}" detected an invalid attribute: '
        #                                   f'Parameter "{ret_val}" for "{self.name}" is invalid.')
        # finally:
        #     return ret_val

    # def to_dict(self):
    #     """return a dict representation of the standard attribute"""
    #
    #     if self.default_value is DefaultValue.NONE:
    #         default_value_str = '$optional'
    #     elif self.default_value is DefaultValue.EMPTY:
    #         default_value_str = '$obligatory'
    #     else:
    #         default_value_str = self.default_value
    #
    #     return dict(description=self.description,
    #                 target_method=self.target_method,
    #                 validator=f'${self.validator.__name__}',
    #                 default_value=default_value_str)
    #
    def validate(self, value, parent=None, attrs=None) -> bool:
        """validate"""
        if value is None:
            return True

        if isinstance(value, dict):
            try:
                key0 = list(self.validator.model_fields.keys())[0]
                logger.debug(f'validating standard attribute "{self.name}" with '
                             f'"{self.validator.model_fields[key0]}"="{value}"')
                self.validator.model_validate({key0: value}, context={'parent': parent, 'attrs': attrs})
                return True
            except pydantic.ValidationError as err:
                return False

        try:
            model_fields = list(self.validator.model_fields.keys())
        except AttributeError:
            tmp_model = pydantic.create_model(self.name, value=(self.validator, ...))
            try:
                _validated_value = tmp_model.model_validate({'value': value},
                                                            context={'parent': parent, 'attrs': attrs})
            except pydantic.ValidationError as err:
                return False
            return False

        key0 = model_fields[0]  # ==self.name!
        try:
            _validated_value = self.validator.model_validate({key0: value},
                                                             context={'parent': parent, 'attrs': attrs})
        except pydantic.ValidationError as _:
            return False
        return True
