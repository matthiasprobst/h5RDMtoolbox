import os
import pathlib
import re
import shutil
from datetime import datetime
from typing import Union, List, Optional
from urllib.parse import urlparse

from dateutil import parser
from pydantic import HttpUrl, FileUrl, field_validator, Field

from ontolutils import Thing, urirefs, namespaces, LangString
from ontolutils.classes.utils import download_file
from .. import foaf
from .. import prov
from ontolutils.typing import AnyThing, AnyIriOf, AnyIri, AnyIriOrListOf, IriList, \
    AnyThingOrList
from ..prov import Attribution
from ..spdx import Checksum

__version__ = "3.0"
_NS = "http://www.w3.org/ns/dcat#"

_EXT_MAP = {
    "csv": "text/csv",
    "tsv": "text/tab-separated-values",
    "json": "application/json",
    "jsonld": "application/ld+json",
    "ttl": "text/turtle",
    "hdf5": "application/x-hdf",
    "hdf": "application/x-hdf",
    "h5": "application/x-hdf",
    "nc": "application/x-netcdf",
    "zip": "application/zip",
    "iges": "model/iges",
    "igs": "model/iges",
    "md": "text/markdown",
    "txt": "text/plain",
    "xml": "application/xml",
    "rdf": "application/rdf+xml",
}


def _parse_media_type(filename_suffix: str) -> str:
    ext = filename_suffix.rsplit('.', 1)[-1].lower()
    return _EXT_MAP.get(ext, "application/octet-stream")


def _parse_license(license: str) -> str:
    """
    Convert a short license code (e.g., 'cc-by-4.0') to its official license URL.

    Supports Creative Commons, MIT, Apache, GPL, BSD, MPL, and others.
    Returns None if no match is found.
    """
    if not license:
        return None
    license_str = str(license)

    if license_str.startswith("http://") or license_str.startswith("https://"):
        return license_str

    code = license_str.strip().lower()

    mapping = {
        # Creative Commons licenses
        "cc0": "https://creativecommons.org/publicdomain/zero/1.0/",
        "cc-by": "https://creativecommons.org/licenses/by/4.0/",
        "cc-by-3.0": "https://creativecommons.org/licenses/by/3.0/",
        "cc-by-4.0": "https://creativecommons.org/licenses/by/4.0/",
        "cc-by-sa": "https://creativecommons.org/licenses/by-sa/4.0/",
        "cc-by-sa-3.0": "https://creativecommons.org/licenses/by-sa/3.0/",
        "cc-by-sa-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
        "cc-by-nd": "https://creativecommons.org/licenses/by-nd/4.0/",
        "cc-by-nd-4.0": "https://creativecommons.org/licenses/by-nd/4.0/",
        "cc-by-nc": "https://creativecommons.org/licenses/by-nc/4.0/",
        "cc-by-nc-4.0": "https://creativecommons.org/licenses/by-nc/4.0/",
        "cc-by-nc-sa": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
        "cc-by-nc-sa-4.0": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
        "cc-by-nc-nd": "https://creativecommons.org/licenses/by-nc-nd/4.0/",
        "cc-by-nc-nd-4.0": "https://creativecommons.org/licenses/by-nc-nd/4.0/",
        # Software licenses
        "mit": "https://opensource.org/licenses/MIT",
        "apache-2.0": "https://www.apache.org/licenses/LICENSE-2.0",
        "gpl-2.0": "https://www.gnu.org/licenses/old-licenses/gpl-2.0.html",
        "gpl-3.0": "https://www.gnu.org/licenses/gpl-3.0.html",
        "lgpl-2.1": "https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html",
        "lgpl-3.0": "https://www.gnu.org/licenses/lgpl-3.0.html",
        "bsd-2-clause": "https://opensource.org/licenses/BSD-2-Clause",
        "bsd-3-clause": "https://opensource.org/licenses/BSD-3-Clause",
        "mpl-2.0": "https://www.mozilla.org/en-US/MPL/2.0/",
        "epl-2.0": "https://www.eclipse.org/legal/epl-2.0/",
        "unlicense": "https://unlicense.org/",
        "proprietary": "https://en.wikipedia.org/wiki/Proprietary_software",
    }

    return mapping.get(code, code)


