from typing import Optional

from ontolutils import Thing, as_id
from ontolutils import urirefs, namespaces
from ontolutils.typing import ResourceType
from pydantic import EmailStr, AnyUrl
from pydantic import Field, model_validator


@namespaces(foaf="http://xmlns.com/foaf/0.1/")
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
    homepage="foaf:homepage",
)
class Agent(Thing):
    """Pydantic Modell für http://www.w3.org/ns/prov#Agent

    .. Hinweis::

        Mehr als die unten aufgeführten Parameter sind möglich, aber hier nicht explizit definiert.

    Parameter
    ---------
    gender: str = None
        Geschlecht (foaf:gender)
    yahooChatID: str = None
        Yahoo Chat-ID (foaf:yahooChatID)
    account: AnyUrl = None
        Account-URL (foaf:account)
    birthday: str = None
        Geburtstag (foaf:birthday)
    icqChatID: str = None
        ICQ Chat-ID (foaf:icqChatID)
    aimChatID: str = None
        AIM Chat-ID (foaf:aimChatID)
    jabberID: str = None
        Jabber-ID (foaf:jabberID)
    made: AnyUrl = None
        Erstellt-URL (foaf:made)
    mbox: EmailStr = None
        E-Mail-Adresse (foaf:mbox)
    interest: AnyUrl = None
        Interessens-URL (foaf:interest)
    tipjar: AnyUrl = None
        Tipjar-URL (foaf:tipjar)
    skypeID: str = None
        Skype-ID (foaf:skypeID)
    topic_interest: AnyUrl = None
        Themeninteresse-URL (foaf:topic_interest)
    age: int = None
        Alter (foaf:age)
    mbox_sha1sum: str = None
        SHA1-Summe der E-Mail (foaf:mbox_sha1sum)
    status: str = None
        Status (foaf:status)
    msnChatID: str = None
        MSN Chat-ID (foaf:msnChatID)
    openid: AnyUrl = None
        OpenID-URL (foaf:openid)
    holdsAccount: AnyUrl = None
        Account-Inhaber-URL (foaf:holdsAccount)
    weblog: AnyUrl = None
        Weblog-URL (foaf:weblog)
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
    mbox: EmailStr = Field(default=None, alias="email")  # foaf:mbox
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
    homepage: Optional[ResourceType] = Field(default=None, alias="homepage")  # foaf:homepage

    @model_validator(mode="before")
    def change_id(self):
        """Change the id to the downloadURL"""
        return as_id(self, "openid")


@namespaces(foaf="http://xmlns.com/foaf/0.1/")
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
    """Pydantic Model für http://www.w3.org/ns/prov#Person

    .. note::

        Mehr als die unten aufgeführten Parameter sind möglich, aber hier nicht explizit definiert.

    Parameter
    ---------
    firstName: str
        Vorname (foaf:firstName)
    familyName: str
        Familienname (foaf:familyName)
    lastName: str
        Nachname (foaf:lastName)
    family_name: str
        Familienname (foaf:family_name)
    plan: str
        Plan (foaf:plan)
    surname: str
        Nachname (foaf:surname)
    geekcode: str
        Geekcode (foaf:geekcode)
    pastProject: str
        Vergangenes Projekt (foaf:pastProject)
    publications: str
        Publikationen (foaf:publications)
    currentProject: str
        Aktuelles Projekt (foaf:currentProject)
    workInfoHomepage: AnyUrl
        Arbeitsinfo-Homepage (foaf:workInfoHomepage)
    myersBriggs: str
        Myers-Briggs Typ (foaf:myersBriggs)
    schoolHomepage: AnyUrl
        Schul-Homepage (foaf:schoolHomepage)
    img: AnyUrl
        Bild-URL (foaf:img)
    workplaceHomepage: AnyUrl
        Arbeitsplatz-Homepage (foaf:workplaceHomepage)
    """
    firstName: str = Field(default=None, alias="first_name")
    familyName: str = Field(default=None, alias="family_name")
    lastName: str = Field(default=None, alias="last_name")
    family_name: str = Field(default=None, alias="family_name")
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

@namespaces(foaf="http://xmlns.com/foaf/0.1/")
@urirefs(
    Organization="foaf:Organization",
)
class Organization(Agent):
    """Pydantic Modell für http://xmlns.com/foaf/0.1/Organization
    """
    pass
