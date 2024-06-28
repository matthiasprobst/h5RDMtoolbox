"""query module"""
import logging
import numpy as np
import re
import warnings

logger = logging.getLogger('h5rdmtoolbox')


def _eq(a, b):
    """Check if a == b"""
    if a is None or b is None:
        return False
    return a == b


def _arreq(a, b):
    """Check if a == b"""
    if a is None or b is None:
        return False
    return np.array_equal(a, b)


def _gt(a, b):
    """Check if a > b"""
    if a is None or b is None:
        return False
    return a > b


def _gte(a, b):
    """Check if a >= b"""
    if a is None or b is None:
        return False
    return a >= b


def _lt(a, b):
    """Check if a < b"""
    logger.debug(f'checking if a < b ({a} < {b})')
    if a is None or b is None:
        return False
    return a < b


def _in(a, b) -> bool:
    """Check if a is in b"""
    if a is None or b is None:
        return False
    return a in b


def _lte(a, b):
    """Check if a <= b"""
    if a is None or b is None:
        return False
    return a <= b


def _regex(value, pattern) -> bool:
    if value is None:
        return False

    if isinstance(value, np.bytes_):
        try:
            value = value.decode()
        except UnicodeDecodeError:
            warnings.warn(f'could not decode {value}', UserWarning)
            return False

    if isinstance(value, bytes):
        value = value.decode()

    value = str(value)

    match = re.search(pattern, value)
    if match is None:
        return False
    return True


def _userdefined(value, func) -> bool:
    if value is None:
        return False
    return func(value)


def _basename(value, basename) -> bool:
    if value is None:
        return False
    return _regex(value, pattern=f'^.*/{basename}$')


def _exists(value, tf: bool) -> bool:
    if tf:
        return value is not None
    return value is None


operator = {'$regex': _regex,
            '$basename': _basename,
            '$eq': _eq,
            '$gt': _gt,
            '$gte': _gte,
            '$lt': _lt,
            '$in': _in,
            '$lte': _lte,
            '$exists': _exists,
            '$userdefined': _userdefined}
value_operator = {'$eq': _arreq, '$gt': _gt, '$gte': _gte, '$lt': _lt, '$lte': _lte}


def _pass(obj, comparison_value):
    if get_ndim(comparison_value) == obj.ndim:
        return obj[()]
    return None


def _mean(obj, _):
    if obj.dtype.char == 'S':
        return None
    return np.mean(obj[()])


def get_ndim(value) -> int:
    """Return the dimension of the input value. Scalars have dimension 0, other inputs are parsed with np.ndim()"""
    if isinstance(value, (int, float)):
        return 0
    return np.ndim(value)


math_operator = {'$eq': _pass,
                 '$mean': _mean}
