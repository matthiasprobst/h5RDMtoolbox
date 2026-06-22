.. _ld_resolver:

IRI Resolver
============

Manual resolver URLs can use ``/resolve?iri=https://doi.org/...%23path`` and do
not require ``--local-iri-pattern``. Resolver pages keep navigation local: URI
objects link back to ``/resolve?iri=...`` instead of sending the browser to the
external page.

The resolver merges served graph data with known ontology TTL sources, Zenodo
RDF attachments, generic ontology documents, and Wikidata direct claims where
applicable. Browser requests that cannot be resolved locally return a small
fallback page that opens the original IRI in a new tab; machine-readable RDF
requests still return ``404`` when no triples are found.

The server keeps one shared graph for all served files and loaded enrichment
graphs, so combined SPARQL queries can run across the whole local view quickly.
Use ``--local-iri-pattern`` when graph nodes should show local resolver links
for selected external IRI patterns, for example Zenodo DOI IRIs.

If a fragment identifier (``#...``) is passed in a URL, encode it as ``%23``
because browsers do not send raw fragments to the server.

.. code-block:: bash

   curl -H "Accept: text/turtle" http://localhost:8000/example.h5/observable_property/T1
   curl -H "Accept: application/ld+json" "http://localhost:8000/resolve?iri=https://doi.org/10.5072/zenodo.403669%23observable_property/T1"
   curl -H "Accept: text/turtle" "http://localhost:8000/resolve?iri=https://matthiasprobst.github.io/ssno%23StandardName"
   curl -H "Accept: text/turtle" "http://localhost:8000/resolve?iri=https://qudt.org/vocab/unit/K"
   curl -H "Accept: text/turtle" "http://localhost:8000/resolve?iri=https://www.wikidata.org/wiki/Q42"
