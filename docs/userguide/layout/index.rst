Layout
======

With "layouts" we can describe the HDF5 file content, including the location of certain
datasets or groups, but also the attributes and properties (`shape`, `dtype`, `compression`, ...).

The way, layouts are designed is based on the HDF5-as-a-database-approach. This means, that we 
collect a list of query statements, which are called on HDF5 files. E.g. we could say, that we 
require an HDF5 file to have a dataset with a specific name. We would write a query accordingly. 
Later, during validation, the query is performed. If such a dataset is found, the layout successfully 
validated the file content.
So, before working with layouts, you might first want to `learn about <https://h5rdmtoolbox.readthedocs.io/en/latest/database/hdfDB.html>`_.



.. toctree::
    :titlesonly:
    :glob:

    getting_started.ipynb
    Examples.ipynb