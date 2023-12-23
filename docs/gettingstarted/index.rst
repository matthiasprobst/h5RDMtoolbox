Getting Started
===============

Get a quick insight into the toolbox and an overview about the capabilities.



The "HDF5 Research Data Management Toolbox" (`h5rdmMtoolbox`) is a python package supporting everyone who is working
with HDF5 to achieve a sustainable data lifecycle which follows the
`FAIR <https://www.nature.com/articles/sdata201618>`_ (Findable, Accessible, Interoperable, Reusable) principles.
It specifically supports the five main steps of

 1. Planning (defining a domain- or problem-specific metadata convention and an layout defining the internal structure of HDF5 files)
 2. Collecting data (creating HDF5 files from scratch or converting to HDF5 files from other sources)
 3. :doc:`Analyzing and processing data <wrapper/index>` (Plotting, processing data while keeping the HDF5 attributes by using
    `xarray <https://xarray.pydata.org/>`_)
 4. Sharing data (either into a repository like e.g. `Zenodo <https://zenodo.org>`_ or into a database)
 5. Reusing data (Searching data in databases, local file structures or online repositories
    like `Zenodo <https://zenodo.org>`_).


.. image:: ../_static/new_icon_with_text.svg
  :width: 500
  :alt: Alternative text
  :align: center


Overview
--------
The `h5rdmtoolbox` is organized in five sub-packages corresponding to main features, which are needed to achieve a
sustainable data lifecycle. The sub-packages are:

Besides the wrapper, which uses the convention sub-package, all sub-packages are independent of each other and can be
developed and used separately.


.. image:: ../_static/h5tbx_modules.svg
  :width: 500
  :alt: Alternative text
  :align: center

.. toctree::
    :maxdepth: 2
    :hidden:

    motivation
    installation
    quickoverview.ipynb

