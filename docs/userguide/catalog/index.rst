.. _catalog:

Catalog
=======

Install the ``catalog`` extra to use local
RDF stores, SPARQL discovery, and HDF5 file stores.

Validation is explicit. ``CatalogManager.validate_catalog(path)`` returns the
shared SHACL ``ValidationResult`` with ``conforms``, report graph, report text,
and structured violations. Registering shapes on a store does not automatically
validate uploads: pass ``validate=True`` when calling ``upload_file`` to request
validation before insertion. Catalog initialization does not validate implicitly.
