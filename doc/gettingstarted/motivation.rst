Motivation
==========

The world generates more and more data. Without sustainable data management sharing and exploring becomes
difficult and oftentimes impossible. A consequence simulations and experiments have to be redone. A data mangement
that respects the FAIR principles (data must be Findable, Accessible, Interoperable and Re-usable) ensures that
mandatory meta-data is available to interpret the data.

This package assists during data generation, conversion and exploration of data stored in HDF5 files. It further
speeds-up and streamlines working with HDF5 datasets by offering usefull features and general and domain-specific
methods, which in the end reduce required code lines. By associating HDF5 files with meta-conventions like standard
names for datasets or layout definitions it is ensured that conventions are met already during data generation.
Consequently, data can be shared more easily and requires less iterations until the file content is complete.


Why HDF5?
---------

HDF5 is chosn as the file format around everything is built because...

 - it allows to store heterogeneous data
 - the access is fast and efficient
 - allows to store metadata (through attributes)
 - has a comprehensive file-system-like structure
 - has a large communitye