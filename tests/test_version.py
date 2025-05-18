import pathlib
import unittest

from h5rdmtoolbox import __version__, get_package_meta

__this_dir__ = pathlib.Path(__file__).parent


class TestVersion(unittest.TestCase):

    def test_version(self):
        this_version = 'x.x.x'
        setupcfg_filename = __this_dir__ / '../setup.cfg'
        with open(setupcfg_filename, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if 'version' in line:
                    this_version = line.split(' = ')[-1].strip()
        self.assertEqual(__version__, this_version)

    def test_codemeta(self):
        """checking if the version in codemeta.json is the same as the one of the toolbox"""

        codemeta = get_package_meta()

        assert codemeta['version'] == __version__

    def test_colab_version(self):
        """open colab jupyter notebook and check first cell for version"""
        with open(__this_dir__ / '../docs' / 'colab' / 'quickstart.ipynb') as f:
            lines = f.readlines()

        found = False
        for line in lines:
            if 'pip install' in line:
                self.assertEqual(line.strip(), f'"# !pip install h5rdmtoolbox=={__version__}"')
                found = True
                break
        self.assertTrue(found)

    def test_citation_cff(self):
        citation_cff = __this_dir__ / "../CITATION.cff"
        import yaml
        with open(citation_cff, 'r') as f:
            cff = yaml.safe_load(f)
        self.assertTrue("todo" not in cff["doi"].lower(), "Please replace 'todo' in CITATION.cff")

    def test_citation_cff_version(self):
        """checking if the version in CITATION.cff is the same as the one of the h5rdmtoolbox"""
        this_version = 'x.x.x'
        setupcfg_filename = __this_dir__ / '../CITATION.cff'
        with open(setupcfg_filename, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if 'version: ' in line:
                    this_version = line.split(':')[-1].strip()
        self.assertEqual(__version__, this_version)