import enum
from typing import Union


class TargetMethod(enum.Enum):
    create_file = 1
    init = 1
    create_group = 2
    create_dataset = 3


class StandardAttributeValidator:
    pass

class StandardNameValidator(StandardAttributeValidator):
    pass


class StandardAttribute:

    def __init__(self,
                 name,
                 validators: StandardAttributeValidator,
                 target_methods: Union[str, TargetMethod],
                 default_value):
        self._name = name
        self._validators = validators
        if isinstance(target_methods, str):
            self._target_methods = TargetMethod[target_methods.strip('_')]
        elif isinstance(target_methods, TargetMethod):
            self._target_methods = target_methods
        else:
            raise TypeError('Invalid type for target method. Expecting "str" or "TargetMethod" '
                            f'but got "{type(target_methods)}".')
        self._default_value = default_value

    def __str__(self):
        pass

    def set(self, parent):
        """1. validate, 2. write attribute"""

    def get(self, parent):
        """get from parent object (group or dataset) and return original
        type based on the validator"""

StandardAttribute('standard_name_table',
                  validators=StandardNameValidator,
                  target_methods='__init__',
                  default_value=''
                  )
