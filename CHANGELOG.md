# CHANGELOG

Log of changes in the versions

## v1.3.0

- important changes:
  - improved and consequent support of RDF/JSON-LD. This means, an HDF5 can be created from a JSON-LD file and vice versa. The JSON-LD file
    contains the structural and contextual metadata of the HDF5 file.
  - namespaces are outsourced to `ontolutils`
- minor changes:
  - When a file is opened with a filename which does not exist and mode is None, the file will NOT be created. This was
    the case in the past, but this may lead to unwanted empty files.
  - Bugfix namespace creation

## v1.2.2

- Hotfix dumping json-ld data (dimension scales were the issue)

## v1.2.1

- Add codemeta namespace
- Improved json-ld export
- Updated qudt namespace
- colab notebook will be managed on a separate branch. the readme link points to the branch

## v1.2.0

- Improved assignment of IRI to attributes
- Export of a JSON-LD file possible
- Updated documentation
- bugfixes

## v1.1.1

- bugfix: Setting a default value for toolbox validators in convention yaml file was not working. Fixed it.

## v1.1.0

- simplified and clean up much code, especially convention sub package
- added identifier utils
- updated and improved documentation

## v1.0.1

- fixed unnecessary call in `create_dataset`, which writes the data twice. Now, the time data is written is comparable
  to the time `h5py` needs to write the data (for small datasets `h5py` is still faster due to the (constant)
  overhead, `h5tbx` adds).

## v1.0.0

major changes:

- zenodo is not a dependency anymore but is implemented as a new subpackage of the toolbox
- zenodo is part or `repository` which is designed to provide interfaces to different data repositories (however,
  only `zenodo` is implemented at the moment)
- the database architecture is changed similarly, such that it has a more logic structure
- both above changes follow a more or less strict inheritance structure from abstract classes defining the interface to
  repositories or databases (databases are meant to be local, like mongoDB, SQL, etc., repositories are online data
  storage, like zenodo, which allows searching for metadata but not within the raw files.)
- python 3.8 until 3.12 inclusive are supported
- IRI as persistent identifier is now supported, which fulfills the F3 requirement of the FAIR principles ("Metadata
  clearly and explicitly include the identifier of the data they describe", https://www.go-fair.org/fair-principles/)
- package renaming and reorganization: `conventions` is now `convention`, `layout` is now a module, new is `repository`
- usage of IRI (persistent identifier) is now supported

## v0.13.0

- scale and offset is now implemented in the package is should not longer be defined in a convention.
- bugfix normalization extension
- bugfix exporting xr.DataArray built with the toolbox to netCDF
- support usage of IRI to describe metadata

## v0.12.2

- bugfix requirements
- add `$exist` `find()`-methods inside of HDF files
- bugfix 0D time data as dimension
- module query functions (`find`, ...) can guess the filename from objects that have
  with `hasattr(hdf_filename, 'hdf_filename')`

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