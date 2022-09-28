HDF5-Conventions
================

In order to interpret data it must come with auxiliary data, so-called metadata. A definition of
it is regulated in conventions. In the context of this repository, we distinguish naming conventions and
layout definitions. While naming conventions like e.g. the CF Metadata Convention (http://cfconventions.org/)
define the dataset attributes and allowed syntax, to describe a comprehensive description of a dataset, layouts
define the expected structure of an HDF5 file. The latter is needed because HDF5 files allow an hierarchical
organization (groups, subgroups, ...). In sum, both concepts guide and control the user
during data creation but also during exploring and comparison.

Standardized Names
------------------
Some scientific domain have standardized names for
physical properties. To fulfill interoperability, findability as well as re-usability
each dataset **must** be assigned with either the attribute `long_name` or `standard_name`. This
choice is adopted from the CF Metadata Conventions , which is also used in the `xarray` package.

long_name
    A human-readable string.
standard_name
    A string respecting more or less strict rules defined by a community and defined in a name table.

Note, that the `long_name` attribute does not guarentee interoperability but `standard_name` does, if
the convention is known to each user.
In addition to this, an additional attribute is required, namely `units`. As we work with scientific
data, each dataset has a physical unit, e.g. [m]. If no physical unit can be set, it might because the
vairable is dimensionless, which is an information about the unit anyhowe, so we set `units=''`.

If the `standard_name` is provided in the dataset creation method and a standard name table (snt) is
available, then `units` is verified by that table. The table holds the base-units (canoncical units) for
each standard name (check is performed on basic SI-units).

Standardized Name Table
-----------------------
A standardized name table (snt) again is motivated by the CF Metadata Convention. It is a table
containing at least name, description and canonical_units. A python class is provided to read
a table from and write to a YML or XML file. Such an object
is passed to a wrapper-HDF-class to control the above described metadata of datasets.



.. toctree::
    :titlesonly:
    :glob:

    conventions
    layouts

