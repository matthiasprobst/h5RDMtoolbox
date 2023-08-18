.. _conventions:

Conventions
===========

In order to interpret data it must come with comprehensible auxiliary data (metadata). The usage must be specified and
shared with all users involved data creation or analysis. Thus, rules on how meta data is used needs to
be specified.

The toolbox introduces the classes "StandardAttribute" and "Layout" to standardize important HDF5 attributes and to define the tree-structure of the file for post-validation. Such specification is called "convention" if it is shared via a repository like Zenodo, which allows versioning and adding persistent identifiers, respectively.

Standard attributes and the layout are defined in YAML files and are therefore easy to share and read.

.. admonition:: Conventions
    :class: tip

    A convention defines the usage of attributes ("standard attributes") and the way data is laid out in
    the HDF5 file ("layout"). A convention can be defined by a community or a project. Multiple layout
    definitions can be used with one convention (e.g. the case for experimental and numerical data generation
    of the same physical problem).

.. admonition:: Standard Attribute
    :class: tip

    Standard Attributes are HDF5 attributes, which are defined in a convention. They make specific data
    identifiable both by humans and machines. The syntax may be defined or a list of allowable names may be
    provided for certain attributes. Not all attributes must be regulated.

.. admonition:: Layout
    :class: tip

    A layout defines the structure of an HDF5 file, e.g. the expected groups and datasets as well properties like
    the shape, data type or compression of datasets. Attributes can be defined as well. Layout specifications help
    creating HDF5 files consistently within a project or collaboration and make data exchange between
    different users efficiently.

An example for the usage of standard attributes is the CF Metadata Convention (http://cfconventions.org/),
which uses **netCDF4** files (very similar to HDF5).

Whether an HDF5 file created by someone else is compliant with a convention and moreover whether it contains
the expected hierarchy and datasets, can be checked by a layout definition. The syntax to create layouts is kept very
similar to the creation of HDF5 files with the package `h5py`.

The following chapters will explain the usage of conventions (standard attributes and layouts) in more detail.

If you are new here, best is you start with [Introduction to Standard Attributes](standard_attributes.ipynb)


.. toctree::
    :maxdepth: 2
    :hidden:

    standard_attributes.ipynb
    conventions.ipynb
    standard_names.ipynb
    layouts.ipynb
