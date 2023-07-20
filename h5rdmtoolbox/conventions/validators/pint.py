import pint

from .base import StandardAttributeValidator
from ... import get_ureg


class PintQuantityValidator(StandardAttributeValidator):

    def __call__(self, scale, parent, **kwargs):
        try:
            get_ureg().Quantity(scale)
            return True
        except (pint.UndefinedUnitError, TypeError):  # as e:
            return False


class PintUnitsValidator(StandardAttributeValidator):

    def __call__(self, value, parent, **kwargs):
        try:
            get_ureg().Unit(value)
        except (pint.UndefinedUnitError, TypeError):  # as e:
            return False  # UndefinedUnitError(f'Units cannot be understood using ureg package: {_units}. --> {e}')
        return True
