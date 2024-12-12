Database
========

HDF5 can be considered a database itself, as it allows multiple datasets and their metadata (attributes) to be stored in a single file. Most of the time, you want to find records in an HDF5 file based on the attributes. However, the `h5py` package does not provide a function to do this.

The *h5rdmtoolbox* provides interfaces to perform queries on a single or even multiple HDF5 files. Two approaches exist: 
Either a query is performed sequentially on one or multiple files or the file metadata is first written into a dedicated 
database solution. The first solution may be slow for many and/or large files, it is a convenient way 
without the need of third party databases. You can use it through `FileDB` (for querying a single HDF5 file) and `FilesDB` (for 
querying multiple files). Those classes inherit from the abstract class `HDF5DBInterface`.

To make use of the capabilities of dedicated databases (e.g. advanced queries and 
performant execution) implementations need to inherit from `ExtHDF5DBInterface`, which will require two more methods. As shown in the 
class diagram, one such concrete implementation is provided by the toolbox, which uses MongoDB as the dedicated database system.

.. image:: ../../_static/database_class_diagram.svg
  :width: 400
  :alt: database_class_diagram
  :align: center

The following two chapters show how the aforementioned approaches (using HDF5 itself and using monogDB) work:


- ``FileDB``: Allows to query inside a single file.
- ``MongoDB``: Using pymongo (mongodb) to mirror metadata of HDF files into the database to be queried afterward.


.. toctree::
    :titlesonly:
    :glob:

    firstSteps.ipynb
    hdfDB.ipynb
    mongoDB.ipynb