"""Module to create the validated metadata for a Zenodo record.

Validation is performed using the pydantic library (also used in h5tbx.convetnions package).

Node, that part of this code is inspired by https://github.com/cthoyt/zenodo-client/tree/main

This code implements the zenodo API as described in https://developers.zenodo.org/#rest-api

As this is done also by the above mentioned library some code might look identical, however, it is just
the implementation of the API.

Also note, that the above mentioned library cannot be used as not all required fields are implemented.
"""
import dateutil
import pydantic
import re
from datetime import datetime
from pydantic import BaseModel, field_validator, Field, ConfigDict
from typing import Optional, Union, List, Dict
from typing_extensions import Literal


def verify_version(version: str) -> str:
    """Verify that version is a valid as defined in https://semver.org/"""
    re_pattern = r'^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
    return re.match(pattern=re_pattern, string=version) is not None


class Creator(BaseModel):
    """Creator Mode class according to Zenodo spec: https://developers.zenodo.org/#representation."""

    name: str  # Format: FamilyName, GivenName
    affiliation: Optional[str] = Field(default=None)
    orcid: Optional[str] = Field(default=None)
    gnd: Optional[str] = Field(default=None)

    @field_validator('name')
    @classmethod
    def _validate_name(cls, value):
        if "," not in value:
            raise ValueError(f'The creator name should be formatted "family name, given names" but is {value}')
        return value


ContributorType = Literal[
    "ContactPerson",
    "DataCollector",
    "DataCurator",
    "DataManager",
    "Distributor",
    "Editor",
    "HostingInstitution",
    "Producer",
    "ProjectLeader",
    "ProjectManager",
    "ProjectMember",
    "RegistrationAgency",
    "RegistrationAuthority",
    "RelatedPerson",
    "Researcher",
    "ResearchGroup",
    "RightsHolder",
    "Supervisor",
    "Sponsor",
    "WorkPackageLeader",
    "Other"
]


class Contributor(Creator):
    """Contributor to the Zenodo record. Is a Person with a role according to
    https://schema.datacite.org/meta/kernel-4.1/include/datacite-contributorType-v4.xsd."""
    type: ContributorType


UploadType = Literal[
    "publication",
    "poster",
    "presentation",
    "dataset",
    "image",
    "video",
    "software",
    "lesson",
    "physicalobject",
    "other",
]

PublicationType = Literal[
    "annotationcollection",
    "book",
    "section",
    "conferencepaper",
    "datamanagementplan",
    "article",
    "patent",
    "preprint",
    "deliverable",
    "milestone",
    "proposal",
    "report",
    "softwaredocumentation",
    "taxonomictreatment",
    "technicalnote",
    "thesis",
    "workingpaper",
    "other",
]

ImageType = Literal[
    "figure",
    "plot",
    "drawing",
    "diagram",
    "photo",
    "other"
]

Datetypes = Literal[
    "created",
    "accepted",
    "available",
    "collected",
    "copyrighted",
    "created",
    "issued",
    "other",
    "submitted",
    "updated",
    "valid",
    "withdrawn",
    'Created',
    'Accepted',
    'Available',
    'Collected',
    'Copyrighted',
    'Created',
    'Issued',
    'Other',
    'Submitted',
    'Updated',
    'Valid',
    'Withdrawn'
]


class DateType(BaseModel):
    """Datetype as used in Zenodo"""
    # date: Union[str, datetime]
    type: Datetypes
    description: Optional[str] = None

    # @field_validator('date')
    # @classmethod
    # def validate_date(cls, value):
    #     """Format Date or Date/Date where Date is YYYY or YYYY-MM or YYYY-MM-DD"""
    #     if isinstance(value, datetime):
    #         return value.strftime('%Y-%m-%d')
    #
    #     if value is None or value.lower() in ('today', 'now', 'none'):
    #         return datetime.today().strftime('%Y-%m-%d')
    #
    #     formats = ['%Y-%m-%d', '%Y-%m', '%Y']
    #
    #     def _check_date(value, format):
    #         try:
    #             datetime.strptime(value, format)
    #             return True
    #         except ValueError:
    #             return False
    #
    #     if not any([_check_date(value, format) for format in formats]):
    #         raise ValueError(f'invalid date format: {value}')
    #     return value


def _parse_ymd(dtime: Union[str, datetime]) -> str:
    if isinstance(dtime, datetime):
        return dtime.strftime('%Y-%m-%d')
    return dateutil.parser.parse(dtime).strftime('%Y-%m-%d')


def _today() -> str:
    """Return today's date in the format YYYY-MM-DD."""
    return _parse_ymd(datetime.today())


class Metadata(BaseModel):
    """Zeno Metadata class according to Zenodo spec: https://developers.zenodo.org/.

    Required fields:
    ----------------
    version
    title
    description
    creators

    Optional/Default fields:
    ----------------
    upload_type=None
    additional_description=None
    dates=[]
    publication_date=datetime.today
    publication_type=None
    image_type=None
    keywords=None
    notes=None
    contributors=[]
    access_right="open"
    license="cc-by-4.0"
    embargo_date=None
    """
    version: Optional[str]
    title: Optional[str]
    description: str
    creators: List[Creator]
    upload_type: UploadType
    additional_description: Optional[Dict] = None
    dates: List[DateType] = pydantic.Field(default_factory=list)
    publication_date: Optional[Union[str, datetime]] = Field(default_factory=_today)
    publication_type: Optional[PublicationType] = None  # if upload_type == publication
    image_type: Optional[ImageType] = None  # if upload_type == image
    keywords: List[str] = None
    notes: Optional[str] = None
    contributors: Optional[List[Contributor]] = pydantic.Field(default_factory=list)
    access_right: Optional[Literal["open", "closed", "restricted", "embargoed"]] = "open"
    license: Optional[Union[str, Dict]] = "cc-by-4.0"
    embargo_date: Optional[Union[str, datetime]] = None

    model_config = ConfigDict(extra='allow')

    @field_validator('license')
    @classmethod
    def _license(cls, value):
        if isinstance(value, dict):
            return value['id']
        return value

    @field_validator('publication_date')
    @classmethod
    def _publication_date(cls, value):
        if isinstance(value, str) and value == 'today':
            return _today()
        return _parse_ymd(value)

    @field_validator('embargo_date')
    @classmethod
    def _embargo_date(cls, value):
        return _parse_ymd(value)

    @field_validator('version')
    @classmethod
    def validate_version(cls, value):
        """Validate the version. See verify_version() for details."""
        if not verify_version(value):
            raise ValueError('invalid version: {value}')
        return value

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.access_right == 'embargoed':
            if self.embargo_date is None:
                raise ValueError("embargo_date is not set but access_right is 'embargoed'")

            def _parse_date(value):
                if isinstance(value, datetime):
                    return value
                for fmt in ['%Y-%m-%d', '%Y-%m', '%Y']:
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        pass
                raise ValueError(f'invalid date format: {value}')

            if self.embargo_date is not None and _parse_date(self.embargo_date) < _parse_date(self.publication_date):
                raise ValueError("embargo_date is in the past")
