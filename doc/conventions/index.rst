Conventions
===========

Conventions in the context of this repository guide and control the user during
dataset creation and exploring. Some scientific domain have standardized names for
physical properties. To fulfill interoperability, findability as well as re-usability
each dataset **must** be assigned with the attribute `long_name` or `standard_name`. This
choice is adopted from the CF Metadata Conventions (http://cfconventions.org/), which is
also used in the `xarray` package.

long_name
    A human-readable string.
standard_name
    A string respecting more or less strict rules defined by a community and defined in a name table.

Note, that the `long_name` attribute does not guarentee interoperability but `standard_nam` does if
the convention is known to each user.
In addition to this an additional attribute is required, namely `units`. As we deal with scientific
data, each dataset may have a physial unit, e.g. [m] or no unit (thus dimensionless).

If `standard_name` is provided in the dataset creation method and a standard name table is
provided, too, then `units` is verified by that table.

Standardized Name Table
-----------------------
A standardized name table again is motivated by the CFD Metadata Convention. It is a table
containing at least name, description and canonical_units. A python class is provided to read
a table from and write to an XML file or to fill from a python script. Such an objec
may be passed to a wrapper-class to control the above described meta data of datasets.

.. toctree::
    :titlesonly:
    :glob:

    conventions