@namespaces(dcat=_NS,
            dcterms="http://purl.org/dc/terms/",
            prov="http://www.w3.org/ns/prov#",
            adms="http://www.w3.org/ns/adms#",
            )
@urirefs(Resource='dcat:Resource',
         title='dcterms:title',
         description='dcterms:description',
         creator='dcterms:creator',
         publisher='dcterms:publisher',
         issued='dcterms:issued',
         modified='dcterms:modified',
         contributor='dcterms:contributor',
         license='dcterms:license',
         version='dcat:version',
         hasVersion='dcat:hasVersion',
         identifier='dcterms:identifier',
         hasPart='dcterms:hasPart',
         keyword='dcat:keyword',
         qualifiedAttribution='prov:qualifiedAttribution',
         accessRights='dcterms:accessRights',
         language='dcterms:language',
         versionNotes='adms:versionNotes',
         hasCurrentVersion='dcat:hasCurrentVersion',
         wasGeneratedBy='prov:wasGeneratedBy',
         first='dcat:first',
         last='dcat:last',
         prev='dcat:prev',
         previousVersion='dcat:previousVersion'
         )
class Resource(Thing):
    """Pydantic implementation of dcat:Resource

    .. note::

        More than the below parameters are possible but not explicitly defined here.



    Parameters
    ----------
    title: str
        Title of the resource (dcterms:title)
    description: str = None
        Description of the resource (dcterms:description)
    creator: Union[
        foaf.Agent, foaf.Organization, foaf.Person, prov.Person, prov.Agent, prov.Organization, HttpUrl,
        List[Union[foaf.Agent, foaf.Organization, foaf.Person, prov.Person, prov.Agent, prov.Organization, HttpUrl]]
    ] = None
        Creator of the resource (dcterms:creator)
    publisher: Union[Agent, List[Agent]] = None
        Publisher of the resource (dcterms:publisher)
    contributor: Union[Agent, List[Agent]] = None
        Contributor of the resource (dcterms:contributor)
    license: ResourceType = None
        License of the resource (dcat:license)
    version: str = None
        Version of the resource (dcat:version),
        best following semantic versioning (https://semver.org/lang/de/)
    identifier: str = None
        Identifier of the resource (dcterms:identifier)
    hasPart: ResourceType = None
        A related resource that is included either physically or logically in the described resource. (dcterms:hasPart)
    keyword: List[str]
        Keywords for the distribution.
    """
    title: Optional[Union[LangString, List[LangString]]] = None  # dcterms:title
    description: Optional[Union[LangString, List[LangString]]] = None  # dcterms:description
    creator: Optional[Union[AnyIri, prov.Person, foaf.Person, prov.Organization, foaf.Organization, List[
        Union[AnyIri, prov.Person, foaf.Person, prov.Organization, foaf.Organization]]]] = None  # dcterms:creator
    publisher: AnyIriOrListOf[foaf.Agent] = None  # dcterms:publisher
    issued: datetime = None  # dcterms:issued
    modified: datetime = None  # dcterms:modified
    contributor: AnyIriOrListOf[foaf.Agent] = None  # dcterms:contributor
    license: Optional[IriList] = None  # dcat:license
    version: str = None  # dcat:version
    versionNote: Optional[Union[LangString, List[LangString]]] = Field(default=None,
                                                                       alias='version_note')  # adms:versionNote
    identifier: str = None  # dcterms:identifier
    hasPart: Optional[AnyThingOrList] = Field(default=None, alias='has_part')
    keyword: Optional[Union[str, List[str]]] = None  # dcat:keyword
    hasVersion: Optional[IriList] = Field(default=None,
                                          alias='has_version')  # dcat:hasVersion
    qualifiedAttribution: AnyIriOf[Attribution] = None  # dcterms:qualifiedAttribution
    accessRights: AnyIriOf[str] = Field(default=None,
                                        alias='access_rights')  # dcterms:accessRights
    language: AnyIriOf[str] = None  # dcterms:language
    versionNotes: Optional[Union[LangString, List[LangString]]] = Field(default=None,
                                                                        alias='version_notes')  # adms:versionNotes

    wasGeneratedBy: AnyThing = Field(
        default=None,
        alias='was_generated_by'
    )  # prov:wasGeneratedBy
    first: Optional[AnyThing] = None  # dcat:first
    last: Optional[AnyThing] = None  # dcat:last
    prev: Optional[AnyThing] = Field(default=None, alias='prev')  # dcat:prev
    previousVersion: Optional[AnyThing] = Field(default=None, alias='previous_version')  # dcat:previousVersion
    hasCurrentVersion: Optional[AnyThing] = Field(default=None,
                                                  alias='has_current_version')  # dcat:hasCurrentVersion

    @field_validator('identifier', mode='before')
    @classmethod
    def _identifier(cls, identifier):
        """parse datetime"""
        if identifier is None:
            return None
        if identifier.startswith('http'):
            return str(HttpUrl(identifier))
        return identifier

    @field_validator('license', mode='before')
    @classmethod
    def _license(cls, license):
        """parse license to URL if possible"""
        if isinstance(license, str):
            return _parse_license(license)
        elif isinstance(license, list):
            return [_parse_license(lic) if isinstance(lic, str) else lic for lic in license]
        return license


