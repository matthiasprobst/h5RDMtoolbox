import pathlib
import unittest

import yaml

from h5rdmtoolbox import __version__, get_package_meta

__this_dir__ = pathlib.Path(__file__).parent

def parse_to_py_version(vstr):
    """Parse a version string and return a standardized version string.
    e.g. removes -rc.X to rcX
    """
    vstr = vstr.replace('-rc.', 'rc')
    return vstr

class TestVersion(unittest.TestCase):

    def test_version(self):
        this_version = 'x.x.x'
        setupcfg_filename = __this_dir__ / '../setup.cfg'
        with open(setupcfg_filename, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if 'version' in line:
                    this_version = parse_to_py_version(line.split(' = ')[-1].strip())
        self.assertEqual(__version__, this_version)

    def test_codemeta(self):
        """checking if the version in codemeta.json is the same as the one of the toolbox"""

        codemeta = get_package_meta()

        assert parse_to_py_version(codemeta['version']) == __version__

    def test_colab_version(self):
        """open colab jupyter notebook and check first cell for version"""
        with open(__this_dir__ / '../docs' / 'colab' / 'quickstart.ipynb') as f:
            lines = f.readlines()

        found = False
        for line in lines:
            if 'pip install' in line:
                self.assertTrue(f'"# !pip install h5rdmtoolbox=={__version__}"' in line.strip())
                found = True
                break
        self.assertTrue(found)

    def test_citation_cff(self):
        citation_cff = __this_dir__ / "../CITATION.cff"
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
                    this_version = parse_to_py_version(line.split(':')[-1].strip())
                # elif 'date-released:' in line:
                #     # check if the date is the same as the one in codemeta.json
                #     date_str = line.split(':')[-1].strip()
                #     dt = datetime.strptime(date_str, '%Y-%m-%d')
        self.assertEqual(__version__, this_version)
        # self.assertEqual(dt.strftime('%Y-%m-%d'), datetime.now().date().strftime('%Y-%m-%d'))
