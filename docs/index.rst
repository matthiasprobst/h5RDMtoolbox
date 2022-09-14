.. image:: icons/icon4_header.svg
  :width: 500
  :alt: Alternative text



Overview
========

The HDF5 Research Data Management Toolbox (h5RDMtoolbox) supports the data creation, processing and sharing
of data using the HDF5 file format while fulfilling the `FAIR priciples <https://www.nature.com/articles/sdata201618>`_.


.. note::

   This project is under current development!


The packges comes with four sub-packages:
  - :doc:`conventions/index`: Naming standards mostly for attributes in the HDF5 files
  - :doc:`h5wrapper/index`: Interacting/working with HDF5 files including many useful features and user-defined methods including static and dynamic layout definition
  - :doc:`x2hdf/index`: package facilitating conversion processes to meet the layout requirements defined in `h5wrapperpy`
  - :doc:`h5database/index`: Practical and easy searching in multiple HDF5 files

.. image:: icons/icon4_subpackages.svg
  :width: 300
  :alt: Alternative text
  :align: center

Installation
------------
The repository requires python 3.8. or higher.

Install from source from github:

.. code:: sh

   pip install https://github.com/matthiasprobst/h5RDMtoolbox

Clone and install from source:

.. code:: sh

   git clone https://github.com/matthiasprobst/h5RDMtoolbox
   pip install h5RDMtoolbox/

You may install optional dependencies to be put in square brackets, e.g. the following, that enables working with the mongoDB:

.. code:: sh

   python3.8 -m pip install "h5RDMtoolbox[mongodb]"
   
Other optional dependency keywords are `tec`, `b16`, `piv`, `cfd`, `cf`, `test`, `docs` or `complete` to install everything.




.. toctree::
   :maxdepth: 3
   :hidden:
   :caption: Documentation

    Getting Started <gettingstarted/index>
    Conventions <conventions/index>
    H5wrapper <h5wrapper/index>
    H5Database <h5database/index>
    x2hdf <x2hdf/index>
    HowTo <howto/howto.ipynb>
    Glossary <glossary/index>
    References <references>

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Repository

   GitHub Repository <https://github.com/matthiasprobst/h5RDMtoolbox>

