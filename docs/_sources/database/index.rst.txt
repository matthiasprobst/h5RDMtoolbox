HDF5-Database
=============

Introduction into h5database.

Three concepts are provided in the scope of this sub-package:

- ``H5repo``: Using external HDF5 links. A HDF5 file serves as a "table of content" to link to files within a classic file system
- ``H5Files``: Allows to open multiple files at the same time and brwose through them
- ``h5mongo``: Using pymongo (mongodb) to mirrow meta data of hdf files

.. toctree::
    :titlesonly:
    :glob:

    Serverless.ipynb
    h5mongo.ipynb