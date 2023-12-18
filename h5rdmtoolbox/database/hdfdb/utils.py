import h5py
from typing import Union

OBJ_FLT_DICT = {'group': h5py.Group,
                'groups': h5py.Group,
                'dataset': h5py.Dataset,
                'datasets': h5py.Dataset,
                '$group': h5py.Group,
                '$groups': h5py.Group,
                '$dataset': h5py.Dataset,
                '$datasets': h5py.Dataset}


def parse_obj_filter_input(objfilter: Union[str, h5py.Dataset, h5py.Group]) -> Union[h5py.Dataset, h5py.Group, None]:
    """Return the object based on the input string

    Parameters
    ----------
    objfilter : str or h5py.Dataset or h5py.Group
        The object to filter for. If it is a string, it must be one of the following:
        'group', 'groups', 'dataset', 'datasets', '$group', '$groups', '$dataset', '$datasets'

    Raises
    ------
    ValueError
        If the input string is not in the list of valid strings (see OBJ_FLT_DICT)
    TypeError
        If the input is not a string or a h5py object (h5py.Dataset or h5py.Group)

    Returns
    -------
    h5py.Dataset or h5py.Group or None
        The object to filter for
    """
    if objfilter is None:
        return
    if isinstance(objfilter, str):
        _obj_cls = OBJ_FLT_DICT.get(objfilter.lower(), None)
        if _obj_cls is None:
            raise KeyError(f'Expected values for argument objfilter are one of these: {OBJ_FLT_DICT.keys()},'
                           f' not "{objfilter}"')
        return _obj_cls
    if not issubclass(objfilter, (h5py.Dataset, h5py.Group)):
        raise TypeError(f'Expected values for argument objfilter are one of these: {OBJ_FLT_DICT.keys()},'
                        f' not {objfilter}')
    return objfilter
