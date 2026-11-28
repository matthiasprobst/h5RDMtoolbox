.. _ld_cli:

Command Line Serialization
==========================

Use ``h5tbx ld dump`` to serialize HDF5 linked data directly from the shell:

.. code-block:: bash

   h5tbx ld dump example.h5
   h5tbx ld dump example.h5 --format json-ld --file-uri https://example.org/data/ --prefix ex
   h5tbx ld dump example.h5 --structural=false
   h5tbx ld dump example.h5 --contextual=false

By default, structural and contextual RDF are both included. Use
``--structural=false`` or ``--contextual=false`` to restrict the output. The
``--file-uri`` option defines stable subject IRIs; ``--prefix`` binds a compact
prefix for that URI in serializations that support prefixes.

The command uses the same structural/contextual RDF model as the Python
functions :func:`h5rdmtoolbox.ld.get_ld`, :func:`h5rdmtoolbox.ld.hdf2ttl`, and
:func:`h5rdmtoolbox.ld.hdf2jsonld`.
