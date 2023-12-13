import requests
import unittest
from datetime import datetime

from h5rdmtoolbox.database.zenodo.config import get_api_token
from h5rdmtoolbox.database.zenodo.metadata import Creator, Contributor
from h5rdmtoolbox.database.zenodo.metadata import Metadata


class TestConfig(unittest.TestCase):

    def test_get_api(self):
        self.assertIsInstance(get_api_token(sandbox=True), str)

    def delete_sandbox_deposits(self):
        """Delete all deposits in the sandbox account."""
        r = requests.get(
            'https://sandbox.zenodo.org/api/deposit/depositions',
            params={'access_token': get_api_token(sandbox=True)}
        )
        for deposit in r.json():
            # if deposit['title'].startswith('[test]'):
            if not deposit['submitted']:
                print(f'deleting deposit {deposit["title"]} with id {deposit["id"]}')
                r = requests.delete(
                    'https://sandbox.zenodo.org/api/deposit/depositions/{}'.format(deposit['id']),
                    params={'access_token': get_api_token(sandbox=True)}
                )
                self.assertEqual(204, r.status_code)
            else:
                print(f'Cannot delete {deposit["title"]} with id {deposit["id"]} because it is already published."')

    def test_create_new_deposit(self):

        from h5rdmtoolbox.database.zenodo.deposit import ZenodoSandboxRecord

        meta = Metadata(
            version="0.1.0-rc.1+build.1",
            title='[test]h5tbxZenodoInterface',
            description='A toolbox for managing HDF5-based research data management',
            creators=[Creator(name="Probst, Matthias",
                              affiliation="KIT - ITS",
                              orcid="0000-0003-4423-4370")],
            contributors=[Contributor(name="Probst, Matthias",
                                      affiliation="KIT - ITS",
                                      orcid="0000-0003-4423-4370",
                                      type="ContactPerson")],
            upload_type='image',
            image_type='photo',
            access_right='open',
            keywords=['hdf5', 'research data management', 'rdm'],
            publication_date=datetime.now(),
            embargo_date='2020'
        )
        zsr = ZenodoSandboxRecord(deposit_id=None,
                                  metadata=meta)
        from h5rdmtoolbox import __version__
        zsr.metadata.notes = f'This is a test deposit created with h5tbx version {__version__}.'
        self.assertEqual(zsr.base_url, 'https://sandbox.zenodo.org/api/deposit/depositions')
        self.assertEqual(zsr.deposit_id, None)
        self.assertEqual(zsr.metadata, meta)
        self.assertFalse(zsr.exists())
        zsr.create()
        self.assertTrue(zsr.exists())
        zsr.delete()
        self.assertFalse(zsr.exists())

    def setUp(self) -> None:
        """Delete all deposits in the sandbox account."""
        if True:
            self.delete_sandbox_deposits()

    def tearDown(self) -> None:
        """Delete all deposits in the sandbox account."""
        if True:
            self.delete_sandbox_deposits()
