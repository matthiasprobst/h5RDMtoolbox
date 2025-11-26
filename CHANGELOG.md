# CHANGELOG

Log of changes in the versions

## v2.5.3

- fix handling multiple RDF type metadata at file level
- support deleting RDF file object

## v2.5.2

- fix passing json-ld as RDF object
- support for blank nodes in contextual semantic metadata
- fix serializing version strings in RDF data
- removing deprecated piv:timeFormat for time datasets
- upgrade to ontolutils 0.22.1

## v2.5.1

- hotfix Organization class

## v2.5.0

- Zenodo Record returns a "dcat:Dataset" object when `publish()` is called.
- Zenodo Record provides `as_dcat_dataset()` method to obtain the "dcat:Dataset" object for a published record.
- Shacl result object `ValidationResult` also provides nodes that caused the validation error
- bugfix HDF serialization for HDF5 datatypes, which were literals and now are URIs

## v2.4.0

- checksum is correctly checked when downloading files
- added support for SHACL through function `shacl_validate`

## v2.4.0-rc.2

- fix issues with ZenodoRecord
- add support of Literals in RDF attributes, e.g. h5.frdf["description"].object = rdflib.Literal("An english
  description", "en")
- removed deprecated methods in `ZenodoSandboxDeposit`
- add support of Literals in RDF attributes, e.g.
  `h5.frdf["description"].object = rdflib.Literal("An english description", "en")`
- improve serializing HDF5 contextual and structural metadata to RDF-based formats
- minor bugfixes
- default dtime format used within h5rdmtoolbox is now ISO 8601 ('%Y-%m-%dT%H:%M:%S%f')

## v2.4.0-rc.1

- allow numpy 2.x versions
- extend support for python 3.13
- upgrade pint to 0.25
- upgrade pint-xarray up to 0.6.0
- upgrading to ontolutils 0.21.1
- fixing linting issues
- RDF-subjects set for dataset and group are modelled with property schema:about to express that a dataset or group is
  described by the RDF subject. This is more in line with semantic web standards.

## v2.3.1

- fixing error in parsing obj name. "/" is saved and will not be converted anymore

## v2.3.0

- hotfix avoiding blank nodes for hdf filter
- RDF IRIs are encoded correctly, when using special characters or spaces. The issue was that if HDF names (dataset,
  group, attribute names) contained special characters or spaces, the generated RDF IRI was not encoded correctly. Now,
  the HDF names are URL-encoded when generating the RDF IRI.
- removed deprecated methods `download_file` and `download_files` from `RepositoryInterface`. The `files`
  property accessor should be used instead.
- bug-fixing

## v2.2.1

- hotfix dependency to ontolutils 0.19.2

## v2.2.0

- use fragments in internal HDF5 URIs to align with semantic web standards (fragments are not resolved in the web
  interface, but are used to identify the HDF5 object in the file)
- housekeeping

## v2.1.0

- upgrade setuptools due to cve and therefore limit minimum python version to 3.9

## v2.0.0

- changed version number to 2.0.0
- housekeeping

## v2.0.0a0

- Major change: Removed code for standard names as it is outsourced to the `ssnolib` package
- fix and upgrade feature `Convention` so that user-defined validators work as expected

## v1.7.4

- limit xarray version to <=2025.3.0
- bugfix reading/displaying binary data
- file can be associates with an ID (h5.frdf.subject = <ID>)

## v1.7.3

- hotfix serialization when multiple rdf:type values are set
- move `jsonld` sub-module from `wrapper` to `ld` module
- hotfix when instantiating File with `fileobj`, which is the case when working with hdf5 through streamlit, for
  instance

## v1.7.2

- remove `skipND` from being deprecated
- separation of "linked data" code into a separate repo
- update documentation

## v1.7.1

- fix documentation at readthedocs

## v1.7.0

- chunks=None as default for `create_dataset` to mimic behavior of `h5py`
- improved formalized representation of the HDF5 file structure based on the Allotrope Foundation's ontology
- removed unclear parameter `resolve_keys` from `dump_jsonld()` and `serialize()`
- HDF.File is not automatically returned if `h5.frdf.type` is called
- update to `ontolutils` v0.13.3
- improve semantic structural description of HDF5 file content

## v1.6.2

- hotfix `rdf_find`
- using `ontolutils` v0.13.2 and its HDF5 namespace definition
- update/improve CLI interface

## v1.6.1

- hotfix `skipND` when calling `dump_jsonld()`. Option was not passed correctly to underlying function.

## v1.6.0

- `rootgroup` as alias for `rootparent`
- `ZenodoRecord` has new property `env_name_for_token` to define the environment variable name to be used for the Zenodo
  token
- bugfix downloading zenodo files
- allowing higher versions of `pymongo`

## v1.5.2

- bugfix dumping json-ld

## v1.5.1

- a json-ld string can be assigned to a rdf object (
  see https://h5rdmtoolbox.readthedocs.io/en/latest/userguide/wrapper/FAIRAttributes.html)

## v1.5.0

- make compliant with higher `pydantic` and `ontolutils` versions
- concrete version selection for other dependencies

## v1.4.1

- Downloading files will be cached by their checksum and/or URL. This avoids multiple downloads of the same file.
- `RepositoryFile` has new abstract property `suffix`,
- `RepositoryInterface` has new abstract method `get_jsonld`
- `RepositoryInterface` has new abstract property `identifier` and `title`
- bugfixes

## v1.4.0

- update package dependency versions
- minor bugfixes and updates in documentation

## v1.4.0rc2

- using suffix `.jsonld` instead of `.json` for JSON-LD files, as it is recommended
  (see https://www.w3.org/TR/json-ld/#iana-considerations)
- bugfixes in documentation (links, figures, ...)
- enhancing zenodo interfaces:
    - removed depr methods, e.g. `get()` from `AbstractZenodoInterface`
    - using cached json dict for zenodo records. call `refresh()` to update the json
    - minor bugfixes
    - introduced property `files`, which is `Dict[str, RepositoryFile]`
    - improve url handling by using properties instead of class variables

## v1.4.0rc1

- The repository interface to Zenodo has one single upload method `upload_file` with the parameter `metamapper`. It
  is a callable which extracts meta information from the actual file to be uploaded. This is especially useful and
  specifically
  intended for HDF5 files. Unless the value for `metamapper` is `None`, the `upload_file` method will use the built-in
  hdf5 extraction function automatically on HDF5 files.
- Clarify abstraction for HDF5 database interfaces. `HDF5DBInterface` is the top abstraction from which
  `ExtHDF5Interface` inherits. `ExtHDF5Interface` makes use of external databases such as *mongoDB*.
- fix issue in online documentation: mongomock is used to run the mongodb jupyter notebook in the documentation
- codemeta.json file is updated with author and institution ROR ID

## v1.3.2

- calling the RDF accessor on an attribute name will only work if the attribute already exists. If not, an error is
  raised.
- Likewise, if an attribute is deleted, the entry in the RDF accessor dictionary is deleted

## v1.3.1

- minor fixes
- add $in operator to query functions
- add argument `rebase` to layout specifications

## v1.3.0

- important changes:
    - improved and consequent support of RDF/JSON-LD. This means, an HDF5 can be created from a JSON-LD file and vice
      versa. The JSON-LD file
      contains the structural and contextual metadata of the HDF5 file.
    - namespaces are outsourced to `ontolutils`
- minor changes:
    - When a file is opened with a filename which does not exist and mode is None, the file will NOT be created. This
      was
      the case in the past, but this may lead to unwanted empty files.
    - Bugfix namespace creation
    - some method renaming and refactoring
    - accessors are refactored and improved (especially shifted away from xarray and fully integrated in hdf)

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

- scale and offset is now implemented in the package. it should no longer be defined in a convention.
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
- new utils like computing file size
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