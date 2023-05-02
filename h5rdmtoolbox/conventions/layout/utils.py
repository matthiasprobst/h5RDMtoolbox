"""utils of layout subpackage"""
import h5py
import typing


def get_subgroups(h5group: h5py.Group) -> typing.List[h5py.Group]:
    """Return a list of all groups in the given group."""
    groups = []

    def visitor(_, obj):
        """Visitor function for h5py.visititems()"""
        if isinstance(obj, h5py.Group):
            groups.append(obj)

    h5group.visititems(visitor)
    return groups


def get_h5datasets(h5group: h5py.Group) -> typing.List[h5py.Dataset]:
    """Return a list of all datasets in the given group."""
    return [h5group[k] for k in h5group.keys() if isinstance(h5group[k], h5py.Dataset)]
