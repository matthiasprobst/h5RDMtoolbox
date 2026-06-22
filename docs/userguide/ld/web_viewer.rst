.. _ld_web_viewer:

Local Web Viewer
================

Start the linked-data web viewer with ``h5tbx serve``:

.. code-block:: bash

   h5tbx serve example.h5
   h5tbx serve data/ --h5ext=.h5 --h5ext=.hdf5
   h5tbx serve example.h5 --file-uri https://doi.org/10.5281/zenodo.17572275# --local-iri-pattern "https://doi.org/10.5281/zenodo.*"

If no filename is provided, ``h5tbx serve`` lists matching files in the current
directory. Each file page links to RDF serializations, an interactive graph,
SPARQL queries, graph metrics, and SHACL validation.

Graph View
----------

The graph page can be shown as a 2D or 3D graph. Nodes are draggable and can be
expanded, hidden, and restored. Literal values are shown in popovers.

Use the graph controls to tune the visualization:

- Color nodes by RDF class or namespace.
- Select a light or strong color scheme.
- Change node size and edge width.
- Set the graph background color.
- Limit large graphs with detail presets, node and edge limits, and search.

The same controls are available for the combined graph. The combined graph
contains all served files and enrichment graphs loaded while browsing.

RDF Responses
-------------

HDF5 object URLs such as ``/example.h5/group/dataset`` are dereferenceable RDF
resources. Browsers get an HTML representation by default; clients can request
RDF with ``Accept: text/turtle`` or ``Accept: application/ld+json``. The
``format`` query parameter overrides content negotiation, for example
``?format=ttl``, ``?format=jsonld``, ``?format=nt``, ``?format=xml``, or
``?format=html``.
