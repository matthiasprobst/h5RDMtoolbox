# CHANGELOG

Log of changes in the versions

## v1.0.0
major changes:
- zenodo is not a dependency anymore but introduces as a new subpackage of the toolbox
- zenodo is part or `repository` which is designed to provide interfaces to different data repositories (however, only `zenodo` is implemented at the moment)
- the database architecture is changed in a similar way, such that it has a more logic structure
- both above changes follow a more or less strict inheritance structure from abstract classes defining the interface to repositories or databases (databases are meant to be local, like mongoDB, sql, etc, repositories are online data storages, like zenodo, which allows to search for metadata but not within the raw files.)
- python 3.8 until 3.12 inclusive are supported
- IRI as persistent identifier is now supported, which fulfills thr F3 requirement of the FAIR principles ("Metadata clearly and explicitly include the identifier of the data they describe", https://www.go-fair.org/fair-principles/)

## v0.13.0
- scale and offset is now implemented in the package is should not longer be defined in a convention.
- bugfix normalization extension
- bugfix exporting xr.DataArray built with the toolbox to netCDF
- support usage of IRI to describe metadata

## v0.12.2

- bugfix requirements
- add `$exist` `find()`-methods inside of HDF files
- bugfix 0D time data as dimension
- module query functions (`find`, ...) can guess the filename from objects that have with `hasattr(hdf_filename, 'hdf_filename')`

## v0.12.1

- bugfix in zenodo search (did Zenodo change their API?)

## v0.12.0

- 0D data is written to MongoDB
- new utils like computing filesize
- update to new zenodo_search package due to change in backend at Zenodo.org
- `find`, `find_one` and `distinct` can be called on HDF files
- small bugfixes

## v0.11.1

- bugfix standard attribute validation
- bugfix in `EngMeta.ipynb`

## v0.11.0

- working with time data is now possible:
    - time data can be created using the high-level method `create_time_dataset`
    - slicing the above "time datasets" will return xarray data
    - See `docs/wrapper/Misc.ipynb`
- fixed issue with user-defined & nested standard attributes

## v0.10.0

- Initial version, published on `pypi`