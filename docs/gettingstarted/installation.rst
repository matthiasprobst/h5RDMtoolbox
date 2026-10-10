.. _installation:

Installation
============

The package supports Python 3.9 through 3.13.

.. code:: sh

   pip install h5RDMtoolbox

You may want to install optional dependencies:

.. code:: sh

   # install dependencies to use the database (MongoDB)
   pip install h5RDMtoolbox[database]
   # Note: MongoDB server must be installed separately

   # install dependencies for testing
   pip install h5RDMtoolbox[test]

   # install dependencies needed to build this documentation
   pip install h5RDMtoolbox[docs]

   # install GUI and test extras (including database, CSV, SNT, and catalog)
   pip install h5RDMtoolbox[complete]

   # install the complete extra plus documentation dependencies
   pip install h5RDMtoolbox[complete-with-docs]

   # install dependencies for CSV support
   pip install h5RDMtoolbox[csv]

   # install dependencies for standard name tables
   pip install h5RDMtoolbox[snt]

   # install dependencies for catalog/SPARQL queries
   pip install h5RDMtoolbox[catalog]

   # install dependencies for layout-validation tables
   pip install h5RDMtoolbox[layout_validation]

   # install the web server and viewer
   pip install h5RDMtoolbox[server]
