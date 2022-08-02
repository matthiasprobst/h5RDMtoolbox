
Glossary
========


.. glossary::

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