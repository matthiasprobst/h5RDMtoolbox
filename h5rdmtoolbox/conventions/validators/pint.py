import pint

from .base import StandardAttributeValidator
from ... import get_ureg


class PintQuantityValidator(StandardAttributeValidator):

    def __call__(self, quantity, parent, **kwargs):
        try:
            get_ureg().Quantity(quantity)
            return True
        except (pint.UndefinedUnitError, TypeError) as e:
            raise ValueError(f'Quantity cannot be understood using ureg package: {scale}. Original error: {e}')
        return quantity


class PintUnitsValidator(StandardAttributeValidator):

    def __call__(self, value, parent, **kwargs):
        try:
            get_ureg().Unit(value)
        except (pint.UndefinedUnitError, TypeError) as e:
            raise ValueError(f'Units cannot be understood using ureg package: {value}. Original error: {e}')
        return value
