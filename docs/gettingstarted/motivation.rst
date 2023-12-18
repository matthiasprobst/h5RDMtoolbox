Motivation
==========

Academia and industry generate more and more data. However, without sustainable data management, sharing and exploring becomes
difficult and oftentimes impossible. Then, data may become valueless or only usable for few users. Especially in the
automatic analysis by machines becomes impossible. In any case, a lot of effort needs to be spent to enrich the data
with meta-information and to make it usable again or, even worse, the data is lost and needs to be re-generated, which
costs time and money.

The FAIR principles (Findable, Accessible, Interoperable and Re-usable) are a set of principles that guide users towards
good practices to make data more reusable. The principles are described in detail `here <https://www.go-fair.org/fair-principles/>`_.

This python package is designed as a toolbox, which assists users and even projects, communities or collaborations
during data generation, processing and exploration. The package is based on the scientific file format
HDF5.

Why HDF5?
---------
The file format is chosen because it is a widely used, open and well-documented format, which allows data
to be stored in a self-describing way by using so-called attributes in addition to the data itself. HDF5 thus
will be very suitable for the majority of scientific data.

In short:

- It allows storing heterogeneous data,
- the access is fast and efficient,
- allows storing metadata together with raw data (self-descriptiveness),
- has a comprehensive file-system-like structure,
- has a large community.

More information on HDF5 can be found `on the HDF Group website <https://www.hdfgroup.org/solutions/hdf5/>`_.


Working HDF5
------------

The toolbox interfaces is based on the `h5py <https://www.h5py.org/>`_ package, which is a pythonic interface to the
HDF5 binary data format. However, it returns `numpy <https://numpy.org/>`_ arrays, which are not self-descriptive (just
data arrays). While efficient to work with, original information from the HDF5 file is lost. The h5rdmtoolbox therefore
provides a wrapper around h5py, which returns a `xarray <http://xarray.pydata.org/en/stable/>`_ object instead of a
numpy array. This object is self-descriptive and allows attaching meta information to the data - just like HDF5 datasets.

Using HDF5 in combination with xarray allows keeping track of the meta information also during data processing, as
both, the file and the data object, allow attaching attributes to the data. This reduces processing errors, enhances
interpretability and finally makes it easier to share.

This is the very basic feature of the toolbox which already enriches your daily work with HDF5 files. However, there
are many more aspects implemented in the toolbox, which assist you in making your data FAIRer. Find out more in the
following sections.
