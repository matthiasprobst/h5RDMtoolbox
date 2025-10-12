import pathlib
from typing import Union


def hdf2json(filename: Union[str, pathlib.Path], **kwargs) -> pathlib.Path:
    """The default metamapper function for HDF5 files. It extracts metadata from the HDF5 file
    and stores it in a JSON-LD file. The filename of the metadata file is returned.

    Parameter
    --------
    filename: Union[str, pathlib.Path]
        The filename of the HDF5 file.

    Return
    ------
    pathlib.Path
        The filename of the metadata file (.json).

    Raises
    ------
    ValueError
        If the filename does not have the correct suffix.

    """
    if pathlib.Path(filename).suffix not in ('.hdf', '.hdf5', '.h5'):
        raise ValueError('The (default) HDF2JSON metamapper function can only be used with HDF5 files.')

    from h5rdmtoolbox.ld import hdf2jsonld

    return hdf2jsonld(filename=filename, skipND=1)


def hdf2ttl(filename: Union[str, pathlib.Path], file_uri, **kwargs) -> pathlib.Path:
    """
    The default metamapper function for HDF5 files. It extracts metadata from the HDF5 file
    and stores it in a Turtle (.ttl) file. The filename of the metadata file is
    returned.

    Parameter
    --------
    filename: Union[str, pathlib.Path]
        The filename of the HDF5 file.
    file_uri: str
        The URI to be used as the base for the RDF triples.
    Return
    ------
    pathlib.Path
        The filename of the metadata file (.ttl).
    """
    if pathlib.Path(filename).suffix not in ('.hdf', '.hdf5', '.h5'):
        raise ValueError('The (default) HDF2TTL metamapper function can only be used with HDF5 files.')

    from h5rdmtoolbox.ld import hdf2ttl

    return hdf2ttl(filename=filename, skipND=1, file_uri=file_uri)
