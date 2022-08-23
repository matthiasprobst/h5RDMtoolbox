
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

    Standardized name table
        A XML document, with tablular content, which contains the standard name and (at least) a description and a
        canonical unit for a it. The respective python class `StandardizedNameTable` is linked to an HDF5 file and
        can performe consistensy checks (checks syntax, name and unit).

    standard_name
        A string respecting more or less strict rules defined by a community and defined in a name table.
        Attribute of a dataset. Must be given if **long_name** is not set.

    units
        Attribute of a dataset describing the physical units of the dataset. Dimensionless datasets
        have units=''

    Layout
        A layout defines the structure of an HDF5 file. It may define exact content, e.g. attribute name and value or
        define expected dataset dimensions or shape. Also some limited conditional layout definition is possible, e.g.
        that dataset may be in another group if the expected does not exist. Layout definitions are attached to a wrapper
        HDF file and epeciall assists during data collection as it defines the final content of a file which was prior
        defined by a community or project.

.. [MICHENER2006] Michener, William K., (2006). Meta-information concepts for ecological data management. Ecological informatics. 1(1), p.3-7.
  DOI: https://doi.org/10.1016/j.ecoinf.2005.08.004