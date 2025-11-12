import pathlib
from datetime import datetime
from typing import Union, List, Optional

import rdflib
from dateutil import parser
from ontolutils import Thing, as_id, urirefs, namespaces, LangString
from ontolutils.namespacelib.spdx import SPDX
from ontolutils.typing import ResourceType
from pydantic import FileUrl
from pydantic import HttpUrl, field_validator, Field, model_validator

from .foaf import Agent


def license_to_url(license_str: str) -> str:
    """
    Convert a short license code (e.g., 'cc-by-4.0') to its official license URL.

    Supports Creative Commons, MIT, Apache, GPL, BSD, MPL, and others.
    Returns None if no match is found.
    """
    if not license_str:
        return None

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

    return mapping.get(code)


@namespaces(dcat="http://www.w3.org/ns/dcat#",
            dcterms="http://purl.org/dc/terms/", )
@urirefs(Resource='dcat:Resource',
         title='dcterms:title',
         description='dcterms:description',
         creator='dcterms:creator',
         publisher='dcterms:publisher',
         contributor='dcterms:contributor',
         license='dcterms:license',
         version='dcat:version',
         identifier='dcterms:identifier',
         hasPart='dcterms:hasPart',
         keyword='dcat:keyword')
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
    creator: Union[Agent, List[Agent]] = None
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
    creator: Union[Agent, ResourceType, List[Union[ResourceType, Agent]]] = None  # dcterms:creator
    publisher: Union[Agent, List[Agent]] = None  # dcterms:publisher
    contributor: Union[Agent, List[Agent]] = None  # dcterms:contributor
    license: Optional[Union[ResourceType, List[ResourceType]]] = None  # dcat:license
    version: str = None  # dcat:version
    identifier: str = None  # dcterms:identifier
    hasPart: Optional[Union[ResourceType, List[ResourceType]]] = Field(default=None, alias='has_part')
    keyword: Union[LangString, List[LangString]] = None  # dcat:keyword

    @model_validator(mode="before")
    def change_id(self):
        """Change the id to the downloadURL"""
        return as_id(self, "identifier")

    @field_validator('identifier', mode='before')
    @classmethod
    def _identifier(cls, identifier):
        """parse datetime"""
        if identifier.startswith('http'):
            return str(HttpUrl(identifier))
        return identifier

    @field_validator('license', mode='before')
    @classmethod
    def _license(cls, license):
        return license_to_url(license) if isinstance(license, str) else license


@namespaces(spdx="http://spdx.org/rdf/terms#")
@urirefs(Checksum='spdx:Checksum',
         algorithm='spdx:algorithm',
         checksumValue='spdx:checksumValue')
class Checksum(Thing):
    """Pydantic implementation of dcat:Checksum

    Parameters
    ----------
    algorithm: str
        The algorithm used to compute the checksum (e.g. "MD5", "SHA-1", "SHA-256")
    checksumValue: str
        The checksum value
    """
    algorithm: Optional[Union[str, ResourceType]] = Field(default="None")  # dcat:algorithm
    checksumValue: str = Field(alias="value")  # dcat:value

    @field_validator("algorithm", mode="before")
    @classmethod
    def validate_algorithm(cls, algorithm_value: Union[str, ResourceType]) -> Union[str, ResourceType]:
        if isinstance(algorithm_value, rdflib.URIRef):
            return str(algorithm_value)
        if isinstance(algorithm_value, str) and str(algorithm_value).startswith("http"):
            return str(algorithm_value)
        if isinstance(algorithm_value, str):
            guess_name = f"checksumAlgorithm_{algorithm_value.lower()}"
            return str(SPDX[guess_name])
        return str(algorithm_value)


@namespaces(dcat="http://www.w3.org/ns/dcat#",
            spdx="http://spdx.org/rdf/terms#")
@urirefs(Distribution='dcat:Distribution',
         downloadURL='dcat:downloadURL',
         accessURL='dcat:accessURL',
         mediaType='dcat:mediaType',
         byteSize='dcat:byteSize',
         checksum='spdx:checksum')
