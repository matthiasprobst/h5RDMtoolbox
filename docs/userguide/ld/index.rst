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
Use ``ld dump`` to serialize a file directly from the shell:

.. code-block:: bash

   h5tbx ld dump example.h5
   h5tbx ld dump example.h5 --format json-ld --file-uri https://example.org/data/ --prefix ex
   h5tbx ld dump example.h5 --structural=false
   h5tbx ld dump example.h5 --contextual=false

By default, structural and contextual RDF are both included. Use
``--structural=false`` or ``--contextual=false`` to restrict the output. The
``--file-uri`` option defines stable subject IRIs; ``--prefix`` binds a compact
prefix for that URI in serializations that support prefixes.

For interactive inspection, start the local web viewer:

.. code-block:: bash

   h5tbx serve example.h5
   h5tbx serve example.h5 --file-uri https://doi.org/10.5281/zenodo.17572275# --local-iri-pattern "https://doi.org/10.5281/zenodo.*"

If no filename is provided, ``h5tbx serve`` lists all ``.h5``, ``.hdf``, and
``.hdf5`` files in the current directory. Each file page links to:

- RDF serializations: Turtle, JSON-LD, N-Triples, and RDF/XML.
- ``Graph``: an interactive RDF graph view with class-based colors, draggable
  nodes, literal popovers, and hide/unhide controls.
- ``Query``: a SPARQL editor with sample queries and tabular SELECT results.
- ``Metrics``: RDF knowledge-graph metrics, including graph size, predicate and
  class usage, connectivity, datatype distribution, label coverage, and external
  namespace usage.
- ``SHACL``: a SHACL validation page where Turtle shapes can be pasted and run
  against the currently loaded RDF graph.

All web views are generated from the currently loaded HDF5 file and support the
same structural/contextual RDF model used by ``ld dump``. HDF5 object URLs such
as ``/example.h5/group/dataset`` are dereferenceable RDF resources. Browsers get
an HTML representation by default; clients can request RDF with ``Accept:
text/turtle`` or ``Accept: application/ld+json``. The ``format`` query parameter
overrides content negotiation, for example ``?format=ttl``, ``?format=jsonld``,
``?format=nt``, ``?format=xml``, or ``?format=html``.

Manual resolver URLs can use ``/resolve?iri=https://doi.org/...%23path`` and do
not require ``--local-iri-pattern``. If the requested IRI is a Zenodo DOI or
Zenodo record URL with a fragment, the server lazily downloads RDF-like files
attached to that Zenodo record into a temporary cache and merges the first
matching subject with the served graph data. Use
``--local-iri-pattern`` only when graph nodes should show local resolver links
for selected external IRI patterns, for example Zenodo DOI IRIs. If a fragment
identifier (``#...``) is passed in a URL, encode it as ``%23`` because browsers
do not send raw fragments to the server.

.. code-block:: bash

   curl -H "Accept: text/turtle" http://localhost:8000/example.h5/observable_property/T1
   curl -H "Accept: application/ld+json" "http://localhost:8000/resolve?iri=https://doi.org/10.5072/zenodo.403669%23observable_property/T1"

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
    shacl_validation.ipynb
