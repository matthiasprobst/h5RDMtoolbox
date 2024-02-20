import json
import unittest
from rdflib.namespace import FOAF

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.convention import MetadataModel
# noinspection PyUnresolvedReferences
from h5rdmtoolbox.extensions import normalize, vector, magnitude


class TestExtension(unittest.TestCase):

    def test_metadata_modelling(self):
        user_model = {
            '@context': {
                'foaf': 'http://xmlns.com/foaf/0.1/',
                # 'first_name': str(FOAF.firstName),
                # 'last_name': str(FOAF.lastName)
                'first_name': 'foaf:firstName',
                'last_name': 'foaf:lastName'
            },
            '@type': str(FOAF.Person),
            'orcidid': ['str', None],  # syntax: [TYPE, DEFAULT]
            'first_name': 'str',
            'last_name': 'str',
            'interests': ['Union[str, List[str]]', 'programming'],
            'age': 'PositiveInt',
            'mailbox': ['EmailStr', None],
            'website': ['HttpUrl', None]
        }
        fname = h5tbx.utils.generate_temporary_filename(suffix='.json')
        with open(fname, 'w') as f:
            json.dump(user_model, f, indent=4)

        # # sanity check check:
        # with open(fname) as f:
        #     pprint(json.load(f))

        UserName = MetadataModel.from_json(fname, 'UserName')
        john_doe = UserName(first_name='John', last_name='Doe', age=32, orcidid='https://orcid.org/0000-0001-8729-0482')
        self.assertEqual(john_doe.first_name, 'John')
        self.assertEqual(john_doe.last_name, 'Doe')
        self.assertEqual(john_doe.age, 32)
        self.assertEqual(john_doe.orcidid, 'https://orcid.org/0000-0001-8729-0482')
