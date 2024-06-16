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
to be stored in a self-describing way by using so-called "HDF attributes" in addition to the data itself. HDF5 thus
is very suitable for the majority of scientific (multidimensional) data source.

In short:

- It allows storing heterogeneous data,
- the access is fast and efficient,
- allows storing metadata together with raw data (self-descriptiveness),
- has a comprehensive file-system-like structure,
- has a large community.

More information on HDF5 can be found `on the HDF Group website <https://www.hdfgroup.org/solutions/hdf5/>`_.


Working HDF5
------------

The toolbox is based on the `h5py <https://www.h5py.org/>`_ package, which provides a pythonic interface to the HDF5
binary data format. The first notable difference for the user is the return object when data is requested from the
file. In contrast to the `h5py` package, which returns `numpy` arrays, the h5rdmtoolbox returns
`xarray.DataArray <https://docs.xarray.dev/en/stable/user-guide/data-structures.html>`_
objects instead. This resembles the original content more closely, as it allows the assignment of attributes and
coordinates (similar to HDF dimension scales).

The combination of HDF5 and xarray allows for the retention of meta-information throughout the data processing cycle.
This reduces the potential occurrence of processing errors, enhances the interpretability of the data, and
ultimately facilitates the sharing of the data.

There are many more aspects implemented in the toolbox, which assist you in making your data FAIRer. Find out more in the
following sections.
