import logging
import pathlib
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.convention.errors import StandardAttributeError

logger = logging.getLogger('h5rdmtoolbox')
# setting logger to debug:
logger.setLevel('DEBUG')
__this_dir__ = pathlib.Path(__file__).parent


class TestEngMeta(unittest.TestCase):

    def test_engmeta(self):
        cv = h5tbx.convention.from_yaml(__this_dir__ / 'EngMeta.yaml')
        cv.register()

        contact = cv.registered_standard_attributes['contact']

        self.assertTrue(contact.validate(
            {'name': 'Matthias Probst',
             'id': 'https://orcid.org/0000-0001-8729-0482',
             'role': 'Researcher'}
        )
        )

        self.assertTrue(contact.validate(None))

        self.assertFalse(contact.validate(
            {'name': 'Matthias Probst',
             'role': 'Invalid Role'}
        )
        )

        with h5tbx.use(cv):
            with h5tbx.File(contact=dict(name='Matthias Probst'),
                            creator=dict(name='Matthias Probst',
                                         id='https://orcid.org/0000-0001-8729-0482',
                                         role='Researcher'
                                         ),
                            pid=dict(id='123', type='other'),
                            title='Test file to demonstrate usage of EngMeta schema') as h5:
                pass

            with self.assertRaises(StandardAttributeError):
                with h5tbx.File(contact=dict(name=1.45),
                                creator=dict(name='Matthias Probst',
                                             id='https://orcid.org/0000-0001-8729-0482',
                                             role='Researcher'
                                             ),
                                pid=dict(id='123', type='other'),
                                title='Test file to demonstrate usage of EngMeta schema') as h5:
                    pass
