.. _conventions:

Conventions
===========

High quality data is data that can be understood, so being re-used at any time by both humans and machines. To achieve this, a **metadata convention** must be defined and applied.

The `h5rdmtoolbox` offers the usage of so-called **standard attributes**. A list of standard attributes is called a `convention` and is intended to be shared with all users. The convention defines which attributes a HDF5 group or dataset must have and it also checks its value. Additionally, it is possible to define a **layout**, which allows checking for a certain file layout (existing of groups, datasets and attributes) and is typically applied before a HDF5 file is shared with collaborators or a database. 

In order to interpret data, it must come with comprehensible auxiliary data (metadata). The usage must be specified and
shared with all users involved data creation or analysis. Thus, rules on how metadata is used needs to
be specified.

All above documents should be shared via online repositories. Currently, the toolbox favors [Zenodo](https://zenodo.org).

The following chapters will explain the usage of conventions (standard attributes and layouts) in more detail.


.. toctree::
    :maxdepth: 2
    :hidden:

    standard_attributes_and_conventions.ipynb
    introduction_to_validators.ipynb
    standard_name_convention.ipynb
    standard_name_interface.ipynb
    Provenance.ipynb
    layouts.ipynb
