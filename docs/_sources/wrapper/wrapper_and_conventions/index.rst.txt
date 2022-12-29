.. _wrapper_and_conventions:

|h5wrappericon| Wrapper + Conventions
=====================================

.. |h5wrappericon| image:: ../../icons/icon_h5wrapper.svg
  :width: 30
  :alt:

To meet the sustainable (FAIR) principles of data management, the package supports the usage of conventions.
Conventions can be naming conventions or ontologies.

Such conventions work together with HDF5 wrapper classes - or the other way around: A wrapper class
is associated with a convention. Generally, conventions are rules how to name HDF5 objects,
which attributes are required for datasets and/or
groups and optionally which values they can take leading to fully described data.

One such existing convention is the CF-conventions (cfconventions.org/) introduced and used by the
Climate and Forecast (CF) community.
Here, variables must be associated with the specific attributes, one of which (and the central one) is
the `standard_name`. The `h5rdmtoolbox` has implemented the concept in a similar manner. As at this stage
of deveopment no claim for completeness is given, the convention is called `CF-like`.


.. toctree::
    :maxdepth: 2
    :hidden:

    cflike.ipynb

