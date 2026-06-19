import unittest

from click.testing import CliRunner

from h5rdmtoolbox_cli import h5tbx


class TestCLI(unittest.TestCase):

    def test_entrypoint_help(self):
        runner = CliRunner()
        result = runner.invoke(h5tbx, ['--help'])

        self.assertIsNone(result.exception)
        self.assertIn("Usage: h5tbx [OPTIONS] COMMAND [ARGS]...", result.output)
        self.assertIn("ld", result.output)

    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(h5tbx, ['--help', ])

        self.assertIsNone(result.exception)
        self.assertIn("Usage: h5tbx [OPTIONS] COMMAND [ARGS]...", result.output)
        self.assertIn("--fairify TEXT", result.output)
        self.assertIn("ld", result.output)
        self.assertIn("metrics", result.output)
        self.assertIn("server", result.output)

    def test_command_ld(self):
        runner = CliRunner()
        result = runner.invoke(h5tbx, ["ld", "--help"])
        self.assertIsNone(result.exception)
        self.assertIn("Usage: h5tbx ld [OPTIONS] [FILENAME] COMMAND [ARGS]...", result.output)
        self.assertIn("-o, --output PATH", result.output)
        self.assertIn("--format TEXT", result.output)
        self.assertIn("--graph", result.output)
        self.assertIn("dump", result.output)

    def test_ld_dump(self):
        from h5rdmtoolbox import File

        with File() as h5:
            pass
        runner = CliRunner()
        result = runner.invoke(h5tbx, ["ld", f"{h5.hdf_filename}"])
        self.assertIsNone(result.exception)
        expected = """@prefix hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#> .

[] a hdf:File ;
    hdf:rootGroup [ a hdf:Group ;
            hdf:name "/" ] .


"""
        self.assertEqual(
            expected,
            result.output
        )

    # def test_fairify(self):
    #     with File() as h5:
    #         pass
    #     runner = CliRunner()
    #     result = runner.invoke(h5tbx, [f"--fairify=does-not-exist.hdf"])
    #     self.assertIsNotNone(result.exception)

