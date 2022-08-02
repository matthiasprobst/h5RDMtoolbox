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

Note, that the `long_name` attribute does not guarentee interoperability but `standard_name` does if
the convention is known to each user.
In addition to this an additional attribute is required, namely `units`. As we deal with scientific
data, each dataset may have a physical unit, e.g. [m] or no unit (thus dimensionless).

If `standard_name` is provided in the dataset creation method and a standard name table is
provided, too, then `units` is verified by that table.

Standardized Name Table
-----------------------
A standardized name table again is motivated by the CF Metadata Convention. It is a table
containing at least name, description and canonical_units. A python class is provided to read
a table from and write to an XML file or to fill from a python script. Such an object
may be passed to a wrapper-class to control the above described metadata of datasets.


Special Name Tables
-------------------
This work supports the genreal notation of the CF Metadata Convention. However, the name table
of scientific domain cannot be used for others. As the authors of this repository are mainly working
with fluid simulations and experiments of hydraulic fluid machineries a new name tables for this domain is
suggested and provided until a standard in the community exists. Concretely, a general table for basic flow
properties is written and a specialiced (inherited from the former) PIV table is provided, too. The
convention package is intended to grow in number of tables for specialized domains until the respective community
publishes a widely accepted one.

.. note::

    The computational fluid dynamic (CFD) domain knows a naming standard; the CFD Generl Notation System CGNS. It is
    beyond the scope of this documentation to argue why this is not the first choice of this repository. However, for the
    sake of completeness the user ma choose this convention with the wrapper classes.


.. toctree::
    :titlesonly:
    :glob:

    conventions

