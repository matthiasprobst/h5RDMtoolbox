from typing import List, Union

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import convention

cv = convention.Convention(name='PersonConvention', contact='John Doe')
cv.register()

from pydantic import BaseModel
from typing_extensions import Literal

Role = Literal[
    "Creator",
    "ContactPerson",
]


class Person(BaseModel):
    first_name: str
    last_name: str
    role: Role


class Creator(Person):
    """Creator of a dataset. Subclass of Person"""
    role: Literal["Creator"] = "Creator"


class Contributors(BaseModel):
    contributors: Union[Person, List[Person]]


class PersonAttribute(h5tbx.convention.standard_attributes.StandardAttribute):

    def __setter__(self, parent, value, attrs=None):
        """Is called when attribute of a standard attribute is set"""
        grp_name = self.validator.__name__
        # i = 0
        # while grp_name in parent:
        #     i += 1
        #     grp_name = f'{value["role"]}Person{i}'
        person_grp = parent.create_group(grp_name)
        person_grp.attrs['iri'] = 'http://www.w3.org/ns/prov#Person'

        person_grp.create_string_dataset('first_name',
                                         data=value['first_name'],
                                         attrs=dict(iri='http://xmlns.com/foaf/0.1/firstName',
                                                    description='The first name of a person'))
        person_grp.create_string_dataset('last_name',
                                         data=value['last_name'],
                                         attrs=dict(iri='http://xmlns.com/foaf/0.1/lastName',
                                                    description='The last name of a person'))


class ContributorAttribute(h5tbx.convention.standard_attributes.StandardAttribute):
    def __setter__(self, parent, value, attrs=None):
        def _overwrite_contributor(_person, _id):
            grp_name = f'Contributor{_id}'
            if grp_name in parent:
                del parent[grp_name]
            person_grp = parent.create_group(grp_name)
            person_grp.attrs['iri'] = 'http://www.w3.org/ns/prov#Person'

            person_grp.create_string_dataset('first_name',
                                             data=value['first_name'],
                                             attrs=dict(iri='http://xmlns.com/foaf/0.1/firstName',
                                                        description='The first name of a person'))
            person_grp.create_string_dataset('last_name',
                                             data=value['last_name'],
                                             attrs=dict(iri='http://xmlns.com/foaf/0.1/lastName',
                                                        description='The last name of a person'))

        if isinstance(value, list):
            for i, person in enumerate(value):
                _overwrite_contributor(person, i)
        else:
            _overwrite_contributor(value, 1)


personStdAttr = PersonAttribute(
    name='person',
    validator=Person,
    target_method='__init__',
    description='Person',
    default_value='$none'
)
creatorStdAttr = PersonAttribute(
    name='creator',
    validator=Creator,
    target_method='__init__',
    description='Creator of the file or dataset.',
    default_value='$none'
)
contributorsStdAttr = ContributorAttribute(
    name='contributors',
    validator=Contributors,
    target_method='__init__',
    description='Contributors to the file or dataset.',
    default_value='$none'
)
Creator(first_name='Matthias', last_name='Probst')

cv.add_standard_attribute(personStdAttr)
cv.add_standard_attribute(creatorStdAttr)
cv.add_standard_attribute(contributorsStdAttr)
# cv.registered_standard_attributes

h5tbx.use(None)
h5tbx.use(cv.name)

Person(first_name='Matthias', last_name='Probst', role='Creator')

with h5tbx.File(creator=dict(first_name='Matthias', last_name='Probst'),
                contributors=dict(first_name='Matthias', last_name='Probst',
                                  role='Creator')) as h5:
    h5.sdump()

# with h5tbx.File(creator=dict(first_name='Matthias', last_name='Probst'),
#                 contributors=[dict(first_name='Matthias', last_name='Probst',
#                                    role='Creator')]) as h5:
#     h5.sdump()
# with h5tbx.File(person=dict(first_name='Matthias', last_name='Probst', role='Creator'),
#                 creator=dict(first_name='Matthias', last_name='Probst')) as h5:
#     h5.sdump()
