import json
import logging
import os
import pathlib
import shutil
import sys
import unittest
from datetime import datetime

import pydantic
import rdflib
import requests
from ontolutils.ex import dcat

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import UserDir
from h5rdmtoolbox.repository import upload_file
from h5rdmtoolbox.repository import zenodo
from h5rdmtoolbox.repository.interface import RepositoryFile
from h5rdmtoolbox.repository.zenodo.core import _bump_version
from h5rdmtoolbox.repository.zenodo.metadata import Metadata, Creator, Contributor
from h5rdmtoolbox.repository.zenodo.tokens import get_api_token, set_api_token
from h5rdmtoolbox.tutorial import TutorialSNTZenodoRecordID
from h5rdmtoolbox.user import USER_DATA_DIR

logger = logging.getLogger(__name__)


def get_python_version():
    """Get the current Python version as a tuple."""
    return sys.version_info.major, sys.version_info.minor, sys.version_info.micro


TESTING_VERSIONS = (9, 13)


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

    @unittest.skipUnless(get_python_version()[1] in TESTING_VERSIONS,
                         reason="Nur auf Python 3.9 und 3.13 testen")
    def test_zenodo_from_url(self):
        z = zenodo.ZenodoRecord("https://zenodo.org/records/10428817")
        self.assertEqual(str(z.rec_id), "10428817")
        z = zenodo.ZenodoRecord("https://doi.org/10.5281/zenodo.10428817")
        self.assertEqual(str(z.rec_id), "10428817")
        z = zenodo.ZenodoRecord(10428817)
        self.assertEqual(str(z.rec_id), "10428817")

    @unittest.skipUnless(get_python_version()[1] in TESTING_VERSIONS,
                         reason="Nur auf Python 3.9 und 3.13 testen")
    def test_zenodo_export(self):
        z = zenodo.ZenodoRecord(10428817)
        fname = z.export(fmt='dcat-ap')
        self.assertIsInstance(fname, pathlib.Path)
        self.assertTrue(fname.exists())

        self.assertIsInstance(z.get_jsonld(), str)
        rdflib.Graph().parse(data=json.loads(z.get_jsonld()), format="json-ld")  # should not raise an error

    @unittest.skipUnless(get_python_version()[1] in TESTING_VERSIONS,
                         reason="Nur auf Python 3.9 und 3.13 testen")
    def test_ZenodoFile(self):
        z = zenodo.ZenodoRecord(TutorialSNTZenodoRecordID)  # an existing repo
        self.assertDictEqual(z._cached_json, {})

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

    @unittest.skipUnless(get_python_version()[1] in TESTING_VERSIONS,
                         reason="Nur auf Python 3.9 und 3.13 testen")
    def test_newSandboxImplementation(self):
        """from 1.4.0 on the sandbox can be init from ZenodoRecord"""
        z = zenodo.ZenodoRecord(TutorialSNTZenodoRecordID, sandbox=True)
        self.assertTrue(z.sandbox)
        self.assertEqual(z.base_url, 'https://sandbox.zenodo.org')

    @unittest.skipUnless(get_python_version()[1] in TESTING_VERSIONS,
                         reason="Nur auf Python 3.9 und 3.13 testen")
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

    @unittest.skipUnless(get_python_version()[1] in TESTING_VERSIONS,
                         reason="Nur auf Python 3.9 und 3.13 testen")
    def test_creator(self):
        from h5rdmtoolbox.repository.zenodo.metadata import Creator
        with self.assertRaises(ValueError):
            _ = Creator(name='John Doe', affiliation='University of Nowhere')
        creator = Creator(name='Doe, John')
        self.assertEqual(creator.name, 'Doe, John')
        with self.assertRaises(pydantic.ValidationError):
            Creator(affiliation='University of Nowhere')

    @unittest.skipUnless(get_python_version()[1] in TESTING_VERSIONS,
                         reason="Nur auf Python 3.9 und 3.13 testen")
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
            _ = Metadata(version='invalid',
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
            _ = Metadata(version='0.1.0-rc.1+build.1',
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
            _ = Metadata(version='0.1.0-rc.1+build.1',
                         title='h5rdmtoolbox',
                         description='A toolbox for managing HDF5-based research data management',
                         creators=[Creator(name='Doe, John', affiliation='University of Nowhere')],
                         keywords=['hdf5', 'research data management', 'rdm'],
                         upload_type='publication',
                         publication_type='other',
                         access_right='embargoed',
                         embargo_date='01-2022-01',  # wrong format!
                         publication_date='2023-01-01')

    @unittest.skipUnless(get_python_version()[1] in TESTING_VERSIONS,
                         reason="Nur auf Python 3.9 und 3.13 testen")
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

    @unittest.skipUnless(get_python_version()[1] in TESTING_VERSIONS,
                         reason="Nur auf Python 3.9 und 3.13 testen")
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

    @unittest.skipUnless(get_python_version()[1] in TESTING_VERSIONS,
                         reason="Nur auf Python 3.9 und 3.13 testen")
    def test_set_api_token(self):

        env_token_sb = os.environ.pop('ZENODO_SANDBOX_API_TOKEN', None)
        env_token = os.environ.pop('ZENODO_API_TOKEN', None)

        ini_filename = h5tbx.utils.generate_temporary_filename(suffix='.ini', touch=False)
        # with self.assertRaises(FileNotFoundError):
        set_api_token(sandbox=True,
                      access_token='321',
                      zenodo_ini_filename=ini_filename)
        ini_filename = h5tbx.utils.generate_temporary_filename(suffix='.ini', touch=False)
        with open(ini_filename, 'w'):
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

    def test_parse_to_dcat(self):
        record = zenodo.ZenodoRecord(source=15389242)
        ds = record.as_dcat_dataset()
        print(ds.serialize("ttl"))

    @unittest.skipUnless(get_python_version()[1] in TESTING_VERSIONS,
                         reason="Nur auf Python 3.9 und 3.13 testen")
    def test_new_version(self):
        z = zenodo.ZenodoRecord(source=None, sandbox=True)
        original_id = z.rec_id
        meta = Metadata(
            version="1.0.0",
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

        z.set_metadata(meta)

        with h5tbx.File() as h5:
            h5.create_dataset('test', data=1, attrs={'units': 'm/s', 'long_name': 'dataset 1'})

        z.upload_file(h5.hdf_filename)
        c_dataset = z.as_dcat_dataset()
        self.assertEqual(
            c_dataset.title,
            '[deleteme]h5tbxZenodoInterface'
        )

        dataset = z.publish()
        self.assertIsInstance(
            dataset,
            dcat.Dataset
        )
        ttl = dataset.serialize("ttl")

        c_dataset = z.as_dcat_dataset()
        self.assertEqual(ttl, c_dataset.serialize("ttl"))

        self.assertEqual(dataset.license, "https://creativecommons.org/licenses/by/4.0/")

        # print(dataset.serialize("ttl"))
        target_dir = pathlib.Path.cwd() / "deleteme-dir"
        if target_dir.exists():
            shutil.rmtree(target_dir)

        dataset.distribution[0].download(
            target_folder=target_dir
        )
        shutil.rmtree(target_dir)

        record_metadata = z.get_metadata()
        self.assertEqual(record_metadata['version'], "1.0.0")
        self.assertTrue(z.is_published())

        new_record = z.new_version("2.0.0")
        discarded_record = new_record.discard()
        self.assertEqual(discarded_record.rec_id, original_id)
        new_record = z.new_version("2.0.0")
        new_metadata = new_record.get_metadata()
        self.assertEqual(new_metadata['version'], "2.0.0")
        new_record.publish()
        self.assertTrue(new_record.is_published())

        with self.assertRaises(ValueError):
            z.new_version("2.0.0", increase_part="patch")
        # new_record.delete()

    @unittest.skipUnless(get_python_version()[1] in TESTING_VERSIONS,
                         reason="Nur auf Python 3.9 und 3.13 testen")
    def test__bump_version(self):
        self.assertEqual("3.0.0", _bump_version("2.0.0", "major"))
        self.assertEqual("2.1.0", _bump_version("2.0.0", "minor"))
        self.assertEqual("2.0.1", _bump_version("2.0.0", "patch"))
        with self.assertRaises(ValueError):
            self.assertEqual("3.0.0", _bump_version("2.0.0", "micro"))

    @unittest.skipUnless(get_python_version()[1] in TESTING_VERSIONS,
                         reason="Nur auf Python 3.9 und 3.13 testen")
    def test_upload_hdf(self):
        z = zenodo.ZenodoRecord(None, sandbox=True)

        with h5tbx.File() as h5:
            h5.attrs['long_name'] = 'root'
            h5.create_dataset('test', data=1, attrs={'units': 'm/s', 'long_name': 'dataset 1'})
            h5.create_dataset('grp1/test2', data=2, attrs={'test': 1, 'long_name': 'dataset 2'})

            orig_hdf_filename = h5.hdf_filename

        hdf_file_name = orig_hdf_filename.name
        json_name = hdf_file_name.replace('.hdf', '.jsonld')

        z.upload_file(orig_hdf_filename)  # metamapper per default converts to JSONLD file
        filenames = list(z.files.keys())
        self.assertIn(hdf_file_name, filenames)
        self.assertIn(json_name, filenames)

        self.assertEqual(z.files.get('invalid.hdf'), None)

        hdf_filenames = [f for f in z.files.keys() if pathlib.Path(f).suffix == '.hdf']
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

    @unittest.skipUnless(get_python_version()[1] in TESTING_VERSIONS,
                         reason="Nur auf Python 3.9 und 3.13 testen")
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
        filenames = list(z.files.keys())
        self.assertIn(hdf_file_name, filenames)
        self.assertIn(json_name, filenames)

        self.assertEqual(z.files.get('invalid.hdf'), None)

        hdf_filenames = [f for f in list(z.files.keys()) if pathlib.Path(f).suffix == '.hdf']
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

    @unittest.skipUnless(get_python_version()[1] in TESTING_VERSIONS,
                         reason="Nur auf Python 3.9 und 3.13 testen")
    def test_ZenodoSandboxDeposit(self):
        z = zenodo.ZenodoRecord(None, sandbox=True)
        self.assertIsInstance(z.get_metadata(), dict)
        self.assertEqual(z.get_doi(), f'10.5281/zenodo.{z.rec_id}')
        self.assertIn('access_right', z.get_metadata())
        self.assertIn('prereserve_doi', z.get_metadata())
        self.assertEqual('open', z.get_metadata()['access_right'])
        self.assertEqual(z.rec_id, z.get_metadata()['prereserve_doi']['recid'])
        self.assertTrue(z.exists())  # exists, but not yet published!
        self.assertFalse(z.is_published())
        self.assertEqual(z.title, 'No title')

        old_rec_id = z.rec_id

        # z.delete()

        with self.assertRaises(ValueError):
            _ = zenodo.ZenodoRecord("123123123123", sandbox=True)

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
            z.upload_file('doesNotExist.txt', metamapper=None)

        z.upload_file(tmpfile, metamapper=None)
        self.assertIn('testfile.txt', list(z.files.keys()))

        upload_file(z, tmpfile, metamapper=None)

        # delete file locally:
        tmpfile.unlink()
        self.assertFalse(tmpfile.exists())

        filename = z.files["testfile.txt"].download()
        self.assertIsInstance(filename, pathlib.Path)
        self.assertTrue(filename.exists())
        with open(filename, 'r') as f:
            self.assertEqual(f.read(), 'This is a test file.')
        filename.unlink()

        filenames = [f.download() for f in z.files.values()]

        self.assertIsInstance(filenames, list)
        self.assertIsInstance(filenames[0], pathlib.Path)
        for filename in filenames:
            self.assertTrue(filename.exists())
            filename.unlink()

        hdf5_filenames = [file.download() for file in z.files.values() if file.suffix == '.hdf']

        self.assertIsInstance(hdf5_filenames, list)
        self.assertEqual(len(hdf5_filenames), 0)

        txt_filenames = [f.download() for f in z.files.values() if f.suffix == ".txt"]
        self.assertIsInstance(txt_filenames, list)
        self.assertEqual(len(txt_filenames), 1)
        self.assertEqual(txt_filenames[0].suffix, '.txt')

        hdf_and_txt_filenames = [f.download() for f in z.files.values() if f.suffix in (".txt", "*.hdf")]
        self.assertIsInstance(hdf_and_txt_filenames, list)
        self.assertEqual(len(hdf_and_txt_filenames), 1)
        self.assertEqual(hdf_and_txt_filenames[0].suffix, '.txt')

        self.assertTrue(z.exists())
        z.delete()
        self.assertFalse(z.exists())

    @unittest.skipUnless(get_python_version()[1] in TESTING_VERSIONS,
                         reason="Nur auf Python 3.9 und 3.13 testen")
    def test_ZenodoSandboxDeposit_newImplementation(self):
        z = zenodo.ZenodoRecord(None, sandbox=True)
        self.assertIsInstance(z.get_metadata(), dict)
        self.assertEqual(z.get_doi(), f'10.5281/zenodo.{z.rec_id}')
        self.assertIn('access_right', z.get_metadata())
        self.assertIn('prereserve_doi', z.get_metadata())
        self.assertEqual('open', z.get_metadata()['access_right'])
        self.assertEqual(z.rec_id, z.get_metadata()['prereserve_doi']['recid'])
        self.assertTrue(z.exists())  # exists, but not yet published!
        self.assertFalse(z.is_published())

        old_rec_id = z.rec_id

        z.delete()

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
            z.upload_file('doesNotExist.txt', metamapper=None)

        z.upload_file(tmpfile, metamapper=None)
        self.assertIn('testfile.txt', list(z.files.keys()))

        upload_file(z, tmpfile, metamapper=None)

        # delete file locally:
        tmpfile.unlink()
        self.assertFalse(tmpfile.exists())

        filename = z.files["testfile.txt"].download()
        self.assertIsInstance(filename, pathlib.Path)
        self.assertTrue(filename.exists())
        with open(filename, 'r') as f:
            self.assertEqual(f.read(), 'This is a test file.')
        filename.unlink()

        filenames = [f.download() for f in z.files.values()]

        self.assertIsInstance(filenames, list)
        self.assertIsInstance(filenames[0], pathlib.Path)
        for filename in filenames:
            self.assertTrue(filename.exists())
            filename.unlink()

        hdf5_filenames = [f.download() for f in z.files.values() if f.suffix == '.hdf']
        self.assertIsInstance(hdf5_filenames, list)
        self.assertEqual(len(hdf5_filenames), 0)

        txt_filenames = [f.download() for f in z.files.values() if f.suffix == '.txt']
        self.assertIsInstance(txt_filenames, list)
        self.assertEqual(len(txt_filenames), 1)
        self.assertEqual(txt_filenames[0].suffix, '.txt')

        hdf_and_txt_filenames = [f.download() for f in z.files.values() if f.suffix in ('.txt', '.hdf')]
        self.assertIsInstance(hdf_and_txt_filenames, list)
        self.assertEqual(len(hdf_and_txt_filenames), 1)
        self.assertEqual(hdf_and_txt_filenames[0].suffix, '.txt')

        self.assertTrue(z.exists())
        z.delete()
        self.assertFalse(z.exists())

    def test_download_public_zenodo(self):
        z = zenodo.ZenodoRecord(17271932)
        ds = z.as_dcat_dataset()
        checksum_values = [dist.checksum.checksumValue for dist in ds.distribution]
        self.assertListEqual(
            sorted(['e88359a859c72af4eefd7734aa77483d',
                    'e23f2b98e4bfebacf5f3818208dcf1b6',
                    '075eeffcfb3008f7f62332cea0e69662']),
            sorted(checksum_values)
        )
