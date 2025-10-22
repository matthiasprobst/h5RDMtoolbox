import pathlib
from dataclasses import dataclass
from typing import Union, List

import h5py
import rdflib
from pyshacl import validate as pyshacl_validate

from .hdf.file import get_ld as get_hdf_ld
from .user.file import get_ld as get_contextual_ld


@dataclass
class ValidationResult:
    conforms: bool
    results_graph: rdflib.Graph
    results_text: str
    messages: List[str]
    nodes: List[str]


def _parse_shacl(shacl: Union[str, pathlib.Path, rdflib.Graph], format) -> rdflib.Graph:
    if isinstance(shacl, pathlib.Path):
        if format is None:
            format = rdflib.util.guess_format(str(shacl))
        shacl_graph = rdflib.Graph()
        shacl_graph.parse(str(shacl), format=rdflib.util.guess_format(str(shacl)))
    elif isinstance(shacl, str):
        if format is None:
            format = 'turtle'
        try:
            shacl_graph = rdflib.Graph()
            shacl_graph.parse(shacl, format=format)
        except Exception:
            # it may be a file, not a string graph:
            return _parse_shacl(pathlib.Path(shacl))
    elif isinstance(shacl, rdflib.Graph):
        shacl_graph = shacl
    else:
        raise TypeError('shacl must be a pathlib.Path, str, or rdflib.Graph')
    return shacl_graph


def validate_hdf(
        *,
        hdf_data: Union[str, rdflib.Graph] = None,
        hdf_source: Union[h5py.File, pathlib.Path] = None,
        shacl_data: Union[str, rdflib.Graph] = None,
        shacl_source: Union[str, pathlib.Path] = None,
        hdf_file_uri="https://example.org/hdf5file#",
        shacl_format: str = 'turtle',
        hdf_data_format: str = 'turtle',
        **pyshacl_kwargs
) -> ValidationResult:
    """
    Validate an HDF5 file against SHACL shapes.
    Parameters
    ----------
    hdf_data: Union[str, rdflib.Graph], optional
        The HDF5 data as a string or rdflib.Graph. If is string is provided
        it is assumed to be in Turtle format (you may overwrite this by passing hdf_data_format.
    hdf_source: Union[h5py.File, pathlib.Path], optional
        The path to the HDF5 file.
    shacl_data: Union[str, rdflib.Graph], optional
        The SHACL shapes as a string or rdflib.Graph. If is string is provided
        it is assumed to be in Turtle format.
    shacl_source: Union[str, pathlib.Path], optional
        The path to the SHACL shapes file.
    shacl_format: str, optional
        The format of the SHACL shapes string. Default is 'turtle'.
    hdf_data_format: str, optional
        The format of the HDF5 data string. Default is 'turtle'.
    **pyshacl_kwargs:
        Additional keyword arguments to pass to pyshacl.validate().

    Returns
    -------
    ValidationResult
        The result of the validation containing:
        - conforms: bool
        - results_graph: rdflib.Graph
        - results_text: str
        - messages: List[str]
    """
    if shacl_data is not None and shacl_source is not None:
        raise ValueError('Only one of "shacl_data" or "shacl_source" should be provided.')
    if shacl_data is None and shacl_source is None:
        raise ValueError('One of "shacl_data" or shacl_source must be provided.')

    if hdf_data is not None and hdf_source is not None:
        raise ValueError('Only one of "hdf_data" or "hdf_source" should be provided.')
    if hdf_data is None and hdf_source is None:
        raise ValueError('One of "hdf_data" or "hdf_source" must be provided.')

    if hdf_data is not None:
        if isinstance(hdf_data, str):
            h5_graph = rdflib.Graph()
            h5_graph.parse(hdf_data, format='turtle')
        elif isinstance(hdf_data, rdflib.Graph):
            h5_graph = hdf_data
        else:
            raise TypeError(f'Parameter "hdf_data" must be a str or rdflib.Graph, but is {type(hdf_data)}')
    if hdf_source is not None:
        if isinstance(hdf_source, (str, pathlib.Path)):
            if not pathlib.Path(hdf_source).exists():
                raise FileNotFoundError(f'HDF5 file source "{hdf_source}" not found.')
            with h5py.File(hdf_source, 'r') as h5f:
                return validate_hdf(
                    hdf_data=None,
                    hdf_source=h5f,
                    shacl_data=shacl_data,
                    shacl_source=shacl_source,
                    hdf_file_uri=hdf_file_uri,
                    hdf_data_format=hdf_data_format,
                    **pyshacl_kwargs
                )
        if not isinstance(hdf_source, h5py.File):
            raise TypeError('Parameter "hdf_source" must be an h5py.File or a path to an HDF5 file.')
        h5_graph1 = get_hdf_ld(hdf_source, file_uri=hdf_file_uri, skipND=True)
        h5_graph2 = get_contextual_ld(hdf_source, file_uri=hdf_file_uri)
        h5_graph = h5_graph1 + h5_graph2

    shacl_graph = None
    if shacl_data is not None:
        if isinstance(shacl_data, str):
            shacl_graph = rdflib.Graph()
            shacl_graph.parse(data=shacl_data, format=shacl_format)
        elif isinstance(shacl_data, rdflib.Graph):
            shacl_graph = shacl_data
        else:
            raise TypeError('Parameter "shacl_data" must be a str or rdflib.Graph')
    elif shacl_source is not None:
        # shacl is a filename:
        if not pathlib.Path(shacl_source).exists():
            raise FileNotFoundError(f'SHACL file source "{shacl_source}" not found.')
        shacl_graph = rdflib.Graph()
        shacl_graph.parse(source=shacl_source, format=shacl_format)

    conforms, results_graph, results_text = _validate_graphs(
        h5_graph,
        shacl_graph,
        **pyshacl_kwargs
    )
    return ValidationResult(
        conforms=conforms,
        results_graph=results_graph,
        results_text=results_text,
        messages=_get_messages(results_graph),
        nodes=_get_focus_nodes(results_graph)
    )