class Distribution(Resource):
    """Implementation of dcat:Distribution

    .. note::
        More than the below parameters are possible but not explicitly defined here.


    Parameters
    ----------
    downloadURL: Union[HttpUrl, FileUrl]
        Download URL of the distribution (dcat:downloadURL)
    mediaType: ResourceType = None
        Media type of the distribution (dcat:mediaType).
        Should be defined by the [IANA Media Types registry](https://www.iana.org/assignments/media-types/media-types.xhtml)
    byteSize: int = None
        Size of the distribution in bytes (dcat:byteSize)
    """
    downloadURL: Union[HttpUrl, FileUrl, pathlib.Path] = Field(default=None, alias='download_URL')
    accessURL: Union[HttpUrl, FileUrl, pathlib.Path] = Field(default=None, alias='access_URL')
    mediaType: Optional[Union[str, ResourceType]] = Field(default=None, alias='media_type')  # dcat:mediaType
    byteSize: Optional[int] = Field(default=None, alias='byte_size')  # dcat:byteSize
    checksum: Optional[Checksum] = None  # dcat:checksum

    def _repr_html_(self):
        """Returns the HTML representation of the class"""
        if self.downloadURL is not None:
            return f"{self.__class__.__name__}({self.downloadURL})"
        return super()._repr_html_()

    @field_validator('mediaType', mode='before')
    @classmethod
    def _mediaType(cls, mediaType):
        """should be a valid URI, like: https://www.iana.org/assignments/media-types/text/markdown"""
        if isinstance(mediaType, str):
            if mediaType.startswith('http'):
                return HttpUrl(mediaType)
            elif mediaType.startswith('iana:'):
                return HttpUrl("https://www.iana.org/assignments/media-types/" + mediaType.split(":", 1)[-1])
            # elif re.match('[a-z].*/[a-z].*', mediaType):
            #     return HttpUrl("https://www.iana.org/assignments/media-types/" + mediaType)
        return mediaType

    @field_validator('downloadURL', mode='before')
    @classmethod
    def _downloadURL(cls, downloadURL):
        """a pathlib.Path is also allowed but needs to be converted to a URL"""
        if isinstance(downloadURL, pathlib.Path):
            return str(FileUrl(f'file://{downloadURL.resolve().absolute()}'))
        try:
            return str(FileUrl(downloadURL))
        except ValueError:
            return str(HttpUrl(downloadURL))

    def download(self,
                 target_folder: Union[str, pathlib.Path],
                 exist_ok: bool = False,
                 **kwargs) -> pathlib.Path:
        """Downloads the distribution
        kwargs are passed to the download_file function, which goes to requests.get()"""
        from ..utils import download_file
        if self.name is None:
            raise ValueError(f"Cannot download distribution without a name.")
        return download_file(
            file_url=self.downloadURL,
            filename=self.name,
            target_folder=pathlib.Path(target_folder),
            checksum=self.checksum.checksumValue,
            checksum_algorithm=self.checksum.algorithm
        )


@namespaces(dcat="http://www.w3.org/ns/dcat#")
@urirefs(DatasetSeries='dcat:DatasetSeries')
class DatasetSeries(Resource):
    """Pydantic implementation of dcat:DatasetSeries"""


@namespaces(dcat="http://www.w3.org/ns/dcat#",
            prov="http://www.w3.org/ns/prov#",
            dcterms="http://purl.org/dc/terms/")
@urirefs(Dataset='dcat:Dataset',
         distribution='dcat:distribution',
         modified='dcterms:modified',
         landingPage='dcat:landingPage',
         inSeries='dcat:inSeries',
         theme='dcat:theme')
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
    distribution: Union[Distribution, List[Distribution]] = None
        Distribution of the resource (dcat:Distribution)
    landingPage: HttpUrl = None
        Landing page of the resource (dcat:landingPage)
    modified: datetime = None
        Last modified date of the resource (dcterms:modified)
    inSeries: DatasetSeries = None
        The series the dataset belongs to (dcat:inSeries)
    theme: HttpUrl or StandardNameTable = None
        A main category of the resource. A resource can have multiple themes.
    """
    # http://www.w3.org/ns/prov#Person, see https://www.w3.org/TR/vocab-dcat-3/#ex-adms-identifier
    distribution: Union[Distribution, List[Distribution]] = None  # dcat:Distribution
    modified: datetime = None  # dcterms:modified
    landingPage: HttpUrl = Field(default=None, alias='landing_page')  # dcat:landingPage
    inSeries: DatasetSeries = Field(default=None, alias='in_series')  # dcat:inSeries
    theme: Optional[Union[ResourceType, Thing]] = Field(default=None)  # dcat:theme

    @field_validator('modified', mode='before')
    @classmethod
    def _modified(cls, modified):
        """parse datetime"""
        if isinstance(modified, str):
            return parser.parse(modified)
        return modified
