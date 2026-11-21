.. _catalog:

Catalog
=======

Install the ``catalog`` extra to use local
RDF stores, SPARQL discovery, and HDF5 file stores.

Register stores explicitly using ``CatalogManager.add_main_rdf_store`` and
``CatalogManager.add_hdf_store``. Use ``InMemoryRDFStore`` for local RDF metadata
and ``HDF5FileStore`` for file registration and access. Query metadata with
``SparqlQuery`` or a remote endpoint with ``RemoteSparqlQuery``.
The SQL catalog adapter is removed in 3.0; no default data store is created.
See :doc:`../../migration-3` for migration guidance.

Validation is explicit. ``CatalogManager.validate_catalog(path)`` returns the
shared SHACL ``ValidationResult`` with ``conforms``, report graph, report text,
and structured violations. Registering shapes on a store does not automatically
validate uploads: pass ``validate=True`` when calling ``upload_file`` to request
validation before insertion. Catalog initialization does not validate implicitly.
