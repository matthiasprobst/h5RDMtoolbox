import pint

from . import StandardAttributeValidator
from .... import get_ureg


class PintQuantityValidator(StandardAttributeValidator):

    def __call__(self, quantity, parent, **kwargs):
        try:
            get_ureg().Quantity(quantity)
        except (pint.UndefinedUnitError, TypeError) as e:
            raise ValueError(f'Quantity cannot be understood using ureg package: {quantity}. Original error: {e}')
        return str(quantity)


class PintUnitsValidator(StandardAttributeValidator):

    def __call__(self, value, parent, **kwargs) -> str:
        try:
            get_ureg().Unit(value)
        except (pint.UndefinedUnitError, TypeError) as e:
            raise ValueError(f'Units cannot be understood using ureg package: {value}. Original error: {e}')
        return str(value)
