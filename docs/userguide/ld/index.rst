.. _ld:


Linked Data (LD)
================

The linked data module enables RDF (Resource Description Framework) integration with HDF5 files,
bringing semantic web capabilities to your scientific data.

Background
----------

While HDF5 files provide a hierarchical structure for storing data and metadata, they lack
standardized semantics. RDF provides a framework for describing resources with unique identifiers
and relationships, enabling:

- **Global uniqueness**: Persistent identifiers (e.g., ORCID, DOI) for researchers and data
- **Interoperability**: Common vocabularies and ontologies for domain-specific terms
- **Machine-readable metadata**: Enable automated discovery and integration
- **Knowledge graphs**: Build interconnected datasets that can be queried with SPARQL

The h5rdmtoolbox ld module bridges HDF5 and RDF by enabling:

1. **Structural RDF**: Automatically converting HDF5 structure to RDF (groups, datasets, attributes)
2. **Contextual RDF**: Mapping HDF5 attributes to semantic concepts via ontologies
3. **SHACL validation**: Validating HDF5 data against RDF shapes
4. **Serialization**: Exporting to JSON-LD, Turtle, and other RDF formats


Key Concepts
------------

**Structural RDF**
   Automatically generated RDF from HDF5 structure (groups, datasets, datatypes).

**Contextual RDF**
   User-defined mappings from HDF5 attributes to semantic concepts.

**RDF Mappings**
   Define how HDF5 attributes map to RDF predicates and objects.

**SHACL Shapes**
   RDF shapes that HDF5 metadata must conform to.

Command Line and Web Viewer
---------------------------

The ``h5tbx`` command exposes the linked-data tools without writing Python code.
Use ``ld dump`` to serialize a file directly from the shell. See
:doc:`cli` for details.

.. code-block:: bash

   h5tbx ld dump example.h5
   h5tbx ld dump example.h5 --format json-ld --file-uri https://example.org/data/ --prefix ex
   h5tbx ld dump example.h5 --structural=false
   h5tbx ld dump example.h5 --contextual=false

By default, structural and contextual RDF are both included. Use
``--structural=false`` or ``--contextual=false`` to restrict the output. The
``--file-uri`` option defines stable subject IRIs; ``--prefix`` binds a compact
prefix for that URI in serializations that support prefixes.

For interactive inspection, start the local web viewer. See
:doc:`web_viewer` for the available pages and graph controls.

.. code-block:: bash

   h5tbx serve example.h5
   h5tbx serve data/ --h5ext=.h5 --h5ext=.hdf5
   h5tbx serve example.h5 --file-uri https://doi.org/10.5281/zenodo.17572275# --local-iri-pattern "https://doi.org/10.5281/zenodo.*"

``h5tbx serve`` accepts files and folders. Folder inputs are searched for
``.h5``, ``.hdf``, and ``.hdf5`` files by default; repeat ``--h5ext`` to limit
folder discovery to specific extensions.

Graph Metrics from Python
-------------------------

The metrics shown in the web viewer are also available from Python. Use
``h5rdmtoolbox.compute_metrics`` for a filename, or ``File.metrics`` for an
opened file:

.. code-block:: python

   import h5rdmtoolbox as h5tbx

   metrics = h5tbx.compute_metrics("example.h5")

   with h5tbx.File("example.h5") as h5:
       metrics = h5.metrics()

The returned dictionary contains the same RDF knowledge-graph metrics as the web
page, including graph size, predicate and class usage, connectivity, datatype
distribution, label coverage, and external namespace usage.


.. toctree::
    :titlesonly:
    :glob:
    :hidden:

    getting_started.ipynb
    cli
    web_viewer
    resolver
    metrics
    shacl_validation.ipynb
