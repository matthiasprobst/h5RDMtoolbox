from pydantic import AnyUrl, Field, model_validator

from ontolutils import urirefs, namespaces, Thing, as_id
from ontolutils.typing import AnyIri, Mailbox

__version__ = "0.1"
_NS = "http://xmlns.com/foaf/0.1/"


@namespaces(foaf=_NS)
@urirefs(
    Agent="foaf:Agent",
    name="foaf:name",
    mbox="foaf:mbox",
    gender="foaf:gender",
    yahooChatID="foaf:yahooChatID",
    account="foaf:account",
    birthday="foaf:birthday",
    icqChatID="foaf:icqChatID",
    aimChatID="foaf:aimChatID",
    jabberID="foaf:jabberID",
    made="foaf:made",
    interest="foaf:interest",
    tipjar="foaf:tipjar",
    skypeID="foaf:skypeID",
    topic_interest="foaf:topic_interest",
    age="foaf:age",
    mbox_sha1sum="foaf:mbox_sha1sum",
    status="foaf:status",
    msnChatID="foaf:msnChatID",
    openid="foaf:openid",
    holdsAccount="foaf:holdsAccount",
    weblog="foaf:weblog",
    homepage="foaf:homepage"
)
class Agent(Thing):
    """A foaf:Agent with selected personal and account metadata.

        Common fields include ``name``, ``mbox`` (alias ``email``), ``homepage``,
        and ``age``. An ``openid`` value can supply the resource ID through
        the model's before-validator. Inspect ``model_fields`` for all declared
        fields and aliases; extra Python fields are not automatically mapped
        to FOAF predicates.
    """
    name: str = Field(default=None, alias="name")
    gender: str = Field(default=None, alias="gender")  # foaf:gender
    yahooChatID: str = Field(default=None, alias="yahoo_chat_id")  # foaf:yahooChatID
    account: AnyUrl = Field(default=None, alias="account")  # foaf:account
    birthday: str = Field(default=None, alias="birthday")  # foaf:birthday
    icqChatID: str = Field(default=None, alias="icq_chat_id")  # foaf:icqChatID
    aimChatID: str = Field(default=None, alias="aim_chat_id")  # foaf:aimChatID
    jabberID: str = Field(default=None, alias="jabber_id")  # foaf:jabberID
    made: AnyUrl = Field(default=None, alias="made")  # foaf:made
    mbox: Mailbox = Field(default=None, alias="email")  # foaf:mbox
    interest: AnyUrl = Field(default=None, alias="interest")  # foaf:interest
    tipjar: AnyUrl = Field(default=None, alias="tipjar")  # foaf:tipjar
    skypeID: str = Field(default=None, alias="skype_id")  # foaf:skypeID
    topic_interest: AnyUrl = Field(default=None, alias="topic_interest")  # foaf:topic_interest
    age: int = Field(default=None, alias="age")  # foaf:age
    mbox_sha1sum: str = Field(default=None, alias="mbox_sha1sum")  # foaf:mbox_sha1sum
    status: str = Field(default=None, alias="status")  # foaf:status
    msnChatID: str = Field(default=None, alias="msn_chat_id")  # foaf:msnChatID
    openid: AnyUrl = Field(default=None, alias="open_id")  # foaf:openid
    holdsAccount: AnyUrl = Field(default=None, alias="holds_account")  # foaf:holdsAccount
    weblog: AnyUrl = Field(default=None, alias="weblog")  # foaf:weblog
    homepage: AnyIri = Field(default=None, alias="homepage")  # foaf:homepage

    @model_validator(mode="before")
    def change_id(self):
        """Use openid as the resource ID when no explicit id was supplied.

        """
        return as_id(self, "openid")


@namespaces(foaf=_NS)
@urirefs(Person="foaf:Person",
         firstName="foaf:firstName",
         familyName="foaf:familyName",
         lastName="foaf:lastName",
         plan="foaf:plan",
         surname="foaf:surname",
         geekcode="foaf:geekcode",
         pastProject="foaf:pastProject",
         publications="foaf:publications",
         currentProject="foaf:currentProject",
         workInfoHomepage="foaf:workInfoHomepage",
         myersBriggs="foaf:myersBriggs",
         schoolHomepage="foaf:schoolHomepage",
         img="foaf:img",
         workplaceHomepage="foaf:workplaceHomepage")
class Person(Agent):
    """A foaf:Person extending Agent with name, project, and profile fields.

        Fields include ``firstName``, ``familyName``, and ``lastName``; see
        ``model_fields`` for their input aliases. This model uses
        ``http://xmlns.com/foaf/0.1/Person``, not the PROV Person class.
    """
    firstName: str = Field(default=None, alias="first_name")
    familyName: str = Field(default=None, alias="family_name")
    lastName: str = Field(default=None, alias="last_name")
    plan: str = Field(default=None, alias="plan")
    surname: str = Field(default=None, alias="surname")
    geekcode: str = Field(default=None, alias="geekcode")
    pastProject: str = Field(default=None, alias="past_project")
    publications: str = Field(default=None, alias="publications")
    currentProject: str = Field(default=None, alias="current_project")
    workInfoHomepage: AnyUrl = Field(default=None, alias="work_info_homepage")
    myersBriggs: str = Field(default=None, alias="myers_briggs")
    schoolHomepage: AnyUrl = Field(default=None, alias="school_homepage")
    img: AnyUrl = Field(default=None, alias="img")
    workplaceHomepage: AnyUrl = Field(default=None, alias="workplace_homepage")


@namespaces(foaf=_NS)
@urirefs(Organization='foaf:Organization',
         name='foaf:name')
class Organization(Agent):
    """Pydantic Model for http://www.w3.org/ns/prov#Organization

    .. note::

        More than the below parameters are possible but not explicitly defined here.


    Parameters
    ----------
    mbox: EmailStr = None
        Email address (foaf:mbox)
    """
