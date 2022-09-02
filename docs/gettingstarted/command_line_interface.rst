Command Line Interfaces
=======================

By installing the package some console calls become available. For all command line interfaces
a help exists. Just pass the argument `-h`:

.. code-block:: bash

    h5tbx -h
    
    
- Open the documentation in the browser:

.. code-block:: bash

    h5tbx -D



- Get the version of the package:

.. code-block:: bash

    h5tbx -V

Layouts
-------

- List all registered layout files

.. code-block:: bash

    h5tbx layout --list
    
    

- Check an HDF5 file (my_file) usign a registered layout (my_layout):

.. code-block:: bash

    h5tbx standard_name -s my_layout -f my_file
    
    

- Check an HDF5 file (my_file) usign a layout file (my_layout.hdf):

.. code-block:: bash

    h5tbx standard_name -s my_layout.hdf -f my_file



Standard name (tables)
----------------------

- List all registered standard name table files

.. code-block:: bash

    h5tbx standard_name --list
    
    

- Check an HDF5 file (my_file) for a registered standard name table (my_table):

.. code-block:: bash

    h5tbx standard_name -s my_table -f my_file
    
    

- Check an HDF5 file (my_file) for a standard name table (my_table.yml):

.. code-block:: bash

    h5tbx standard_name -s my_table.yml -f my_file