import unittest

from click.testing import CliRunner

from h5rdmtoolbox_cli import _graph_output_filename, _resolve_format, h5tbx


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
        self.assertIn("Usage: h5tbx ld [OPTIONS] COMMAND [ARGS]...", result.output)
        self.assertIn("dump", result.output)

    def test_command_ld_dump_help(self):
        runner = CliRunner()
        result = runner.invoke(h5tbx, ["ld", "dump", "--help"])
        self.assertIsNone(result.exception)
        self.assertIn("Usage: h5tbx ld dump [OPTIONS] FILENAME", result.output)
        self.assertIn("-o, --output PATH", result.output)
        self.assertIn("--format TEXT", result.output)
        self.assertIn("--structural BOOLEAN", result.output)
        self.assertIn("--contextual BOOLEAN", result.output)
        self.assertIn("--file-uri TEXT", result.output)
        self.assertIn("--graph", result.output)

    def test_ld_format_resolution(self):
        self.assertEqual(_resolve_format(None, "out.jsonld"), "json-ld")
        self.assertEqual(_resolve_format(None, "out.ttl"), "ttl")
        self.assertEqual(_resolve_format("jsonld", "out.ttl"), "json-ld")
        self.assertEqual(_resolve_format("turtle", None), "ttl")

    def test_ld_graph_output_filename(self):
        self.assertEqual(str(_graph_output_filename("data/example.h5")), r"data\example-graph.html")

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
        self.assertIn(expected, result.output)

    def test_ld_dump_without_structural_or_contextual(self):
        from h5rdmtoolbox import File

        with File() as h5:
            pass
        runner = CliRunner()
        result = runner.invoke(
            h5tbx,
            ["ld", "dump", f"{h5.hdf_filename}", "--structural=false", "--contextual=false"],
        )

        self.assertIsNotNone(result.exception)
        self.assertIn("At least one of structural or contextual must be True", result.output)

    def test_ld_dump_with_file_uri(self):
        from h5rdmtoolbox import File

        with File() as h5:
            pass
        runner = CliRunner()
        result = runner.invoke(
            h5tbx,
            ["ld", "dump", f"{h5.hdf_filename}", "--file-uri=https://example.org/data#"],
        )

        self.assertIsNone(result.exception)
        self.assertIn("<https://example.org/data#tmp", result.output)

    # def test_fairify(self):
    #     with File() as h5:
    #         pass
    #     runner = CliRunner()
    #     result = runner.invoke(h5tbx, [f"--fairify=does-not-exist.hdf"])
    #     self.assertIsNotNone(result.exception)

