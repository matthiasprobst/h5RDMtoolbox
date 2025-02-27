Getting Started
===============

Obtain a concise overview of the `h5rdmtoolbox` and its functionalities.


The "HDF5 Research Data Management Toolbox" (`h5rdmtoolbox`) is a python package supporting everyone who is working
with HDF5 to achieve a sustainable data lifecycle which follows the
`FAIR <https://www.nature.com/articles/sdata201618>`_ (Findable, Accessible, Interoperable, Reusable) principles.
It specifically supports the five main steps of

 1. Planning (defining a domain- or problem-specific metadata convention and an layout defining the internal structure of HDF5 files)
 2. Collecting data (creating HDF5 files from scratch or converting to HDF5 files from other sources)
 3. :doc:`Analyzing and processing data <../userguide/wrapper/index>` (Plotting, processing data while keeping the HDF5 attributes by using
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
The toolbox implements six modules corresponding to main features, which are needed to achieve a
sustainable data lifecycle. The module layout is shown below. The numbers reference to their main usage in the stages in
the data lifecycle above. The wrapper module implements the main interface between the user and the HDF5 file. It
extends the features of the underlying `h5py` library. Some of the features are implemented in other modules, hence the
wrapper module depends on the convention, database and linked data (ld) module.


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

