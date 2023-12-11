.. _conventions:

Conventions
===========

It is good scientific practice to provide rich metadata with raw data. In HDF5 files, this means, that each group or dataset should have a reasonable amount of meaningful attributes. This will allow other users and software to reuse the file. Especially, for automatical processing of the file by software, it is important, that the attributes are given in a standardized way. This means, that they are free from typos or personal preferences. Example: The unit of a dataset shall be specified by the attribute name "units", not "unit" or "Einheit".

To assure reliable metadata, the `h5rdmtoolbox` introduces the concept of so-called **standard attributes**. A list of standard attributes is called a `convention` and is intended to be shared with all users. The convention defines which attributes a HDF5 group or dataset must have and it also checks its value. Additionally, it is possible to define a **layout**, which allows checking for a certain file layout (existing of groups, datasets and attributes) and is typically applied before a HDF5 file is shared with collaborators or a database. 

In order to interpret data, it must come with comprehensible auxiliary data (metadata). The usage must be specified and
shared with all users involved data creation or analysis. Thus, rules on how metadata is used needs to
be specified.

All above documents should be shared via online repositories. Currently, the toolbox favors `Zenodo <https://zenodo.org>`_.

The following chapters will explain the usage of conventions (standard attributes and layouts) in more detail.


.. toctree::
    :maxdepth: 2
    :hidden:

    ontologies.ipynb
    standard_attributes_and_conventions.ipynb
    layouts.ipynb
    Examples <examples/index>