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
----------
- The combination of HDF5 and `xarray <https://docs.xarray.dev/en/stable/>`_ facilitates convenient access to
  metadata and data during analysis and processing (`find out more here <https://h5rdmtoolbox.readthedocs.io/en/latest/gettingstarted/quickoverview.html#datasets-xarray-interface>`_).
- Metadata can be assigned with "globally unique and persistent identifiers" as required by `F1 of the FAIR
  principles <https://www.go-fair.org/fair-principles/f1-meta-data-assigned-globally-unique-persistent-identifiers/>`_.
  This is achieved by introducing RDF syntax to HDF5 and thus avoids "ambiguity in the meaning of your published data...".
- The definition of standard attributes through so-called
  `conventions <https://h5rdmtoolbox.readthedocs.io/en/latest/userguide/convention/index.html>`_ enforces users
  to use specific attributes, which get validated and are essential for the interpretation of the data.
- HDF5 files can be uploaded directly to `repositories <https://h5rdmtoolbox.readthedocs.io/en/latest/userguide/repository/index.html>`_
  like `Zenodo <https://zenodo.org/>`_.
- A database interface allows querying for information in the file or moving metadata to `noSQL databases <https://h5rdmtoolbox.readthedocs.io/en/latest/userguide/database/index.html>`_ like
  `mongoDB <https://www.mongodb.com/>`_ for dedicated and more complex search queries.


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

