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
HDF5. The file format is chosen because it is a widely used, open and well-documented format, which allows data
to be stored in a self-describing way by using so-called attributes in addition to the data itself. HDF5 thus
will be very suitable for the majority of scientific data.

Why HDF5?
---------

HDF5 is selected as the file format around everything is built because...

- it allows to store heterogeneous data
- the access is fast and efficient
- allows to store metadata together with raw data (self-descriptiveness)
- has a comprehensive file-system-like structure
- has a large community.

Using HDF5 in combination with xarray allows keeping track of the meta information also during data processing, as
both, the file and the data object, allow attaching attributes to the data. This reduces processing errors, enhances
interpretability and finally makes it easier to share.

More information on HDF5 can be found `here <https://www.hdfgroup.org/solutions/hdf5/>`_.