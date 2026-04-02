HDF5 Research Data Management Toolbox
=====================================

The "HDF5 Research Data Management Toolbox" (*h5rdmtoolbox*) is a Python package
designed to assist those engaged in the management of HDF5 data,
enabling the implementation of a sustainable data lifecycle, that adheres to the
`FAIR <https://www.nature.com/articles/sdata201618>`_ principles (Findable,
Accessible, Interoperable, Reusable).



.. note::

   This project is under current development and is happy to receive ideas, code contributions as well as
   `bug and issue reports <https://github.com/matthiasprobst/h5RDMtoolbox/issues/new?title=Issue%20on%20page%20%2Findex.html&body=Your%20issue%20content%20here.>`_.
   Thank you!


Highlights
==========

Effortless, FAIR Metadata
--------------------------

HDF5 already supports rich metadata—but using it consistently can be tedious.
h5rdmtoolbox removes that barrier. Add structured metadata with minimal effort,
validate physical units automatically, and integrate metadata seamlessly into your
analysis workflow with xarray. Metadata can be enriched using RDF
(subject–predicate–object) statements and URI-based identifiers, enabling
machine-readable, FAIR descriptions when needed.

*Result: your data becomes more findable and interoperable—without extra complexity.* *(Findable, Interoperable)*

Turn Your HDF5 Files into FAIR Knowledge Graphs
-----------------------------------------------

Every HDF5 file encodes structure—groups, datasets, attributes. h5rdmtoolbox unlocks
that structure as a knowledge graph. Automatically extract RDF, query your data with
SPARQL, export to JSON-LD or Turtle, and validate metadata using SHACL constraints.
What was once static metadata becomes connected, searchable, and reusable across systems.

*Result: your data gains strong interoperability and reusability.* *(Interoperable, Reusable)*

Persistent Identifiers for Unambiguous Reuse
--------------------------------------------

Ambiguity limits reuse—but it doesn't have to. h5rdmtoolbox enables precise,
persistent identification. Assign identifiers (DOI, ORCID, or custom URIs) to datasets,
people, and metadata elements. You can link units to ontologies like QUDT or describe
authors using FOAF—demonstrating how scientific data can be made unambiguous and
machine-interpretable.

*Result: your data is more findable and easier to reuse correctly.* *(Findable, Reusable)*

From Experiment to FAIR Publication
-----------------------------------

When your work is ready to share, h5rdmtoolbox bridges the gap to publication.
Publish directly to repositories like Zenodo, including rich, standardized metadata
extracted from your files. The same metadata that supports your workflow is preserved
and shared, ensuring others can discover, understand, and reuse your data.

*Result: your data remains accessible and reusable over time.* *(Accessible, Reusable)*

Built on FAIR Semantic Web Principles
------------------------------------

Interoperability starts with shared meaning. h5rdmtoolbox is built on semantic web
technologies. Using RDF, SPARQL, and URI-based identifiers, it turns HDF5 metadata
into machine-readable, linkable information, with validation through SHACL to ensure
quality and consistency. It provides a flexible framework to incorporate scientific
conventions such as NeXus, metadata4ing, and standard-name-based approaches—without
enforcing a fixed schema.

*Result: metadata that is interoperable, reusable, and ready to connect across domains.* *(Interoperable, Reusable)*


Why h5rdmtoolbox?
------------------

For scientists working with HDF5 data, h5rdmtoolbox addresses critical challenges:

**Time Savings**
- No more hunting for metadata scattered across spreadsheets and README files
- Automatic validation catches errors before data is published
- Conventions enforce consistency without manual checking

**Reproducibility**
- Every dataset carries its context: units, coordinates, processing history
- Standardized attributes make data understandable years later
- Full provenance tracking from raw data to publication-ready results

**FAIR Compliance**
- Funding agencies increasingly require FAIR data management plans
- h5rdmtoolbox makes FAIR principles practical, not just aspirational
- Community standard support (NeXus, domain-specific conventions)

**Collaboration**
- Shared conventions ensure everyone on a team uses the same metadata standards
- Layout validation catches structure issues before sharing files
- Rich metadata exports enable integration with data catalogs and repositories

**Scientific Domains**
- Native HDF5 support ideal for: imaging, spectroscopy, simulations, experimental data
- Dimension scales and coordinates preserved throughout analysis
- Physical units validated using the pint library


.. grid:: 3

    .. grid-item-card:: Getting started
        :img-top: _static/icon_getting_started.svg
        :link: gettingstarted/index
        :link-type: doc

        Get a quick overview about capabilities of the toolbox.

    .. grid-item-card::  User guide
        :img-top: _static/icon_user_guide.svg
        :link: userguide/index
        :link-type: doc

        In-depth documentation of the *h5rdmtoolbox* features helping
        you achieving FAIR data.

    .. grid-item-card::  API reference
        :img-top: _static/icon_api.svg
        :link: api
        :link-type: doc

        The h5rdmtoolbox API. Getting insight into the code of the h5rdmtoolbox.


.. toctree::
   :maxdepth: 3
   :hidden:
   :caption: Documentation

    Getting Started <gettingstarted/index>
    User Guide <userguide/index>
    Practical Examples <practical_examples/index>
    HowTo <howto/index>
    Glossary <glossary/index>
    API Reference <api>
    References <references>

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Repository

   GitHub Repository <https://github.com/matthiasprobst/h5RDMtoolbox>