@namespaces(dcat=_NS,
            prov="http://www.w3.org/ns/prov#",
            dcterms="http://purl.org/dc/terms/")
@urirefs(Distribution='dcat:Distribution',
         downloadURL='dcat:downloadURL',
         accessURL='dcat:accessURL',
         mediaType='dcat:mediaType',
         byteSize='dcat:byteSize',
         hasPart='dcterms:hasPart',
         checksum='spdx:checksum',
         accessService='dcat:accessService',
         conformsTo='dcterms:conformsTo'
         )
class Distribution(Resource):
    """Implementation of dcat:Distribution

    .. note::
        More than the below parameters are possible but not explicitly defined here.


    Parameters
    ----------
    downloadURL: Union[HttpUrl, FileUrl]
        Download URL of the distribution (dcat:downloadURL)
    mediaType: HttpUrl = None
        Media type of the distribution (dcat:mediaType).
        Should be defined by the [IANA Media Types registry](https://www.iana.org/assignments/media-types/media-types.xhtml)
    byteSize: int = None
        Size of the distribution in bytes (dcat:byteSize)
    """
    downloadURL: Union[HttpUrl, FileUrl, pathlib.Path] = Field(default=None, alias='download_URL')
    accessURL: Union[HttpUrl, FileUrl, pathlib.Path] = Field(default=None, alias='access_URL')
    mediaType: Optional[AnyThing] = Field(default=None, alias='media_type')  # dcat:mediaType
    byteSize: int = Field(default=None, alias='byte_size')  # dcat:byteSize
    hasPart: Optional[AnyThing] = Field(default=None, alias='has_part')  # dcterms:hasPart
    checksum: Optional[AnyIriOf[Checksum]] = None  # spdx:checksum
    accessService: Optional[AnyThing] = Field(default=None, alias='access_service')  # dcat:accessService
    conformsTo: Optional[AnyThing] = Field(default=None, alias='conforms_to')  # dcterms:conformsTo

    def _repr_html_(self):
        """Returns the HTML representation of the class"""
        if self.download_URL is not None:
            return f"{self.__class__.__name__}({self.download_URL})"
        return super()._repr_html_()

    def download(self,
                 dest_filename: Union[str, pathlib.Path] = None,
                 target_folder: Union[str, pathlib.Path] = None,
                 overwrite_existing: bool = False,
                 **kwargs) -> pathlib.Path:
        """Downloads the distribution
        kwargs are passed to the download_file function, which goes to requests.get()"""

        if target_folder is not None and dest_filename is not None:
            raise ValueError('Either target_folder or dest_filename can be provided, not both')

        downloadURL = str(self.downloadURL)
        if self.download_URL is None:
            raise ValueError('The downloadURL is not defined')

        def _get_filename():
            if str(downloadURL).endswith("/content"):
                filename = str(downloadURL).rsplit("/", 2)[-2]
            else:
                filename = os.path.basename(urlparse(str(downloadURL)).path)
            if filename == '':
                filename = str(downloadURL).rsplit("#", 1)[-1]
            return filename

        if target_folder is not None:
            target_folder = pathlib.Path(str(target_folder))
            target_folder.mkdir(parents=True, exist_ok=True)
            dest_filename = target_folder / _get_filename()
        else:
            if dest_filename is None:
                target_folder = pathlib.Path.cwd()
                dest_filename = target_folder / pathlib.Path(_get_filename())
            else:
                dest_filename = pathlib.Path(dest_filename)
            if dest_filename.is_dir():
                raise IsADirectoryError(f'Destination filename {dest_filename} is a directory')

        if "exist_ok" in kwargs:
            overwrite_existing = kwargs.pop("exist_ok")

        def _parse_file_url(furl):
            """in windows, we might need to strip the leading slash"""
            # if on windows, lstrip:
            if os.name == 'nt':
                return pathlib.Path(urlparse(self.downloadURL.unicode_string()).path.lstrip("/\\"))
            return pathlib.Path(urlparse(self.downloadURL.unicode_string()).path)

        if self.download_URL.scheme == 'file':
            _src_filename = _parse_file_url(self.download_URL.path)
            if not _src_filename.exists():
                raise FileNotFoundError(f"Source file '{_src_filename}' does not exist")
            if dest_filename is None:
                return _src_filename
            else:
                if _src_filename.resolve() == dest_filename.resolve():
                    return dest_filename
                return shutil.copy(_src_filename, dest_filename)

        if dest_filename is None:
            raise ValueError(f"No destination filename provided for download of {self.download_URL}")
        if not dest_filename.suffix.startswith("."):
            raise ValueError('Destination filename must have a valid suffix/extension')

        if dest_filename.exists():
            return dest_filename

        return download_file(self.download_URL,
                             dest_filename,
                             exist_ok=overwrite_existing,
                             **kwargs)

    @field_validator('mediaType', mode='before')
    @classmethod
    def _mediaType(cls, mediaType):
        """should be a valid URI, like: https://www.iana.org/assignments/media-types/text/markdown"""
        if isinstance(mediaType, str):
            if mediaType.startswith('http'):
                return mediaType
            elif mediaType.startswith('iana:'):
                return "https://www.iana.org/assignments/media-types/" + mediaType.split(":", 1)[-1]
            elif re.match('[a-z].*/[a-z].*', mediaType):
                return "https://www.iana.org/assignments/media-types/" + mediaType
            else:
                return "https://www.iana.org/assignments/media-types/" + _parse_media_type(mediaType)
        return mediaType

    @field_validator('downloadURL', mode='before')
    @classmethod
    def _downloadURL(cls, downloadURL):
        """a pathlib.Path is also allowed but needs to be converted to a URL"""
        if isinstance(downloadURL, pathlib.Path):
            return FileUrl(downloadURL.resolve().as_uri())
        return downloadURL


