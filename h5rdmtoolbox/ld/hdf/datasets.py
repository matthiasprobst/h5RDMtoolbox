from typing import Optional

import h5py
import numpy as np
import rdflib
from ontolutils.namespacelib.hdf5 import HDF5
from rdflib import Namespace
from rdflib import RDFS
from rdflib import XSD, RDF

from h5rdmtoolbox.convention.ontology.hdf_datatypes import get_datatype
from h5rdmtoolbox.ld.hdf.attributes import process_attribute

HDF = Namespace(str(HDF5))
HDF5_FILTER_ONTOLOGY = {
    "gzip": HDF5.FilterDeflate,
    "fletcher32": HDF5.FilterFletcher,
    "shuffle": HDF5.FilterShuffle,
    "scaleoffset": HDF5.FilterScaleOffset,
    "szip": HDF5.FilterSZip,
    "nbit": HDF5.FilterNBit,
}


def add_filter(dataset: h5py.Dataset, dataset_uri, graph) -> rdflib.Graph:
    # Check predefined compression filters
    if dataset.compression:
        filter_type = HDF5_FILTER_ONTOLOGY.get(dataset.compression, None)
        filter_uri = rdflib.BNode()
        if filter_type:
            graph.add((filter_uri, RDF.type, filter_type))
            if filter_type == HDF5.FilterDeflate:
                graph.add(
                    (filter_uri, HDF5.deflateLevel, rdflib.Literal(dataset.compression_opts, datatype=XSD.integer))
                )
        else:
            graph.add((filter_uri, RDF.type, HDF5.Filter))
            graph.add((filter_uri, RDFS.label, rdflib.Literal(dataset.compression, datatype=XSD.integer)))
            graph.add((filter_uri, RDFS.comment,
                       rdflib.Literal("Unknown compression filter. Could not determine class nor parameters.",
                                      datatype=XSD.string)))
        graph.add((dataset_uri, HDF5.filter, filter_uri))
    return graph


def process_dataset(
        dataset,
        graph,
        parent_uri,
        dataset_uri,
        blank_node_iri_base: Optional[str] = None,
        skipND: int = 1
):
    """Process an HDF5 dataset, adding it to the RDF graph."""
    graph.add((dataset_uri, RDF.type, HDF.Dataset))

    graph = add_filter(dataset, dataset_uri, graph)

    graph.add((parent_uri, HDF.member, dataset_uri))

    graph.add((dataset_uri, HDF5.name, rdflib.Literal(dataset.name)))
    graph.add((dataset_uri, HDF5.rank, rdflib.Literal(dataset.ndim, datatype=XSD.integer)))
    graph.add((dataset_uri, HDF5.size, rdflib.Literal(dataset.size, datatype=XSD.integer)))

    if dataset.maxshape:
        if all(dataset.maxshape):
            graph.add(
                (dataset_uri, HDF5.maximumSize, rdflib.Literal(int(np.prod(dataset.maxshape)), datatype=XSD.integer)))
        else:
            graph.add((dataset_uri, HDF5.maximumSize, rdflib.Literal(-1, datatype=XSD.integer)))
    else:
        graph.add((dataset_uri, HDF5.maximumSize, rdflib.Literal(-1, datatype=XSD.integer)))

    datatype = get_datatype(dataset)

    if datatype:
        graph.add((datatype, RDF.type, HDF5.Datatype))
        graph.add((dataset_uri, HDF5.datatype, datatype))

    is_string_dataset = False
    if dataset.dtype.kind == 'S':
        is_string_dataset = True
        graph.add((dataset_uri, HDF5.datatype, rdflib.Literal('H5T_STRING')))
    elif dataset.dtype.kind in ('i', 'u'):
        graph.add((dataset_uri, HDF5.datatype, rdflib.Literal('H5T_INTEGER')))
    else:
        graph.add((dataset_uri, HDF5.datatype, rdflib.Literal('H5T_FLOAT')))

    dataset_layout = dataset.id.get_create_plist().get_layout()
    if dataset.chunks is not None:
        graph.add((dataset_uri, HDF5.layout, HDF5.H5D_CHUNKED))
    elif dataset_layout == h5py.h5d.COMPACT:
        graph.add((dataset_uri, HDF5.layout, HDF5.H5D_COMPACT))
    elif dataset_layout == h5py.h5d.CONTIGUOUS:
        graph.add((dataset_uri, HDF5.layout, HDF5.H5D_CONTIGUOUS))
    elif dataset.is_virtual:
        graph.add((dataset_uri, HDF5.layout, HDF5.H5D_VIRTUAL))

    if dataset.chunks:
        chunk_dimension_uri = rdflib.BNode()
        graph.add((chunk_dimension_uri, RDF.type, HDF5.ChunkDimension))
        graph.add((dataset_uri, HDF5.chunk, chunk_dimension_uri))

        for ichunk, chunk in enumerate(dataset.chunks):
            dimension_index_uri = rdflib.BNode()
            graph.add((dimension_index_uri, RDF.type, HDF5.DataspaceDimension))
            graph.add((chunk_dimension_uri, HDF5.dimension, dimension_index_uri))
            graph.add((dimension_index_uri, HDF5.size, rdflib.Literal(chunk, datatype=XSD.integer)))
            graph.add((dimension_index_uri, HDF5.dimensionIndex, rdflib.Literal(ichunk, datatype=XSD.integer)))

    if dataset.ndim > 0:
        dataspace_uri = rdflib.BNode()
        graph.add((dataspace_uri, RDF.type, HDF5.SimpleDataspace))
        for idim, dim in enumerate(dataset.shape):
            dataspace_dimension_node = rdflib.BNode()
            graph.add((dataspace_dimension_node, RDF.type, HDF5.DataspaceDimension))
            graph.add((dataspace_uri, HDF5.dimension, dataspace_dimension_node))
            graph.add((dataspace_dimension_node, HDF5.size, rdflib.Literal(dim, datatype=XSD.integer)))
            graph.add((dataspace_dimension_node, HDF5.dimensionIndex, rdflib.Literal(idim, datatype=XSD.integer)))

        if skipND and dataset.ndim < skipND:
            data = dataset[()].tolist()
            if is_string_dataset:
                graph.add((dataset_uri, HDF5.value, rdflib.Literal([s.decode() for s in data])))
            else:
                graph.add((dataset_uri, HDF5.value, rdflib.Literal(data)))
    else:
        dataspace_uri = HDF5.scalarDataspace
        graph.add((dataspace_uri, RDF.type, HDF5.scalarDataspace))

        if skipND and dataset.ndim < skipND:
            data = dataset[()]
            if is_string_dataset:
                graph.add((dataset_uri, HDF5.value, rdflib.Literal(data.decode())))
            else:
                graph.add((dataset_uri, HDF5.value, rdflib.Literal(data)))

    graph.add((dataset_uri, HDF5.dataspace, dataspace_uri))

    # Process attributes of the dataset
    for attr, value in dataset.attrs.items():
        process_attribute(attr, value, graph, dataset_uri)
