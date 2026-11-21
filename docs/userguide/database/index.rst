Local HDF5 queries
==================

Query one file with ``FileDB``, several files with ``FilesDB``, or an open
object with ``ObjDB``. Results provide lazy access without retaining an open
file. A lazy result from a file opened with ``decode_calibration=True`` retains
that scientific read setting.

For indexing and discovery across collections, use :doc:`../catalog/index`.
The MongoDB adapter has been removed in 3.0.
