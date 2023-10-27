# CHANGELOG

Log of changes in the versions

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