import json
import logging
import os
import pathlib
import shutil
import unittest
from datetime import datetime

import pydantic
import requests

import rdflib
import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import UserDir
from h5rdmtoolbox.repository import upload_file
from h5rdmtoolbox.repository import zenodo
from h5rdmtoolbox.repository.interface import RepositoryFile
from h5rdmtoolbox.repository.zenodo.metadata import Metadata, Creator, Contributor
from h5rdmtoolbox.repository.zenodo.tokens import get_api_token, set_api_token
from h5rdmtoolbox.tutorial import TutorialSNTZenodoRecordID
from h5rdmtoolbox.user import USER_DATA_DIR

logger = logging.getLogger(__name__)


class TestZenodo(unittest.TestCase):

    def setUp(self):
        # backup zenodo.ini
        zenodo_ini_filename = UserDir['repository'] / 'zenodo.ini'
        if zenodo_ini_filename.exists():
            shutil.copy(zenodo_ini_filename, UserDir['repository'] / '__test_backup__ini_file__')

    def tearDown(self):
        # restore zenodo.ini
        zenodo_ini_filename = UserDir['repository'] / 'zenodo.ini'
        bak_ini_filename = UserDir['repository'] / '__test_backup__ini_file__'
        if bak_ini_filename.exists():
            shutil.copy(bak_ini_filename, zenodo_ini_filename)
            bak_ini_filename.unlink()

    def test_zenodo_from_url(self):
        z = zenodo.ZenodoRecord("https://zenodo.org/records/10428817")
        self.assertEqual(str(z.rec_id), "10428817")
        z = zenodo.ZenodoRecord("https://doi.org/10.5281/zenodo.10428817")
        self.assertEqual(str(z.rec_id), "10428817")
        z = zenodo.ZenodoRecord(10428817)
        self.assertEqual(str(z.rec_id), "10428817")

    def test_zenodo_export(self):
        z = zenodo.ZenodoRecord(10428817)
        fname = z.export(fmt='dcat-ap')
        self.assertIsInstance(fname, pathlib.Path)
        self.assertTrue(fname.exists())

        self.assertIsInstance(z.get_jsonld(), str)
        print(z.get_jsonld())

    def test_ZenodoFile(self):
        z = zenodo.ZenodoRecord(TutorialSNTZenodoRecordID)  # an existing repo
        self.assertDictEqual(z._cached_json, {})
        z.refresh()
        self.assertNotEqual(z._cached_json, {})

        self.assertTrue(z.exists())
        for file in z.files.values():
            self.assertIsInstance(file, RepositoryFile)
        self.assertEqual(len(z.files), 1)
        for file in z.files.values():
            r = requests.get(file.download_url)
            self.assertEqual(r.status_code, 200)
            downloaded_filename = file.download()
            self.assertTrue(downloaded_filename.exists())
            self.assertTrue(downloaded_filename.is_file())
            self.assertIsInstance(file.jsonld(), str)

    def test_newSandboxImplementation(self):
        """from 1.4.0 on the sandbox can be init from ZenodoRecord"""
        z = zenodo.ZenodoRecord(TutorialSNTZenodoRecordID, sandbox=True)
        self.assertTrue(z.sandbox)
        self.assertEqual(z.base_url, 'https://sandbox.zenodo.org')

    def test_ZenodoRecord_without_token(self):
        """remove all info about zenodo api token!"""
        curr_zenodo_api_token = os.environ.pop('ZENODO_API_TOKEN', None)

        zenodo_ini_filename = UserDir['repository'] / 'zenodo.ini'

        if zenodo_ini_filename.exists():
            (UserDir['repository'] / 'zenodo.ini.tmpbak').unlink(missing_ok=True)
            zenodo_ini_filename.rename(UserDir['repository'] / 'zenodo.ini.tmpbak')

        zenodo_repo = zenodo.ZenodoRecord(TutorialSNTZenodoRecordID)
        self.assertTrue(zenodo_repo.access_token is None)
        self.assertTrue(zenodo_repo.exists())

        if curr_zenodo_api_token is not None:
            os.environ['ZENODO_API_TOKEN'] = curr_zenodo_api_token
        if (UserDir['repository'] / 'zenodo.ini.tmpbak').exists():
            (UserDir['repository'] / 'zenodo.ini.tmpbak').rename(UserDir['repository'] / 'zenodo.ini')

    def test_creator(self):
        from h5rdmtoolbox.repository.zenodo.metadata import Creator
        with self.assertRaises(ValueError):
            creator = Creator(name='John Doe', affiliation='University of Nowhere')
        creator = Creator(name='Doe, John')
        self.assertEqual(creator.name, 'Doe, John')
        with self.assertRaises(pydantic.ValidationError):
            Creator(affiliation='University of Nowhere')

    def test_metadata(self):
        from h5rdmtoolbox.repository.zenodo.metadata import Metadata, Creator
        metadata = Metadata(version='0.1.0-rc.1+build.1',
                            title='h5rdmtoolbox',
                            description='A toolbox for managing HDF5-based research data management',
                            creators=[Creator(name='Doe, John', affiliation='University of Nowhere')],
                            keywords=['hdf5', 'research data management', 'rdm'],
                            upload_type='publication',
                            publication_type='other',
                            access_right='open',
                            publication_date=datetime.now())
        self.assertEqual(metadata.version, '0.1.0-rc.1+build.1')
        self.assertEqual(metadata.title, 'h5rdmtoolbox')
        self.assertEqual(metadata.description, 'A toolbox for managing HDF5-based research data management')
        self.assertEqual(metadata.creators[0].name, 'Doe, John')
        self.assertEqual(metadata.creators[0].affiliation, 'University of Nowhere')
        self.assertEqual(metadata.contributors, [])
        self.assertEqual(metadata.keywords, ['hdf5', 'research data management', 'rdm'])
        self.assertEqual(metadata.upload_type, 'publication')
        self.assertEqual(metadata.publication_type, 'other')
        self.assertEqual(metadata.access_right, 'open')
        self.assertEqual(metadata.publication_date, datetime.today().strftime('%Y-%m-%d'))

        metadata = Metadata(version='0.1.0-rc.1+build.1',
                            title='h5rdmtoolbox',
                            description='A toolbox for managing HDF5-based research data management',
                            creators=[Creator(name='Doe, John', affiliation='University of Nowhere')],
                            keywords=['hdf5', 'research data management', 'rdm'],
                            upload_type='publication',
                            publication_type='other',
                            access_right='open',
                            publication_date='today')
        self.assertEqual(metadata.publication_date, datetime.today().strftime('%Y-%m-%d'))

        metadata = Metadata(version='0.1.0-rc.1+build.1',
                            title='h5rdmtoolbox',
                            description='A toolbox for managing HDF5-based research data management',
                            creators=[Creator(name='Doe, John', affiliation='University of Nowhere')],
                            keywords=['hdf5', 'research data management', 'rdm'],
                            upload_type='publication',
                            publication_type='other',
                            access_right='open',
                            publication_date='2023-01-01')
        self.assertEqual(metadata.publication_date, '2023-01-01')

        with self.assertRaises(ValueError):
            # wrong version
            metadata = Metadata(version='invalid',
                                title='h5rdmtoolbox',
                                description='A toolbox for managing HDF5-based research data management',
                                creators=[Creator(name='Doe, John', affiliation='University of Nowhere')],
                                keywords=['hdf5', 'research data management', 'rdm'],
                                upload_type='publication',
                                publication_type='other',
                                access_right='open',
                                publication_date='2023-01-01')

        with self.assertRaises(ValueError):
            # invalid embargo date
            metadata = Metadata(version='0.1.0-rc.1+build.1',
                                title='h5rdmtoolbox',
                                description='A toolbox for managing HDF5-based research data management',
                                creators=[Creator(name='Doe, John', affiliation='University of Nowhere')],
                                keywords=['hdf5', 'research data management', 'rdm'],
                                upload_type='publication',
                                publication_type='other',
                                access_right='embargoed',
                                embargo_date='2022-01-01',  # too early!
                                publication_date='2023-01-01')

        # invalid embargo date format
        with self.assertRaises(ValueError):
            metadata = Metadata(version='0.1.0-rc.1+build.1',
                                title='h5rdmtoolbox',
                                description='A toolbox for managing HDF5-based research data management',
                                creators=[Creator(name='Doe, John', affiliation='University of Nowhere')],
                                keywords=['hdf5', 'research data management', 'rdm'],
                                upload_type='publication',
                                publication_type='other',
                                access_right='embargoed',
                                embargo_date='01-2022-01',  # wrong format!
                                publication_date='2023-01-01')

    def test_get_api(self):
        self.assertIsInstance(get_api_token(sandbox=True), str)

        from h5rdmtoolbox.repository.zenodo.tokens import _parse_ini_file
        fname = USER_DATA_DIR / 'zenodo.ini'
        if fname.exists():
            bak_fname = fname.rename(fname.with_suffix('.bak'))
        else:
            bak_fname = None

        zenodo_ini_filename = UserDir['repository'] / 'zenodo.ini'
        if zenodo_ini_filename.exists():
            tmp_zenodo_ini_filename = zenodo_ini_filename.rename(zenodo_ini_filename.with_suffix('.ini_bak'))
        else:
            tmp_zenodo_ini_filename = None

        self.assertEqual(_parse_ini_file(None), zenodo_ini_filename)

        self.assertEqual(_parse_ini_file('invalid.ini'), pathlib.Path('invalid.ini'))

        if bak_fname:
            bak_fname.rename(fname)

        tmp_ini_file = h5tbx.utils.generate_temporary_filename(suffix='.ini', touch=True)
        ini_filename = _parse_ini_file(tmp_ini_file)
        self.assertEqual(ini_filename, tmp_ini_file)
        self.assertTrue(ini_filename.exists())
        ini_filename.unlink()

        if tmp_zenodo_ini_filename:
            tmp_zenodo_ini_filename.rename(tmp_zenodo_ini_filename.with_suffix('.ini'))

    def test_get_api_token(self):
        env_token_sb = os.environ.pop('ZENODO_SANDBOX_API_TOKEN', None)
        env_token = os.environ.pop('ZENODO_API_TOKEN', None)
        test_ini_filename = pathlib.Path(__file__).parent / 'test.ini'
        self.assertEqual(get_api_token(sandbox=True, zenodo_ini_filename=test_ini_filename), '123')
        self.assertEqual(get_api_token(sandbox=False, zenodo_ini_filename=test_ini_filename), '456')

        os.environ['ZENODO_SANDBOX_API_TOKEN'] = 'abc'
        self.assertEqual(get_api_token(sandbox=True, zenodo_ini_filename=test_ini_filename), 'abc')

        os.environ['ZENODO_API_TOKEN'] = 'def'
        self.assertEqual('def', os.environ.get('ZENODO_API_TOKEN', None))
        self.assertEqual(get_api_token(sandbox=False, zenodo_ini_filename=test_ini_filename), 'def')
        os.environ.pop('ZENODO_API_TOKEN', None)

        # reset environment variable
        if env_token_sb is not None:
            os.environ['ZENODO_SANDBOX_API_TOKEN'] = env_token_sb
            self.assertEqual(env_token_sb, os.environ.get('ZENODO_SANDBOX_API_TOKEN', None))
        else:
            os.environ.pop('ZENODO_SANDBOX_API_TOKEN')

        if env_token is not None:
            os.environ['ZENODO_API_TOKEN'] = env_token
        else:
            os.environ.pop('ZENODO_API_TOKEN', None)
        self.assertEqual(env_token, os.environ.get('ZENODO_API_TOKEN', None))

    def test_set_api_token(self):

        env_token_sb = os.environ.pop('ZENODO_SANDBOX_API_TOKEN', None)
        env_token = os.environ.pop('ZENODO_API_TOKEN', None)

        ini_filename = h5tbx.utils.generate_temporary_filename(suffix='.ini', touch=False)
        # with self.assertRaises(FileNotFoundError):
        set_api_token(sandbox=True,
                      access_token='321',
                      zenodo_ini_filename=ini_filename)
        ini_filename = h5tbx.utils.generate_temporary_filename(suffix='.ini', touch=False)
        with open(ini_filename, 'w') as f:
            pass
        set_api_token(sandbox=True,
                      access_token='321',
                      zenodo_ini_filename=ini_filename)
        t = get_api_token(sandbox=True, zenodo_ini_filename=ini_filename)
        self.assertEqual(t, '321')

        set_api_token(sandbox=False,
                      access_token='321123',
                      zenodo_ini_filename=ini_filename)
        t = get_api_token(sandbox=False, zenodo_ini_filename=ini_filename)
        self.assertEqual(t, '321123')

        if env_token_sb is not None:
            os.environ['ZENODO_SANDBOX_API_TOKEN'] = env_token_sb
        self.assertEqual(env_token_sb, os.environ.get('ZENODO_SANDBOX_API_TOKEN', None))
        if env_token is not None:
            os.environ['ZENODO_API_TOKEN'] = env_token

    def test_upload_hdf(self):
        z = zenodo.ZenodoSandboxDeposit(None)

        with h5tbx.File() as h5:
            h5.attrs['long_name'] = 'root'
            h5.create_dataset('test', data=1, attrs={'units': 'm/s', 'long_name': 'dataset 1'})
            h5.create_dataset('grp1/test2', data=2, attrs={'test': 1, 'long_name': 'dataset 2'})

            orig_hdf_filename = h5.hdf_filename

        hdf_file_name = orig_hdf_filename.name
        json_name = hdf_file_name.replace('.hdf', '.jsonld')

        z.upload_file(orig_hdf_filename)  # metamapper per default converts to JSONLD file
        filenames = z.get_filenames()
        self.assertIn(hdf_file_name, filenames)
        self.assertIn(json_name, filenames)

        self.assertEqual(z.files.get('invalid.hdf'), None)

        hdf_filenames = [f for f in z.get_filenames() if pathlib.Path(f).suffix == '.hdf']
        self.assertEqual(len(hdf_filenames), 1)

        hdf_filename = z.files.get(hdf_file_name).download()

        self.assertTrue(hdf_filename.exists())

        with h5tbx.File(hdf_filename) as h5:
            self.assertEqual(h5.attrs['long_name'], 'root')
            self.assertEqual(h5['test'].attrs['units'], 'm/s')
            self.assertEqual(h5['test'].attrs['long_name'], 'dataset 1')
            self.assertEqual(h5['grp1/test2'].attrs['test'], 1)
            self.assertEqual(h5['grp1/test2'].attrs['long_name'], 'dataset 2')

        self.assertEqual(z.files.get(json_name).suffix, '.jsonld')
        json_filename = z.files.get(json_name).download()
        self.assertTrue(json_filename.exists())

        graph = rdflib.Graph().parse(source=json_filename, format='json-ld')
        query = """
        PREFIX schema: <http://schema.org/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#>
        
        SELECT ?name
        WHERE {
            ?s rdf:type hdf:Group .
            ?s hdf:name ?name .
}"""
        res = graph.query(query)
        group_names = [str(row[rdflib.Variable("name")]) for row in res.bindings]
        self.assertEqual(
            sorted(["/", "/grp1"]),
            sorted(group_names)
        )

    def test_upload_hdf_new_implementation(self):
        z = zenodo.ZenodoRecord(None, sandbox=True)

        with h5tbx.File() as h5:
            h5.attrs['long_name'] = 'root'
            h5.create_dataset('test', data=1, attrs={'units': 'm/s', 'long_name': 'dataset 1'})
            h5.create_dataset('grp1/test2', data=2, attrs={'test': 1, 'long_name': 'dataset 2'})

            orig_hdf_filename = h5.hdf_filename

        hdf_file_name = orig_hdf_filename.name
        json_name = hdf_file_name.replace('.hdf', '.jsonld')

        z.upload_file(orig_hdf_filename)  # metamapper per default converts to JSONLD file
        filenames = z.get_filenames()
        self.assertIn(hdf_file_name, filenames)
        self.assertIn(json_name, filenames)

        self.assertEqual(z.files.get('invalid.hdf'), None)

        hdf_filenames = [f for f in z.get_filenames() if pathlib.Path(f).suffix == '.hdf']
        self.assertEqual(len(hdf_filenames), 1)

        hdf_filename = z.files.get(hdf_file_name).download()

        self.assertTrue(hdf_filename.exists())

        with h5tbx.File(hdf_filename) as h5:
            self.assertEqual(h5.attrs['long_name'], 'root')
            self.assertEqual(h5['test'].attrs['units'], 'm/s')
            self.assertEqual(h5['test'].attrs['long_name'], 'dataset 1')
            self.assertEqual(h5['grp1/test2'].attrs['test'], 1)
            self.assertEqual(h5['grp1/test2'].attrs['long_name'], 'dataset 2')

        json_filename = z.files.get(json_name).download()
        self.assertTrue(json_filename.exists())
        with open(json_filename) as f:
            json_dict = json.loads(f.read())

        self.assertTrue('@context' in json_dict)

        graph = rdflib.Graph().parse(source=json_filename, format='json-ld')
        query = """
        PREFIX schema: <http://schema.org/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#>
        
        SELECT ?name
        WHERE {
            ?s rdf:type hdf:Group .
            ?s hdf:name ?name .
}"""
        res = graph.query(query)
        group_names = [str(row[rdflib.Variable("name")]) for row in res.bindings]
        self.assertEqual(
            sorted(["/", "/grp1"]),
            sorted(group_names)
        )

    def test_ZenodoSandboxDeposit(self):
        z = zenodo.ZenodoSandboxDeposit(None)
        self.assertIsInstance(z.get_metadata(), dict)
        self.assertEqual(z.get_doi(), f'10.5281/zenodo.{z.rec_id}')
        self.assertIn('access_right', z.get_metadata())
        self.assertIn('prereserve_doi', z.get_metadata())
        self.assertEqual('open', z.get_metadata()['access_right'])
        self.assertEqual(z.rec_id, z.get_metadata()['prereserve_doi']['recid'])
        self.assertFalse(z.exists())  # not yet published!
        self.assertFalse(z.is_published())
        self.assertEqual(z.title, 'No title')

        old_rec_id = z.rec_id

        # z.delete()

        with self.assertRaises(ValueError):
            _ = zenodo.ZenodoSandboxDeposit('123123123123')

        z = zenodo.ZenodoSandboxDeposit(None)
        self.assertNotEqual(old_rec_id, z.rec_id)

        # with self.assertRaises(TypeError):
        #     z.metadata = {'access_right': 'closed'}

        meta = Metadata(
            version="0.1.0-rc.1+build.1",
            title='[deleteme]h5tbxZenodoInterface',
            description='A toolbox for managing HDF5-based research data management',
            creators=[Creator(name="Probst, Matthias",
                              affiliation="KIT - ITS",
                              orcid="0000-0001-8729-0482")],
            contributors=[Contributor(name="Probst, Matthias",
                                      affiliation="KIT - ITS",
                                      orcid="0000-0001-8729-0482",
                                      type="ContactPerson")],
            upload_type='image',
            image_type='photo',
            access_right='open',
            keywords=['hdf5', 'research data management', 'rdm'],
            publication_date=datetime.now(),
            embargo_date='2020'
        )

        with self.assertRaises(TypeError):
            z.set_metadata(12)

        z.set_metadata(meta.model_dump())
        z.set_metadata(meta)
        ret_metadata = z.get_metadata()
        self.assertEqual(ret_metadata['upload_type'],
                         meta.model_dump()['upload_type'])
        self.assertListEqual(ret_metadata['keywords'],
                             meta.model_dump()['keywords'])

        # add file:
        tmpfile = pathlib.Path('testfile.txt')
        with open(tmpfile, 'w') as f:
            f.write('This is a test file.')

        with self.assertRaises(FileNotFoundError):
            z.upload_file('doesNotExist.txt', overwrite=True, metamapper=None)

        z.upload_file(tmpfile, overwrite=True, metamapper=None)
        self.assertIn('testfile.txt', z.get_filenames())

        with self.assertWarns(UserWarning):
            z.upload_file('testfile.txt', overwrite=False, metamapper=None)

        upload_file(z, tmpfile, overwrite=True, metamapper=None)

        with self.assertWarns(UserWarning):
            upload_file(z, tmpfile, overwrite=False, metamapper=None)

        # delete file locally:
        tmpfile.unlink()
        self.assertFalse(tmpfile.exists())

        filename = z.download_file('testfile.txt')
        self.assertIsInstance(filename, pathlib.Path)
        self.assertTrue(filename.exists())
        with open(filename, 'r') as f:
            self.assertEqual(f.read(), 'This is a test file.')
        filename.unlink()

        filenames = z.download_files()

        self.assertIsInstance(filenames, list)
        self.assertIsInstance(filenames[0], pathlib.Path)
        for filename in filenames:
            self.assertTrue(filename.exists())
            filename.unlink()

        hdf5_filenames = [file.download() for file in z.files.values() if file.suffix == '.hdf']
        with self.assertWarns(DeprecationWarning):
            z.download_files(suffix='.hdf')
        self.assertIsInstance(hdf5_filenames, list)
        self.assertEqual(len(hdf5_filenames), 0)

        txt_filenames = z.download_files(suffix='.txt')
        self.assertIsInstance(txt_filenames, list)
        self.assertEqual(len(txt_filenames), 1)
        self.assertEqual(txt_filenames[0].suffix, '.txt')

        hdf_and_txt_filenames = z.download_files(suffix=['.txt', '.hdf'])
        self.assertIsInstance(hdf_and_txt_filenames, list)
        self.assertEqual(len(hdf_and_txt_filenames), 1)
        self.assertEqual(hdf_and_txt_filenames[0].suffix, '.txt')

        self.assertFalse(z.exists())
        # z.delete()
        # self.assertFalse(z.exists())

    def test_ZenodoSandboxDeposit_newImplementation(self):
        z = zenodo.ZenodoRecord(None, sandbox=True)
        self.assertIsInstance(z.get_metadata(), dict)
        self.assertEqual(z.get_doi(), f'10.5281/zenodo.{z.rec_id}')
        self.assertIn('access_right', z.get_metadata())
        self.assertIn('prereserve_doi', z.get_metadata())
        self.assertEqual('open', z.get_metadata()['access_right'])
        self.assertEqual(z.rec_id, z.get_metadata()['prereserve_doi']['recid'])
        self.assertFalse(z.exists())  # not yet published!
        self.assertFalse(z.is_published())

        old_rec_id = z.rec_id

        # z.delete()

        with self.assertRaises(ValueError):
            _ = zenodo.ZenodoRecord('123123123123', sandbox=True)

        z = zenodo.ZenodoRecord(None, sandbox=True)
        self.assertNotEqual(old_rec_id, z.rec_id)

        # with self.assertRaises(TypeError):
        #     z.metadata = {'access_right': 'closed'}

        meta = Metadata(
            version="0.1.0-rc.1+build.1",
            title='[deleteme]h5tbxZenodoInterface',
            description='A toolbox for managing HDF5-based research data management',
            creators=[Creator(name="Probst, Matthias",
                              affiliation="KIT - ITS",
                              orcid="0000-0001-8729-0482")],
            contributors=[Contributor(name="Probst, Matthias",
                                      affiliation="KIT - ITS",
                                      orcid="0000-0001-8729-0482",
                                      type="ContactPerson")],
            upload_type='image',
            image_type='photo',
            access_right='open',
            keywords=['hdf5', 'research data management', 'rdm'],
            publication_date=datetime.now(),
            embargo_date='2020'
        )

        with self.assertRaises(TypeError):
            z.set_metadata(12)

        z.set_metadata(meta.model_dump())
        z.set_metadata(meta)
        ret_metadata = z.get_metadata()
        self.assertEqual(ret_metadata['upload_type'],
                         meta.model_dump()['upload_type'])
        self.assertListEqual(ret_metadata['keywords'],
                             meta.model_dump()['keywords'])

        # add file:
        tmpfile = pathlib.Path('testfile.txt')
        with open(tmpfile, 'w') as f:
            f.write('This is a test file.')

        with self.assertRaises(FileNotFoundError):
            z.upload_file('doesNotExist.txt', overwrite=True, metamapper=None)

        z.upload_file(tmpfile, overwrite=True, metamapper=None)
        self.assertIn('testfile.txt', z.get_filenames())

        with self.assertWarns(UserWarning):
            z.upload_file('testfile.txt', overwrite=False, metamapper=None)

        upload_file(z, tmpfile, overwrite=True, metamapper=None)

        with self.assertWarns(UserWarning):
            upload_file(z, tmpfile, overwrite=False, metamapper=None)

        # delete file locally:
        tmpfile.unlink()
        self.assertFalse(tmpfile.exists())

        filename = z.download_file('testfile.txt')
        self.assertIsInstance(filename, pathlib.Path)
        self.assertTrue(filename.exists())
        with open(filename, 'r') as f:
            self.assertEqual(f.read(), 'This is a test file.')
        filename.unlink()

        filenames = z.download_files()

        self.assertIsInstance(filenames, list)
        self.assertIsInstance(filenames[0], pathlib.Path)
        for filename in filenames:
            self.assertTrue(filename.exists())
            filename.unlink()

        hdf5_filenames = z.download_files(suffix='.hdf')
        self.assertIsInstance(hdf5_filenames, list)
        self.assertEqual(len(hdf5_filenames), 1)

        txt_filenames = z.download_files(suffix='.txt')
        self.assertIsInstance(txt_filenames, list)
        self.assertEqual(len(txt_filenames), 1)
        self.assertEqual(txt_filenames[0].suffix, '.txt')

        hdf_and_txt_filenames = z.download_files(suffix=['.txt', '.hdf'])
        self.assertIsInstance(hdf_and_txt_filenames, list)
        self.assertEqual(len(hdf_and_txt_filenames), 1)
        self.assertEqual(hdf_and_txt_filenames[0].suffix, '.txt')

        self.assertFalse(z.exists())
        # z.delete()
        # self.assertFalse(z.exists())
