.. _installation:

Installation
============

The package requires Python 3.9 or higher (automatic testing is performed for Python 3.9-3.13).

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

   # install all above dependencies
   pip install h5RDMtoolbox[complete]

   # install dependencies for CSV support
   pip install h5RDMtoolbox[csv]

   # install dependencies for standard name tables
   pip install h5RDMtoolbox[snt]

   # install dependencies for catalog/SPARQL queries
   pip install h5RDMtoolbox[catalog]