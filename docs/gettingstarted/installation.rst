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

   # install server and test dependencies, including HTTPX for TestClient
   python -m pip install "h5RDMtoolbox[test-server]"

The documentation extra currently requires Python 3.10 or newer because it uses
Sphinx 8. The base package continues to support Python 3.9.

For server development, the ``test-server`` extra provides both the optional
server and its test dependencies. Set ``H5RDMTOOLBOX_REQUIRE_SERVER_TESTS=1``
when checking that feature; missing dependencies then fail instead of skipping
the server test module. See the repository testing guide for the JUnit execution
check used by CI.
