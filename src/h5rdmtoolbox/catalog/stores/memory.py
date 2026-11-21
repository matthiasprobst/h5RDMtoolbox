"""Local RDF storage backed by an in-memory graph."""

import logging
import pathlib
import shutil
from typing import List, Tuple, Union

import rdflib
from rdflib.graph import _TripleType

from ..abstracts import RDFStore

logger = logging.getLogger("h5rdmtoolbox.catalog")


class InMemoryRDFStore(RDFStore):
    """In-memory RDF database that can upload files and return a combined graph."""

    __supports_named_graphs__ = False
    __default_expected_file_extensions__ = {
        ".ttl",
        ".rdf",
        ".jsonld",
        ".nt",
        ".xml",
        ".n3",
    }
    __populate_on_init__ = True

    def __init__(
        self,
        data_dir: Union[str, pathlib.Path],
        recursive_exploration: bool = True,
        formats: Union[str, List[str], Tuple[str]] = None,
    ):
        """Initializes the InMemoryRDFStore.

        Parameters
        ----------
        data_dir : Union[str, pathlib.Path]
            The directory where RDF files are stored.
        recursive_exploration : bool, optional
            If True, the directory will be explored recursively for RDF files. Default is False.
        formats : Union[str, List[str], Tuple[str]], optional
            The expected file formats/extensions. Can be a single string or a list/tuple of strings.
            Default is None, which uses the default expected file extensions.
        """
        if formats is None:
            formats = self.__default_expected_file_extensions__
        elif isinstance(formats, str):
            formats = {
                f".{formats.lstrip('.')}",
            }
        elif isinstance(formats, (list, set, tuple)):
            formats = {f".{fmt.lstrip('.')}" for fmt in formats}
        else:
            raise ValueError("formats must be a string or a list/set/tuple of strings.")

        for _fmt in formats:
            if _fmt not in self.__default_expected_file_extensions__:
                raise ValueError(f"File format '{_fmt}' not supported.")

        self._expected_file_extensions = formats
        self._data_dir = pathlib.Path(data_dir).resolve()
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._recursive_exploration = recursive_exploration
        self._filenames = []
        self._graphs = {}
        self._combined_graph = rdflib.Graph()
        if self.__populate_on_init__:
            self.populate()

    @property
    def data_dir(self) -> pathlib.Path:
        """Returns the data directory where files are stored."""
        return self._data_dir

    def populate(self, recursive: bool = None) -> "InMemoryRDFStore":
        """Populates the RDF store by scanning the data directory for RDF files and adding them to the graph."""
        _recursive_exploration = recursive or self._recursive_exploration
        for _ext in self._expected_file_extensions:
            if _recursive_exploration:
                self._filenames.extend(
                    [f.resolve().absolute() for f in self.data_dir.rglob(f"*{_ext}")]
                )
            else:
                self._filenames.extend(
                    [f.resolve().absolute() for f in self.data_dir.glob(f"*{_ext}")]
                )
        self._filenames = list(set(self._filenames))  # remove duplicates
        for filename in self._filenames:
            logger.debug(
                f"Adding file '{filename}' to the RDF store {self.__class__.__name__}."
            )
            self._add_to_graph(filename)
        return self

    @property
    def filenames(self):
        """Returns the list of filenames uploaded to the store."""
        return self._filenames

    def _upload_file(
        self,
        filename: Union[str, pathlib.Path],
        validate: bool = False,
        skip_unsupported: bool = False,
    ) -> bool:
        """Uploads a file to the in-memory RDF store.

        Parameters
        ----------
        filename : Union[str, pathlib.Path]
            The path to the RDF file to upload.
        validate : bool, optional
            If True, validate against registered shapes before uploading. Default is False.
        skip_unsupported : bool, optional
            If True, unsupported file types will be skipped without raising an error.

        Returns
        -------
        bool
            True if the file was uploaded successfully, False if skipped due to unsupported type.
        """
        filename = pathlib.Path(filename).resolve().absolute()
        if not filename.exists():
            raise FileNotFoundError(f"File {filename} not found.")
        if filename.suffix not in self._expected_file_extensions:
            if not skip_unsupported:
                raise ValueError(f"File type {filename.suffix} not supported.")
            if skip_unsupported:
                return False
        if filename in self._filenames:
            self._filenames.remove(filename)
        self._filenames.append(filename)
        if filename.parent != self.data_dir:
            shutil.copy(filename, self.data_dir / filename.name)
        self._add_to_graph(filename)
        return True

    def _upload_triple(self, triple: _TripleType) -> bool:
        """Uploads a single triple to the in-memory RDF store.

        Parameters
        ----------
        triple : _TripleType
            The RDF triple to upload.

        Returns
        -------
        bool
            True if the triple was uploaded successfully.
        """
        s, p, o = triple
        self.graph.add((s, p, o))
        return True

    def _upload_data(self, data: str, format: str) -> bool:
        """Uploads RDF data to the in-memory RDF store.

        Parameters
        ----------
        data : str
            The RDF data to upload.
        format : str
            The format of the RDF data (e.g., "turtle", "xml", "json-ld").

        Returns
        -------
        bool
            True if the data was uploaded successfully.
        """
        g = rdflib.Graph()
        g.parse(data=data, format=format)
        self._combined_graph += g
        return True

    def _add_to_graph(self, filename: pathlib.Path):
        """Adds the RDF graph from the file to the combined graph."""
        g = self._graphs.get(filename, None)
        if not g:
            g = rdflib.Graph()
            try:
                g.parse(filename)
            except Exception as e:
                raise ValueError(f"Could not parse file '{filename}'. Error: {e}")
            for s, p, o in g:
                if isinstance(s, rdflib.BNode):
                    new_s = rdflib.URIRef(f"https://example.org/{s}")
                else:
                    new_s = s
                if isinstance(o, rdflib.BNode):
                    new_o = rdflib.URIRef(f"https://example.org/{o}")
                else:
                    new_o = o
                g.remove((s, p, o))
                g.add((new_s, p, new_o))
            self._graphs[filename] = g
            self._combined_graph += g

    @property
    def graph(self) -> rdflib.Graph:
        return self._combined_graph

    def reset(self, *args, **kwargs):
        self._filenames = []
        self._graphs = rdflib.Graph()
        self._combined_graph = rdflib.Graph()
        return self

    def save(self, filename: Union[str, pathlib.Path]):
        """Saves the combined graph to a file.

        Parameters
        ----------
        filename : Union[str, pathlib.Path]
            The path to the file where the graph will be saved.
        """
        filename = pathlib.Path(filename).resolve().absolute()
        filename_suffix = filename.suffix.lower()
        if filename_suffix == ".ttl":
            _format = "turtle"
        elif filename_suffix == ".rdf" or filename_suffix == ".xml":
            _format = "xml"
        elif filename_suffix == ".jsonld":
            _format = "json-ld"
        elif filename_suffix == ".nt":
            _format = "nt"
        else:
            raise ValueError(
                f"File format '{filename_suffix}' not supported for saving."
            )
        self.graph.serialize(destination=str(filename), format=_format)