def _validate_graphs(
        data_graph,
        shacl_graph,
        inference='rdfs',
        abort_on_first=False,
        meta_shacl=False,
        advanced=False,
        debug=False):
    """
    Validate a data graph against a SHACL shapes graph.

    Parameters:
    - data_graph: The RDF graph containing the data to be validated.
    - shacl_graph: The RDF graph containing the SHACL shapes.
    - inference: Type of inference to apply ('rdfs', 'owl', or None).
    - abort_on_first: If True, stop validation on the first error found.
    - meta_shacl: If True, enable Meta-SHACL features.
    - advanced: If True, enable advanced SHACL features.
    - debug: If True, enable debug output.

    Returns:
    - A tuple (conforms, results_graph, results_text) where:
      - conforms: Boolean indicating if the data graph conforms to the shapes.
      - results_graph: An RDF graph with validation results.
      - results_text: A textual summary of the validation results.
    """

    conforms, results_graph, results_text = pyshacl_validate(
        data_graph,
        shacl_graph=shacl_graph,
        inference=inference,
        abort_on_first=abort_on_first,
        meta_shacl=meta_shacl,
        advanced=advanced,
        debug=debug
    )

    return conforms, results_graph, results_text


def _get_messages(results_graph):
    """
    Extract validation messages from a SHACL results graph.

    Parameters:
    - results_graph: An RDF graph containing SHACL validation results.

    Returns:
    - A list of validation messages.
    """
    messages = []
    for s, p, o in results_graph.triples((None, rdflib.namespace.SH.resultMessage, None)):
        messages.append(str(o))
    return messages

def _get_focus_nodes(results_graph):
    """
    Extract focus nodes from a SHACL results graph.

    Parameters:
    - results_graph: An RDF graph containing SHACL validation results.

    Returns:
    - A list of focus nodes.
    """
    focus_nodes = []
    for s, p, o in results_graph.triples((None, rdflib.namespace.SH.focusNode, None)):
        focus_nodes.append(o)
    return focus_nodes
