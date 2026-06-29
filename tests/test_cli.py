import unittest
import contextlib
import os
import pathlib
import tempfile
from unittest.mock import patch

from typer.testing import CliRunner
from typer.main import get_command

from h5rdmtoolbox_cli import _graph_output_filename, _resolve_format, h5tbx


@contextlib.contextmanager
def isolated_filesystem():
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        try:
            yield pathlib.Path(tmpdir)
        finally:
            os.chdir(cwd)


def combined_output(result):
    try:
        stderr = result.stderr
    except ValueError:
        stderr = ""
    return result.output + stderr


class TestCLI(unittest.TestCase):

    def test_entrypoint_help(self):
        runner = CliRunner()
        result = runner.invoke(h5tbx, ['--help'], color=False)

        self.assertIsNone(result.exception)
        self.assertIn("Usage:", result.output)
        self.assertIn("ld", result.output)

    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(h5tbx, ['--help', ], color=False)

        self.assertIsNone(result.exception)
        self.assertIn("Usage:", result.output)
        self.assertIn("--fairify", result.output)
        self.assertIn("ld", result.output)
        self.assertIn("metrics", result.output)
        self.assertIn("serve", result.output)

    def test_command_ld(self):
        runner = CliRunner()
        result = runner.invoke(h5tbx, ["ld", "--help"], color=False)
        self.assertIsNone(result.exception)
        self.assertIn("Usage:", result.output)
        self.assertIn("dump", result.output)

    def test_command_ld_dump_help(self):
        runner = CliRunner()
        result = runner.invoke(h5tbx, ["ld", "dump", "--help"], color=False)
        self.assertIsNone(result.exception)
        self.assertIn("Usage:", result.output)
        self.assertIn("FILENAME", result.output)
        self.assertIn("--output", result.output)
        self.assertIn("--format", result.output)
        self.assertIn("--structural", result.output)
        self.assertIn("--contextual", result.output)
        self.assertIn("--file-uri", result.output)
        self.assertIn("--graph", result.output)

    def test_command_ld_dump_option_names(self):
        command = get_command(h5tbx)
        ld_command = command.get_command(None, "ld")
        dump_command = ld_command.get_command(None, "dump")
        opts_by_name = {param.name: param.opts for param in dump_command.params}

        self.assertEqual(opts_by_name["output"], ["-o", "--output"])
        self.assertEqual(opts_by_name["format"], ["--format"])
        self.assertEqual(opts_by_name["structural"], ["--structural"])
        self.assertEqual(opts_by_name["contextual"], ["--contextual"])
        self.assertEqual(opts_by_name["file_uri"], ["--file-uri"])
        self.assertEqual(opts_by_name["graph"], ["--graph"])

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
        self.assertIn("At least one of structural or contextual must be True", combined_output(result))

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
        with isolated_filesystem():
            open("a.h5", "w").close()
            open("b.hdf5", "w").close()
            with patch("h5rdmtoolbox.server.run_server") as run_server:
                result = runner.invoke(h5tbx, ["serve", "a.h5", "b.hdf5"])

        self.assertIsNone(result.exception)
        run_server.assert_called_once()
        self.assertEqual(run_server.call_args.kwargs["filenames"], ["a.h5", "b.hdf5"])

    def test_serve_with_folder(self):
        runner = CliRunner()
        with isolated_filesystem():
            pathlib.Path("data").mkdir()
            with patch("h5rdmtoolbox.server.run_server") as run_server:
                result = runner.invoke(h5tbx, ["serve", "data"])

        self.assertIsNone(result.exception)
        run_server.assert_called_once()
        self.assertEqual(run_server.call_args.kwargs["filenames"], ["data"])

    def test_serve_with_h5ext(self):
        runner = CliRunner()
        with isolated_filesystem():
            pathlib.Path("data").mkdir()
            with patch("h5rdmtoolbox.server.run_server") as run_server:
                result = runner.invoke(h5tbx, ["serve", "data", "--h5ext=.h5", "--h5ext=hdf5"])

        self.assertIsNone(result.exception)
        run_server.assert_called_once()
        self.assertEqual(run_server.call_args.kwargs["h5_extensions"], [".h5", ".hdf5"])

    def test_serve_with_recursive_and_include_ttl(self):
        runner = CliRunner()
        with isolated_filesystem():
            pathlib.Path("data").mkdir()
            with patch("h5rdmtoolbox.server.run_server") as run_server:
                result = runner.invoke(h5tbx, ["serve", "data", "--recursive", "--include-ttl"])

        self.assertIsNone(result.exception)
        run_server.assert_called_once()
        self.assertTrue(run_server.call_args.kwargs["recursive"])
        self.assertTrue(run_server.call_args.kwargs["include_ttl"])

    def test_server_command_is_removed(self):
        runner = CliRunner()
        result = runner.invoke(h5tbx, ["server", "--help"])

        self.assertIsNotNone(result.exception)
        self.assertIn("No such command 'server'", result.output)

    def test_serve_command(self):
        runner = CliRunner()
        with isolated_filesystem():
            pathlib.Path("data").mkdir()
            with patch("h5rdmtoolbox.server.run_server") as run_server:
                result = runner.invoke(h5tbx, ["serve", "data", "--recursive", "--include-ttl"])

        self.assertIsNone(result.exception)
        run_server.assert_called_once()
        self.assertEqual(run_server.call_args.kwargs["filenames"], ["data"])
        self.assertTrue(run_server.call_args.kwargs["recursive"])
        self.assertTrue(run_server.call_args.kwargs["include_ttl"])

    def test_serve_with_local_iri_pattern(self):
        runner = CliRunner()
        with isolated_filesystem():
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
        with isolated_filesystem():
            open("a.h5", "w").close()
            with patch("h5rdmtoolbox.server.run_server") as run_server:
                result = runner.invoke(h5tbx, ["serve", "a.h5", "--graph-view=3d"])

        self.assertIsNone(result.exception)
        run_server.assert_called_once()
        self.assertEqual(run_server.call_args.kwargs["graph_view"], "3d")

    def test_metrics_command_is_removed(self):
        runner = CliRunner()
        with isolated_filesystem():
            pathlib.Path("graph.ttl").write_text("", encoding="utf-8")
            result = runner.invoke(h5tbx, ["metrics", "graph.ttl"])

        self.assertIsNotNone(result.exception)
        self.assertIn("The metrics command has been removed", combined_output(result))

    # def test_fairify(self):
    #     with File() as h5:
    #         pass
    #     runner = CliRunner()
    #     result = runner.invoke(h5tbx, [f"--fairify=does-not-exist.hdf"])
    #     self.assertIsNotNone(result.exception)