@namespaces(dcat=_NS,
            prov="http://www.w3.org/ns/prov#",
            dcterms="http://purl.org/dc/terms/")
@urirefs(Dataset='dcat:Dataset',
         identifier='dcterms:identifier',
         creator='dcterms:creator',
         distribution='dcat:distribution',
         modified='dcterms:modified',
         landingPage='dcat:landingPage',
         inSeries='dcat:inSeries',
         license='dcterms:license',
         spatial='dcterms:spatial',  # The geographical area covered by the dataset.
         spatialResolutionInMeters='dcterms:spatialResolutionInMeters',
         temporalResolution='dcat:temporalResolution'
         )
class Dataset(Resource):
    """Pydantic implementation of dcat:Dataset

    .. note::

        More than the below parameters are possible but not explicitly defined here.



    Parameters
    ----------
    title: str
        Title of the resource (dcterms:title)
    description: str = None
        Description of the resource (dcterms:description)
    version: str = None
        Version of the resource (dcat:version)
    identifier: str = None
        Identifier of the resource (dcterms:identifier)
    distribution: List[Distribution] = None
        Distribution of the resource (dcat:Distribution)
    landingPage: HttpUrl = None
        Landing page of the resource (dcat:landingPage)
    modified: datetime = None
        Last modified date of the resource (dcterms:modified)
    inSeries: Thing or IRI, optional
        The series the dataset belongs to (dcat:inSeries)
    """
    identifier: Union[
        str, LangString] = None  # dcterms:identifier, see https://www.w3.org/TR/vocab-dcat-3/#ex-identifier
    # http://www.w3.org/ns/prov#Person, see https://www.w3.org/TR/vocab-dcat-3/#ex-adms-identifier
    distribution: Optional[AnyIriOrListOf[Distribution]] = Field(default=None)  # dcat:Distribution
    modified: datetime = Field(default=None)  # dcterms:modified
    landingPage: HttpUrl = Field(default=None, alias="landing_page")  # dcat:landingPage
    inSeries: Optional[AnyThing] = Field(default=None, alias='in_series')  # dcat:inSeries
    license: Optional[IriList] = Field(default=None)  # dcat:license
    spatial: Optional[AnyIriOrListOf[str]] = Field(default=None)  # dcterms:spatial
    spatialResolutionInMeters: Optional[Union[float, str]] = Field(
        default=None,
        alias='spatial_resolution_in_meters'
    )  # dcterms:spatialResolutionInMeters
    temporal: Optional[AnyThing] = Field(
        default=None,
        alias='temporal',
        description="The temporal period that the dataset covers."
    )  # dcterms:temporal
    temporalResolution: Optional[Union[float, str]] = Field(
        default=None,
        alias='temporal_resolution',
        description="The temporal resolution of the dataset."
    )  # dcterms:temporalResolution

    @field_validator('modified', mode='before')
    @classmethod
    def _modified(cls, modified):
        """parse datetime"""
        if isinstance(modified, str):
            return parser.parse(modified)
        return modified


