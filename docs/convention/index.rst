.. _conventions:

Conventions
===========


Background/Motivation
---------------------
It is good scientific practice to provide rich metadata with raw data. In HDF5 files, this means,
that each group or dataset should have a reasonable amount of meaningful attributes.
This will allow other users and software to reuse the file. Especially, for automatically processing
of the file by software, it is important, that the attributes are given in a standardized way.
This means, that they are free from typos or personal preferences. Example: The unit of a dataset
shall be specified by the attribute name "units", not "unit" or "Einheit".



What is a convention?
---------------------
A ``Convention`` is a class which holds a set of rules for attributes. By activating a convention, the attributes defined
in it, will become parameters of the methods they are assigned to, which are ``create_dataset`` and ``create_group``. We
call those attributes ``standard attributes``.

The ``standard attributes`` may be optional or mandatory and will be checked accordingly during the
call of their respective methods. Furthermore, the attribute values are checked according to their validators, which
were set during the definition of the convention.

Note, that conventions can be shared, as they are defined via YAML or JSON files. It is recommended, to publish them
on data repositories, such as Zenodo. This will allow other users to reuse them and they obtain a unique identifier.

The following sections will provide detailed examples on how to use and construct conventions.


.. toctree::
    :maxdepth: 2
    :hidden:

    standard_attributes_and_conventions.ipynb
    ontologies.ipynb
    Examples <examples/index>