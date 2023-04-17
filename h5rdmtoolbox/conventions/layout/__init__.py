from .layout import Layout
from .validators import Any, Regex, Equal, Validator


class _Optional:

    def __call__(self, obj):
        if isinstance(obj, (int, float, str)):
            obj = Equal(obj)
        if not isinstance(obj, Validator):
            raise TypeError(f'Cannot make {obj} optional')
        obj.optional = True
        return obj


Optional = _Optional()

__all__ = ['Layout']
