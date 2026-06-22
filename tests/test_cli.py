import unittest
import pathlib
from unittest.mock import patch

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
        self.assertIn("serve", result.output)

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
        self.assertEqual(
            _graph_output_filename("data/example.h5"),
            pathlib.Path("data") / "example-graph.html",
        )

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

    def test_serve_without_filenames_discovers_files(self):
        runner = CliRunner()
        with patch("h5rdmtoolbox.server.run_server") as run_server:
            result = runner.invoke(h5tbx, ["serve"])

        self.assertIsNone(result.exception)
        run_server.assert_called_once()
        self.assertIsNone(run_server.call_args.kwargs["filenames"])

    def test_serve_with_filenames(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            open("a.h5", "w").close()
            open("b.hdf5", "w").close()
            with patch("h5rdmtoolbox.server.run_server") as run_server:
                result = runner.invoke(h5tbx, ["serve", "a.h5", "b.hdf5"])

        self.assertIsNone(result.exception)
        run_server.assert_called_once()
        self.assertEqual(run_server.call_args.kwargs["filenames"], ["a.h5", "b.hdf5"])

    def test_serve_with_folder(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            pathlib.Path("data").mkdir()
            with patch("h5rdmtoolbox.server.run_server") as run_server:
                result = runner.invoke(h5tbx, ["serve", "data"])

        self.assertIsNone(result.exception)
        run_server.assert_called_once()
        self.assertEqual(run_server.call_args.kwargs["filenames"], ["data"])

    def test_serve_with_h5ext(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            pathlib.Path("data").mkdir()
            with patch("h5rdmtoolbox.server.run_server") as run_server:
                result = runner.invoke(h5tbx, ["serve", "data", "--h5ext=.h5", "--h5ext=hdf5"])

        self.assertIsNone(result.exception)
        run_server.assert_called_once()
        self.assertEqual(run_server.call_args.kwargs["h5_extensions"], [".h5", ".hdf5"])

    def test_serve_with_local_iri_pattern(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            open("a.h5", "w").close()
            with patch("h5rdmtoolbox.server.run_server") as run_server:
                result = runner.invoke(
                    h5tbx,
                    [
                        "serve",
                        "a.h5",
                        "--local-iri-pattern",
                        "https://doi.org/10.5281/zenodo.*",
                    ],
                )

        self.assertIsNone(result.exception)
        run_server.assert_called_once()
        self.assertEqual(
            run_server.call_args.kwargs["local_iri_patterns"],
            ["https://doi.org/10.5281/zenodo.*"],
        )

    def test_serve_with_graph_view(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            open("a.h5", "w").close()
            with patch("h5rdmtoolbox.server.run_server") as run_server:
                result = runner.invoke(h5tbx, ["serve", "a.h5", "--graph-view=3d"])

        self.assertIsNone(result.exception)
        run_server.assert_called_once()
        self.assertEqual(run_server.call_args.kwargs["graph_view"], "3d")

    # def test_fairify(self):
    #     with File() as h5:
    #         pass
    #     runner = CliRunner()
    #     result = runner.invoke(h5tbx, [f"--fairify=does-not-exist.hdf"])
    #     self.assertIsNotNone(result.exception)

