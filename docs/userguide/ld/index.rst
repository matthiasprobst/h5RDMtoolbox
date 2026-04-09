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


.. toctree::
    :titlesonly:
    :glob:
    :hidden:

    getting_started.ipynb
    shacl_validation.ipynb