@namespaces(dcat=_NS,
            prov="http://www.w3.org/ns/prov#",
            dcterms="http://purl.org/dc/terms/",
            foaf="http://xmlns.com/foaf/0.1/",
            )
@urirefs(Catalog='dcat:Catalog',
         dataset='dcat:dataset',
         primaryTopic='foaf:primaryTopic',
         record='dcterms:record',
         resource='dcat:resource',
         service='dcat:service',
         homepage='foaf:homepage',
         catalog='dcat:catalog',
         themeTaxonomy='dcat:themeTaxonomy'
         )
class Catalog(Dataset):
    """A curated collection of metadata about resources."""
    dataset: Optional[AnyIriOrListOf[Dataset]] = Field(default=None, alias="dataset")  # dcat:dataset
    primaryTopic: AnyThingOrList = None  # dcterms:primaryTopic
    record: AnyThingOrList = Field(default=None, alias='catalog_record')  # dcterms:catalogRecord
    resource: Optional[AnyIriOrListOf[Resource]] = None  # dcterms:resource
    service: Optional[AnyThingOrList] = None  # dcterms:service
    homepage: Optional[AnyIri] = None  # foaf:homepage
    catalog: "Catalog" = None  # dcat:catalog
    themeTaxonomy: Optional[AnyThingOrList] = Field(default=None, alias='theme')  # dcat:themeTaxonomy


Catalog.model_rebuild(force=True)
