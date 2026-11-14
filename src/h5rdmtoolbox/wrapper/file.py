"""HDF5 file lifecycle and per-file scientific read policy."""
from __future__ import annotations

from typing import Dict, Optional, Union
from pathlib import Path
from datetime import datetime, timezone
import os
import pathlib
import shutil
import warnings

from h5py._objects import ObjectID
import h5py
from h5py._hl.base import phil
import rdflib

from ..ld._types import RDFMappingEntry
from .h5attr import WrapperAttributeManager
from ..ld.utils import _serialize_graph as _serialize_ld_graph
from .._cfg import get_config
from ..ld import rdf
from .. import utils
from ._shared import (
    H5KWARGS,
    _delattr,
    _normalize_file_uri_and_prefix,
    _validate_jsonld_file_uri,
    _warn_on_missing_file_uri,
    logger,
)
from .group import Group


class File(h5py.File, Group):
    """Main wrapper around h5py.File.

    Adds additional features and methods to h5py.File in order to streamline the work with
    HDF5 files with explicit metadata and per-file scientific read settings.


    .. note:: All features from h5py packages are preserved.


    Parameters
    ----------
    filename : str
        The name of the file to open. If the file mode is 'w' or 'r+' and the file does not exist,
        a temporary file is created in the user's temporary directory.
    mode : {'r', 'r+', 'w', 'w-', 'x', 'a'}, optional
        The mode in which to open the file. The default is 'r'.
    decode_calibration : bool, default=False
        Apply attached scale/offset metadata during xarray reads. Raw .values
        access always returns stored values.
    **kwargs : Dict
        Additional keyword arguments are passed to h5py.File.


    Notes
    -----
    The following methods are added to the h5py.File object:

    * moveto(): Move the file to a new location.
    * saveas(): Save the file to a new location.
    * reopen(): Reopen the closed file.

    The following attributes are added to the h5py.File object:

    * rdf: RDF Manager
    * hdf_filename: (pathlib.Path) The name of the file, accessible even if the file is closed.
    * version: (str) The version of the package used to create the file.
    * modification_time: (datetime) The modification time of the file.
    * creation_time: (datetime) The creation time of the file.
    * filesize: (int) The size of the file in bytes.

    .. seealso:: :class:`h5rdmtoolbox.core.Group`
    """

    @property
    def attrs(self) -> WrapperAttributeManager:
        """Return an attribute manager that is inherited from h5py's attribute manager"""
        with phil:
            return WrapperAttributeManager(self)

    def __getitem__(self, name):
        from .group import Group
        return Group.__getitem__(self, name)

    def values(self):
        from .group import Group
        return Group.values(self)

    def items(self):
        from .group import Group
        return Group.items(self)

    def visititems(self, func):
        from .group import Group
        return Group.visititems(self, func)

    @property
    def version(self) -> str:
        """Return version stored in file, which is the package version used at the time of creation.
        Not necessarily the current version of the package."""
        return self.get("h5rdmtoolbox", {}).attrs.get("__h5rdmtoolbox_version__")

    @property
    def modification_time(self) -> datetime:
        """Return the modification from the file. Not stored as an attribute!"""
        return datetime.fromtimestamp(
            self._hdf_filename.stat().st_mtime, tz=timezone.utc
        ).astimezone()

    @property
    def creation_time(self) -> datetime:
        """Return the creation time from the file. Not stored as an attribute!"""
        return datetime.fromtimestamp(
            self._hdf_filename.stat().st_ctime, tz=timezone.utc
        ).astimezone()

    @property
    def filesize(self):
        """
        Returns file size in units of bytes.

        Returns
        -------
        pint.Quantity
            The file size in units of bytes.

        """
        return utils.get_filesize(self.filename)

    def __init__(
        self,
        name: Union[str, Path] = None,
        mode: str = None,
        attrs: Dict = None,
        *,
        decode_calibration: bool = False,
        **kwargs,
    ):
        if not isinstance(decode_calibration, bool):
            raise TypeError("decode_calibration must be a bool")
        self._decode_calibration = decode_calibration
        is_fileobj_init = False
        # path is file object:
        if isinstance(name, ObjectID):
            # Select HDF5 file-opening options:
            super(File, self).__init__(name, mode, **kwargs)
            self._hdf_filename = Path(self.filename)
            return
        elif hasattr(name, "read") and hasattr(name, "seek"):
            super(File, self).__init__(name, mode, **kwargs)
            self._hdf_filename = Path(self.filename)
            is_fileobj_init = True

        if not is_fileobj_init:
            # name is path or None:
            if name is None:
                _tmp_init = True
                logger.debug("An empty File class is initialized")
                name = utils.touch_tmp_hdf5_file()
                if mode is None:
                    mode = "r+"
                else:
                    mode = mode
            elif isinstance(name, (str, pathlib.Path)):
                logger.debug("A filename is given to initialize the File class")
                fname = pathlib.Path(name)
                # a filename is given.

                if mode is None:  # mode not given:
                    # file does exist and mode not given --> read only!
                    if fname.exists():
                        mode = "r"
                        logger.debug(
                            'Mode is set to "r" because file exists and mode was not given.'
                        )

                    # file does not exist and mode is not given--> write!
                    elif not fname.exists():
                        raise FileNotFoundError(
                            f'File "{fname}" does not exist and mode is not given.'
                        )

                elif mode == "w" and fname.exists():
                    fname.unlink()
                    logger.debug(
                        'File exists and mode is set to "w". Deleting file first.'
                    )
                # else mode is given, so just continue... may be correct, may be not... let h5py find out

            if mode is None:
                logger.debug('Mode not set. Set it to "r" by default')
                mode = "r"
            elif not isinstance(name, (str, Path)):
                raise ValueError(
                    f'It seems that no proper file name is passed: type of "{name}" is {type(name)}'
                )
            else:
                if mode == "r+":
                    if not Path(name).exists():
                        _tmp_init = True
                        # mode = 'r+'
                        # "touch" the file, so it exists
                        _h5pykwargs = kwargs.copy()
                        for k in list(kwargs.keys()):
                            if k not in H5KWARGS:
                                _h5pykwargs.pop(k, None)
                        with h5py.File(name, mode="w", **_h5pykwargs) as _h5:
                            pass  # just touching the file
                        logger.debug(
                            f'An empty File class is initialized for "{name}".Mode is set to "r+"'
                        )

            if attrs is None:
                attrs = {}

            attrs = dict(attrs)

            logger.debug(
                f"Initializing h5py.File with name={name}, mode={mode} and kwargs={kwargs}"
            )
            try:
                super().__init__(name=name, mode=mode, **kwargs)
            except OSError as e:
                logger.error(f"Unable to open file {name}. Error message: {e}")
                from ..utils import DownloadFileManager

                DownloadFileManager().remove_corrupted_file(name)

                raise e
            self._hdf_filename = Path(self.filename)

            if self.mode != "r":
                # update file toolbox version, wrapper version
                if get_config("auto_create_h5tbx_version"):
                    if "h5rdmtoolbox" not in self and get_config(
                        "auto_create_h5tbx_version"
                    ):
                        utils.create_h5tbx_version_grp(self)
                for k, v in attrs.items():
                    self.attrs[k] = v

    def __setattr__(self, key, value):
        if not key.startswith("_"):
            raise AttributeError("Store HDF5 metadata through attrs, not Python properties")
        super().__setattr__(key, value)

    def __repr__(self):
        return super().__repr__()

    def __str__(self):
        return super().__str__()

    def __delattr__(self, item):
        _delattr(self, item)



    @property
    def rdf(self):
        """Return RDF Manager"""
        return rdf.RDFManager(self.attrs)

    @property
    def iri(self):
        """Deprecated. Use rdf instead."""
        warnings.warn(
            'Property "iri" is deprecated. Use "rdf" instead.', DeprecationWarning
        )
        return rdf.RDFManager(self.attrs)

    # @property
    # def attrsdef(self) -> definition.DefinitionManager:
    #     """Return DefinitionManager"""
    #     return definition.DefinitionManager(self.attrs)

    def validate(self, shapes, **kwargs):
        """Validate structure and metadata against explicit SHACL shapes."""
        from ..validation import validate
        return validate(self, shapes, **kwargs)

    def shacl_validate(
        self,
        data: Union[str, rdflib.Graph] = None,
        source: Union[str, Path] = None,
        shacl_format: Union[str] = "turtle",
        **kwargs,
    ):
        """Validate the HDF5 file content against SHACL shapes.

        Parameters
        ----------
        data : Union[str, rdflib.Graph]
            The data graph as string or rdflib.Graph. If None, the data is taken from the HDF5 file.
        source : Union[str, Path]
            The SHACL shapes as string or path to file.
        shacl_format : str
            The format of the SHACL shapes. Default is 'turtle'.
        **kwargs : Dict
            Additional keyword arguments are passed to the validate_hdf function.

        Returns
        -------
        ValidationResult
            The result of the validation containing:
            - conforms: bool
            - results_graph: rdflib.Graph
            - results_text: str
            - messages: List[str]
        """
        from ..ld.shacl import validate_hdf

        return validate_hdf(
            hdf_source=self,
            shacl_data=data,
            shacl_source=source,
            shacl_format=shacl_format,
            **kwargs,
        )

    def sparql(self,
               query,
               **kwargs):
        """Run a SPARQL query on the RDF graph of the file."""
        from ..ld.sparql import sparql
        return sparql(self, query, **kwargs)


    def moveto(self, destination: Path, overwrite: bool = False) -> Path:
        """Move the opened file to a new destination.

        Parameters
        ----------
        destination : Path
            New filename.
        overwrite : bool
            Whether to overwrite an existing file.

        Return
        ------
        new_filepath : Path
            Path to new file locationRaises

        Raises
        ------
        FileExistsError
            If destination file exists and overwrite is False.
        """
        dest_fname = Path(destination)
        if dest_fname.exists() and not overwrite:
            raise FileExistsError(
                f'The target file "{dest_fname}" already exists and overwriting is set to False.'
                " Not moving the file!"
            )
        logger.debug("Moving file %s to %s", {self._hdf_filename}, dest_fname)

        if not dest_fname.parent.exists():
            Path.mkdir(dest_fname.parent, parents=True)
            logger.debug("Created directory %s", dest_fname.parent)

        mode = self.mode
        self.close()
        shutil.move(self._hdf_filename, dest_fname)
        super().__init__(dest_fname, mode=mode)
        new_filepath = dest_fname.absolute()
        self._hdf_filename = new_filepath
        return new_filepath

    def saveas(self, filename: Path, overwrite: bool = False) -> "File":
        """
        Save this file under a new name (effectively a copy). This file is closed and re-opened
        from the new destination using the previous file mode.

        Parameters
        ----------
        filename: Path
            New filename.
        overwrite: bool, default=False
            Whether not to overwrite an existing filename.

        Returns
        -------
        File
            Instance of moved File

        """
        _filename = Path(filename)
        if _filename.is_file():
            if overwrite:
                os.remove(_filename)
            else:
                raise FileExistsError(
                    "Note: File was not moved to new location as a file already exists with this name"
                    " and overwriting was disabled"
                )

        src = self.filename
        mode = self.mode
        self.close()  # close this instance

        shutil.copy2(src, _filename)
        self._hdf_filename = _filename
        return File(_filename, mode=mode, decode_calibration=self.decode_calibration)

    def reopen(self, mode: str = "r+") -> None:
        """Open the closed file"""
        self.__init__(self._hdf_filename, mode=mode)

    @staticmethod
    def open(filename: Union[str, pathlib.Path], mode: str = "r+") -> "File":
        """Open the closed file and use the correct wrapper class

        Parameters
        ----------
        filename: str ot pathlib.Path
            Path to file to be opened
        mode: str
            Mode used to open the file: r, r+, w, w-, x, a

        Returns
        -------
        Subclass of File
        """
        return File(filename, mode)

    def dump_jsonld(
        self,
        indent: int = 2,
        skipND: int = 1,
        structural: bool = True,
        contextual: bool = True,
        context: Optional[Dict] = None,
        file_uri: Optional[str] = None,
    ) -> str:
        """Dump the file content as JSON-LD string"""
        _validate_jsonld_file_uri(file_uri)

        return self.serialize(
            fmt="json-ld",
            indent=indent,
            skipND=skipND,
            structural=structural,
            contextual=contextual,
            context=context,
            file_uri=file_uri,
        )

    def serialize(
        self,
        fmt: str,
        skipND: int = 1,
        structural: bool = True,
        contextual: bool = True,
        file_uri: Optional[Union[str, Dict]] = None,
        context: Optional[Dict] = None,
        indent: int = 2,
        rdf_mappings: Dict[str, RDFMappingEntry] = None,
    ):
        """Serialize the file content to a specific format"""
        from h5rdmtoolbox.ld import get_ld

        _warn_on_missing_file_uri(file_uri)
        file_uri, prefix = _normalize_file_uri_and_prefix(file_uri)

        graph = get_ld(
            self.hdf_filename,
            structural=structural,
            contextual=contextual,
            file_uri=file_uri,
            skipND=skipND,
            context=context,
            rdf_mappings=rdf_mappings,
        )
        if prefix is not None:
            graph.bind(prefix, file_uri)
        return _serialize_ld_graph(graph, fmt=fmt, indent=indent, context=context)
