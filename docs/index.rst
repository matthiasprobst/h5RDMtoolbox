HDF5 Research Data Management Toolbox
=====================================

The "HDF5 Research Data Management Toolbox" (*h5rdmtoolbox*) is a python package supporting everyone who is working
with HDF5 to achieve a sustainable data lifecycle which follows the
`FAIR <https://www.nature.com/articles/sdata201618>`_ (Findable, Accessible, Interoperable, Reusable) principles.



.. note::

   This project is under current development and is happy to receive ideas, code contributions as well as
   `bug and issue reports <https://github.com/matthiasprobst/h5RDMtoolbox/issues/new?title=Issue%20on%20page%20%2Findex.html&body=Your%20issue%20content%20here.>`_.
   Thank you!


Highlights
----------
- Combining HDF5 and [xarray](https://docs.xarray.dev/en/stable/) to allow easy access to metadata and data during
  analysis and processing (see [here](https://h5rdmtoolbox.readthedocs.io/en/latest/gettingstarted/quickoverview.html#datasets-xarray-interface).
- Assigning [metadata with "globally unique and persistent identifiers"]() as required by [F1 of the FAIR
  principles](https://www.go-fair.org/fair-principles/f1-meta-data-assigned-globally-unique-persistent-identifiers/).
  This "remove[s] ambiguity in the meaning of your published data...".
- Define standard attributes through
  [conventions](https://h5rdmtoolbox.readthedocs.io/en/latest/userguide/convention/index.html) and enforce users
  to use them
- Upload HDF5 files directly to [repositories](https://h5rdmtoolbox.readthedocs.io/en/latest/userguide/repository/index.html)
  like [Zenodo](https://zenodo.org/) or [use them with noSQL databases](https://h5rdmtoolbox.readthedocs.io/en/latest/userguide/database/index.html) like
  [mongoDB](https://www.mongodb.com/).


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

