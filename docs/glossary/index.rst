Glossary
========


.. glossary::

    metadata
        "Information about data" :cite:t:`michener2006meta` o higher level descriptions of data sets. In HDF5
        files, attributes are used to describe data. Standardized attribute names like **long_name** or
        **standard_name** are special meta data descriptors that follow a specific standard and allow
        automated exploration and analysis.

    convention
        Set of "standard attributes" used to describe data. A convention can be enabled, which will
        automatically add the standard attributes as parameters to the methods like e.g. `create_dataset`.

    standard attributes
        Attributes that are used to describe data. Standard attributes are defined by a convention.
        Standard attributes validate the user input, which is done using the `pydantic` package.

    layout
        Layouts define the structure of an HDF5 file. It may define exact content, e.g. attribute name and value or
        define expected dataset dimensions or shape. It cannot specify the array data of datasets.

    repository
        A repository is a storage place for data, usually online, which assigns a unique identifier to the uploaded
        data. An popular example is Zenodo. Typically, a repository can be queried for metadata such as author,
        title, description, type of data, but not for the content of the data (see database).

    database
        A database hosts data and allows querying of the data content. Examples for databases in the context
        of HDF5 is MongoDB. Databases allow complex queries that would be slow or impossible on the raw HDF5 files.


FAIR Principles and h5rdmtoolbox
================================

The `FAIR principles <https://www.go-fair.org/fair-principles/>`_ (Findable, Accessible, Interoperable, Reusable)
provide guidelines for making data more reusable. Below is a mapping of how h5rdmtoolbox features support each principle.

Findable
--------

**F1**: (Meta)data are assigned a globally unique and persistent identifier

*h5rdmtoolbox features:*
  - ORCID integration for author identification
  - DOI assignment via Zenodo upload
  - IRI/URI support for all metadata elements

**F2**: Data are described with rich metadata

*h5rdmtoolbox features:*
  - Standard attributes with conventions
  - xarray integration preserves context
  - Automatic metadata collection during file creation

**F3**: Metadata clearly and explicitly include the identifier of the data they describe

*h5rdmtoolbox features:*
  - Automatic linking of metadata to datasets via RDF triples
  - Subject/predicate/object structure for all attributes

**F4**: (Meta)data are registered or indexed in a searchable resource

*h5rdmtoolbox features:*
  - JSON-LD export for search engine indexing
  - MongoDB integration for metadata search
  - Zenodo upload with rich metadata

Accessible
----------

**A1**: (Meta)data are retrievable by their identifier using a standardized communications protocol

*h5rdmtoolbox features:*
  - Zenodo repository integration
  - FileDB for local file search

**A2**: Metadata are accessible, even when the data are no longer available

*h5rdmtoolbox features:*
  - JSON-LD export captures all semantic information
  - Separate metadata files can be generated independently

Interoperable
-------------

**I1**: (Meta)data use a formal, accessible, shared, and broadly applicable language

*h5rdmtoolbox features:*
  - RDF/JSON-LD for semantic interoperability
  - Standard attribute conventions

**I2**: (Meta)data use vocabularies that follow FAIR principles

*h5rdmtoolbox features:*
  - QUDT unit ontology for physical quantities
  - FOAF ontology for person descriptions
  - M4I (metadata4ing) ontology for experimental metadata
  - Custom ontology integration support

**I3**: (Meta)data include qualified references to other (meta)data

*h5rdmtoolbox features:*
  - RDF triple linking between datasets
  - Provenance tracking with references
  - Cross-file references

Reusable
--------

**R1**: (Meta)data are richly described with a plurality of accurate and relevant attributes

*h5rdmtoolbox features:*
  - Standard attributes with validators
  - Conventions with domain-specific rules
  - Provenance and processing information

**R1.1**: (Meta)data are released with a clear and accessible data usage license

*h5rdmtoolbox features:*
  - License attribute support
  - Zenodo integration handles licensing automatically

**R1.2**: (Meta)data are associated with detailed provenance

*h5rdmtoolbox features:*
  - Processing step tracking
  - RDF provenance ontology support
  - Version history preservation

**R1.3**: (Meta)data meet domain-relevant community standards

*h5rdmtoolbox features:*
  - NeXus format support for beamline data
  - Custom convention creation
  - SHACL validation against domain shapes
