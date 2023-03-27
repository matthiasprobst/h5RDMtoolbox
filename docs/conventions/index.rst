Conventions
===========

In order to interpret data it must come with auxiliary data, so-called metadata. A definition of
it is regulated in conventions.

In the context of this repository, we distinguish "naming conventions" and
"layout definitions":


.. admonition:: Conventions
    :class: tip

    Naming conventions define the usage and syntax of attributes for datasets and groups.

.. admonition:: Layouts
    :class: tip

    Layout definitions define the structure of an HDF5 file, e.g. the expected groups and datasets and its content.

Naming conventions are used to define and prescribe the syntax of specific attributes, which give a comprehensive
description of a dataset. Such conventions are commonly defined by a community. An example is the CF Metadata
Convention (http://cfconventions.org/), which uses **netCDF4** files (very similar to HDF5).

Whether or not an HDF5 file created by someone else is compliant with a convention and moreover whether it contains
the expected hierarchy and datasets, can be checked by a layout definition. A layout definition essentially is an
HDF5 file itself and is to be defined within a project.

In sum, both concepts guide and control the user (and all collaborators) during data creation but also during exploring
and comparison to ensure all data is available and with the agreed naming standard.

Available Conventions
---------------------
The `h5RDMtoolbox` comes with two conventions, namely the

default-convention
    Basic convention not prescribing any mandatory attributes

and the

CF-like-convention
    Convention based on the CF Metadata Convention, enforcing the usage of `standard_name` and `units`.

Both conventions are outlined in the following sections.


.. toctree::
    :titlesonly:
    :glob:

    default
    cflike
    layouts

