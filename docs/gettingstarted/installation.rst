.. _installation:

Installation
============

The repository requires python 3.8. or higher (automatic testing is performed until 3.12).

.. code:: sh

   pip install h5RDMtoolbox

You may want to install optional dependencies:

.. code:: sh

   # install dependencies to use the database mongoDB
   pip install h5RDMtoolbox[mongodb]

   # install dependencies for testing
   pip install h5RDMtoolbox[test]

   # install dependencies needed to build this documentation
   pip install h5RDMtoolbox[docs]

   # install all above dependencies
   pip install h5RDMtoolbox[complete]