
Glossary
========


.. glossary::

    metadata
        "Information about data" ([MICHENER2006]_) o higher level descriptions of data sets. In HDF5
        files, attributes are used to describe data. Standardized attribute names like **long_name** or
        **standard_name** are special meta data describtors that follow a specific standard and allow
        automated exploration and analysis.

    long_name
        A human-readable string. Attribute of a dataset. Must be given if **standard_name** is not set.

    standard_name
        A string respecting more or less strict rules defined by a community and defined in a name table.
        Attribute of a dataset. Must be given if **long_name** is not set.

    units
        Attribute of a dataset describing the physical units of the dataset. Dimensionless datasets
        have units=''

    standardized name table
        Also **standard name table**, a table which holds all names, descriptions and units of a onvention.
        A wrapper-class uses it when **standard_name** and **units** are provided during dataset creation
        and when the content of a file is checked.

.. [MICHENER2006] Michener, William K., (2006). Meta-information concepts for ecological data management. Ecological informatics. 1(1), p.3-7.
  DOI: https://doi.org/10.1016/j.ecoinf.2005.08.004
