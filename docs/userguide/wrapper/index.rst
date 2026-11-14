Scientific HDF5 I/O
===================

``File``, ``Group`` and ``Dataset`` extend h5py with metadata-aware xarray reads.
Set attributes explicitly; validation is a separate operation.

.. code-block:: python

   import h5rdmtoolbox as h5tbx
   with h5tbx.File("measurement.h5", "w") as h5:
       ds = h5.create_dataset("signal", data=[1., 2.], attrs={"units": "m"})
       scale = h5.create_dataset("scale", data=2., attrs={"units": ""})
       offset = h5.create_dataset("offset", data=3., attrs={"units": "m"})
       ds.attach_data_scale_and_offset(scale, offset)
   with h5tbx.File("measurement.h5", decode_calibration=True) as h5:
       assert h5["signal"][()].values.tolist() == [5., 7.]
       assert h5["signal"].values[()].tolist() == [1., 2.]

Calibration is disabled by default, scoped to each open file, and preserved by
child objects and lazy query handles. Missing references or incompatible units
raise errors during decoded reads. Existing files need no conversion.

Dimension scales become xarray coordinates. Use ``sel`` and ``isel`` for
coordinate/index selection; unit conversion uses the package Pint registry.
For plotting, normalization and vector operations, operate on the returned xarray
objects directly. Notebook HTML display requires the ``notebook`` extra.
