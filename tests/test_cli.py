import unittest

from click.testing import CliRunner

from h5rdmtoolbox import File
from h5rdmtoolbox.cli import h5tbx


class TestCLI(unittest.TestCase):

    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(h5tbx, input='--help\n')

        self.assertIsNone(result.exception)
        self.assertEqual(result.output,
                         """Usage: h5tbx [OPTIONS] COMMAND [ARGS]...

Options:
  --fairify PATH  Starts the app helping you to make the file FAIRer
  --help          Show this message and exit.

Commands:
  ld  Linked-Data command
""")

    def test_command_ld(self):
        runner = CliRunner()
        result = runner.invoke(h5tbx, ["ld", "--help"])
        self.assertIsNone(result.exception)
        self.assertEqual(result.output,
                         """Usage: h5tbx ld [OPTIONS] FILENAME

  Linked-Data command

Options:
  -o, --output PATH  Filename to write the JSON-LD data to.
  --format TEXT      The output format, e.g. jsonld.
  --graph            Generates a graph and stores it in OUTPUT-graph.html. Uses
                     pyvis and kglab. Please Make sure it is installed
  --help             Show this message and exit.
""")

    def test_ld_dump(self):
        with File() as h5:
            pass
        runner = CliRunner()
        result = runner.invoke(h5tbx, ["ld", f"{h5.hdf_filename}"])
        self.assertIsNone(result.exception)
        expected = """@prefix hdf5: <http://purl.allotrope.org/ontologies/hdf5/1.8#> .

[] a hdf5:File ;
    hdf5:rootGroup [ a hdf5:Group ;
            hdf5:name "/" ] .


"""
        self.assertEqual(
            expected,
            result.output
        )
