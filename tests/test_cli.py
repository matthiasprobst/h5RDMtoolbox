import unittest
import contextlib
import os
import pathlib
import re
import tempfile
from unittest.mock import patch

from typer.testing import CliRunner
from typer.main import get_command

from h5rdmtoolbox_cli import _resolve_format, h5tbx


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


@contextlib.contextmanager
def isolated_filesystem():
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        try:
            yield pathlib.Path(tmpdir)
        finally:
            os.chdir(cwd)


def normalize_cli_output(text: str) -> str:
    text = ANSI_ESCAPE_RE.sub("", text)
    return " ".join(text.split())


def combined_output(result):
    return normalize_cli_output(result.output)


class TestCLI(unittest.TestCase):

    def test_entrypoint_help(self):
        runner = CliRunner()
        result = runner.invoke(h5tbx, ['--help'], color=False)
        output = normalize_cli_output(result.output)

        self.assertIsNone(result.exception)
        self.assertIn("Usage:", output)
        self.assertIn("ld", output)

    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(h5tbx, ['--help', ], color=False)
        output = normalize_cli_output(result.output)

        self.assertIsNone(result.exception)
        self.assertIn("Usage:", output)
        self.assertNotIn("--fairify", output)
        self.assertIn("ld", output)
        self.assertNotIn("metrics", output)
        self.assertNotIn("serve", output)

    def test_command_ld(self):
        runner = CliRunner()
        result = runner.invoke(h5tbx, ["ld", "--help"], color=False)
        output = normalize_cli_output(result.output)
        self.assertIsNone(result.exception)
        self.assertIn("Usage:", output)
        self.assertIn("dump", output)

    def test_command_ld_dump_help(self):
        runner = CliRunner()
        result = runner.invoke(h5tbx, ["ld", "dump", "--help"], color=False)
        output = normalize_cli_output(result.output)
        self.assertIsNone(result.exception)
        self.assertIn("Usage:", output)
        self.assertIn("filename", output.lower())
        self.assertIn("--output", output)
        self.assertIn("Filename to write the serialized", output)
        self.assertIn("--format", output)
        self.assertIn("--structural", output)
        self.assertIn("--contextual", output)
        self.assertIn("--file-uri", output)
        self.assertIn("--prefix", output)
        self.assertNotIn("--graph", output)

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
        self.assertEqual(opts_by_name["prefix"], ["--prefix"])

    def test_ld_format_resolution(self):
        self.assertEqual(_resolve_format(None, "out.jsonld"), "json-ld")
        self.assertEqual(_resolve_format(None, "out.ttl"), "ttl")
        self.assertEqual(_resolve_format("jsonld", "out.ttl"), "json-ld")
        self.assertEqual(_resolve_format("turtle", None), "ttl")


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

    def test_ld_dump_with_file_uri_and_prefix(self):
        from h5rdmtoolbox import File

        with File() as h5:
            pass
        runner = CliRunner()
        result = runner.invoke(
            h5tbx,
            [
                "ld",
                "dump",
                f"{h5.hdf_filename}",
                "--file-uri=https://example.org/data#",
                "--prefix=ex",
            ],
        )

        self.assertIsNone(result.exception)
        self.assertIn("@prefix ex: <https://example.org/data#>", result.output)

    def test_ld_dump_prefix_requires_file_uri(self):
        from h5rdmtoolbox import File

        with File() as h5:
            pass
        runner = CliRunner()
        result = runner.invoke(h5tbx, ["ld", "dump", f"{h5.hdf_filename}", "--prefix=ex"])

        self.assertIsNotNone(result.exception)
        self.assertIn("--prefix requires --file-uri", combined_output(result))

    def test_ld_dump_rejects_invalid_prefix(self):
        from h5rdmtoolbox import File

        with File() as h5:
            pass
        runner = CliRunner()
        result = runner.invoke(
            h5tbx,
            [
                "ld",
                "dump",
                f"{h5.hdf_filename}",
                "--file-uri=https://example.org/data#",
                "--prefix=invalid prefix",
            ],
        )

        self.assertIsNotNone(result.exception)
        self.assertIn("Prefix must start with a letter or underscore", combined_output(result))











    # def test_fairify(self):
    #     with File() as h5:
    #         pass
    #     runner = CliRunner()
    #     result = runner.invoke(h5tbx, [f"--fairify=does-not-exist.hdf"])
    #     self.assertIsNotNone(result.exception)

