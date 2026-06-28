import pathlib
import sys
from enum import Enum
from typing import Annotated, List, Optional

import click
import typer
import typer.rich_utils
from typer.core import TyperGroup

typer.rich_utils.STYLE_OPTIONS_TABLE_BOX = "ASCII"
typer.rich_utils.STYLE_COMMANDS_TABLE_BOX = "ASCII"

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


_FORMAT_ALIASES = {
    "ttl": "ttl",
    "turtle": "ttl",
    "json": "json-ld",
    "jsonld": "json-ld",
    "json-ld": "json-ld",
}
_VALID_OUTPUT_EXTENSIONS = {
    ".jsonld": "json-ld",
    ".json-ld": "json-ld",
    ".ttl": "ttl",
    ".turtle": "ttl",
}


class GraphView(str, Enum):
    """Supported graph visualization modes."""

    two_d = "2d"
    three_d = "3d"


def _normalize_format(fmt):
    try:
        return _FORMAT_ALIASES[fmt.lower()]
    except KeyError as exc:
        valid_formats = ", ".join(sorted(_FORMAT_ALIASES))
        raise typer.BadParameter(f"Use one of: {valid_formats}") from exc


def _parse_bool_option(value, option_name: str) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise typer.BadParameter(f"{option_name} must be true or false.")


def _resolve_format(fmt, output):
    if fmt is not None:
        return _normalize_format(fmt)
    if output is not None:
        output_suffix = pathlib.Path(output).suffix.lower()
        if output_suffix in _VALID_OUTPUT_EXTENSIONS:
            return _VALID_OUTPUT_EXTENSIONS[output_suffix]
    return "ttl"


def _graph_output_filename(filename):
    path = pathlib.Path(filename)
    return path.with_name(f"{path.stem}-graph.html")


class LegacyLDGroup(TyperGroup):
    """Route legacy `h5tbx ld FILE` calls to `h5tbx ld dump FILE`."""

    def resolve_command(self, ctx, args):
        if args:
            command_name = click.utils.make_str(args[0])
            if self.get_command(ctx, command_name) is None:
                args = ["dump", *args]
        return super().resolve_command(ctx, args)


app = typer.Typer(
    name="h5tbx",
    invoke_without_command=True,
    no_args_is_help=True,
    add_completion=False,
    help="h5RDMtoolbox command line tools.",
)
ld_app = typer.Typer(
    cls=LegacyLDGroup,
    invoke_without_command=True,
    no_args_is_help=True,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
    help="Linked-Data commands for serializing HDF5 files.",
)


@app.callback()
def main(
        fairify: Annotated[
            Optional[pathlib.Path],
            typer.Option("--fairify", help="Starts the app helping you to make the file FAIRer."),
        ] = None,
):
    if fairify:
        from h5rdmtoolbox.gui.fairify import start

        typer.echo(f"Opening GUI to fairify the file {fairify}")
        start(filename=fairify)
        typer.echo("GUI closed")


@ld_app.command()
def dump(
        filename: Annotated[
            pathlib.Path,
            typer.Argument(exists=True, help="HDF5 file to serialize as linked data."),
        ],
        output: Annotated[
            Optional[pathlib.Path],
            typer.Option("-o", "--output", help="Filename to write the serialized linked-data output to."),
        ] = None,
        format: Annotated[
            Optional[str],
            typer.Option("--format", help="Output format: ttl, turtle, jsonld, json-ld, or json."),
        ] = None,
        structural: Annotated[
            str,
            typer.Option("--structural", help="Include structural HDF5 RDF data."),
        ] = "true",
        contextual: Annotated[
            str,
            typer.Option("--contextual", help="Include contextual/user RDF data."),
        ] = "true",
        file_uri: Annotated[
            Optional[str],
            typer.Option("--file-uri", help="Base file URI to use for RDF subjects."),
        ] = None,
        graph: Annotated[
            bool,
            typer.Option(
                "--graph",
                help="Generates a graph and stores it in FILENAME-graph.html. Uses pyvis and kglab.",
            ),
        ] = False,
):
    """Dump an HDF5 file as linked data."""
    structural_value = _parse_bool_option(structural, "--structural")
    contextual_value = _parse_bool_option(contextual, "--contextual")
    if not structural_value and not contextual_value:
        typer.echo("Error: At least one of structural or contextual must be True.", err=True)
        raise typer.Exit(code=1)

    fmt = _resolve_format(format, output)

    if output:
        if output.suffix.lower() not in _VALID_OUTPUT_EXTENSIONS:
            valid_extensions = ", ".join(sorted(_VALID_OUTPUT_EXTENSIONS))
            raise typer.BadParameter(
                f"Output filename must use one of: {valid_extensions}",
                param_hint="'--output'",
            )
        content = _serialize(filename, fmt, structural=structural_value, contextual=contextual_value, file_uri=file_uri)
        with open(output, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        content = _serialize(filename, fmt, structural=structural_value, contextual=contextual_value, file_uri=file_uri)
        typer.echo(content)

    if graph:
        from h5rdmtoolbox import build_pyvis_graph

        build_pyvis_graph(filename, output_filename=_graph_output_filename(filename))


def _serialize(filename, fmt, structural=True, contextual=True, file_uri=None):
    from h5rdmtoolbox import serialize

    return serialize(filename, fmt=fmt, indent=2, structural=structural, contextual=contextual, file_uri=file_uri)


@app.command()
def serve(
        filenames: Annotated[
            Optional[List[pathlib.Path]],
            typer.Argument(exists=True, help="HDF5 files or folders to serve."),
        ] = None,
        host: Annotated[
            str,
            typer.Option("--host", help="Host interface to bind the server to."),
        ] = "127.0.0.1",
        port: Annotated[
            int,
            typer.Option("--port", help="Port to run the server on."),
        ] = 8000,
        no_structural: Annotated[
            bool,
            typer.Option("--no-structural", help="Do not include structural RDF."),
        ] = False,
        no_contextual: Annotated[
            bool,
            typer.Option("--no-contextual", help="Do not include contextual RDF."),
        ] = False,
        file_uri: Annotated[
            Optional[str],
            typer.Option("--file-uri", help="Base file URI to use for RDF subjects (must end with # or /)."),
        ] = None,
        local_iri_pattern: Annotated[
            Optional[List[str]],
            typer.Option(
                "--local-iri-pattern",
                help='External IRI pattern to resolve locally, e.g. "https://doi.org/10.5281/zenodo.*".',
            ),
        ] = None,
        h5ext: Annotated[
            Optional[List[str]],
            typer.Option("--h5ext", help='HDF5 extension to discover in folders, e.g. ".h5" or "hdf5".'),
        ] = None,
        recursive: Annotated[
            bool,
            typer.Option("--recursive", help="Recursively discover HDF5 files in folders."),
        ] = False,
        include_ttl: Annotated[
            bool,
            typer.Option("--include-ttl", help="Also include Turtle files in the combined RDF graph."),
        ] = False,
        graph_view: Annotated[
            GraphView,
            typer.Option("--graph-view", case_sensitive=False, help="Default graph visualization view."),
        ] = GraphView.two_d,
):
    """Serve HDF5 file RDF data over HTTP (FastAPI/uvicorn)."""
    structural = not no_structural
    contextual = not no_contextual
    from h5rdmtoolbox.server import _normalize_hdf_extensions, run_server

    selected_filenames = [str(filename) for filename in filenames] if filenames else None
    h5_extensions = sorted(_normalize_hdf_extensions(h5ext)) if h5ext else None
    run_server(host=host, port=port, filenames=selected_filenames,
               structural=structural, contextual=contextual,
               file_uri=file_uri,
               local_iri_patterns=list(local_iri_pattern or []),
               h5_extensions=h5_extensions,
               recursive=recursive,
               include_ttl=include_ttl,
               graph_view=graph_view.value)


@app.command()
def metrics(
        rdf_file: Annotated[
            pathlib.Path,
            typer.Argument(exists=True, help="RDF file."),
        ],
        rdf_format: Annotated[
            str,
            typer.Option("--format", help="RDF format (turtle, xml, nt, json-ld)."),
        ] = "turtle",
        directed: Annotated[bool, typer.Option("--directed", help="Build directed graph.")] = False,
        include_literals: Annotated[bool, typer.Option("--include-literals", help="Include literal values as nodes.")] = False,
        ignore_rdf_type: Annotated[bool, typer.Option("--ignore-rdf-type", help="Ignore rdf:type predicates.")] = False,
        top_n: Annotated[int, typer.Option("--top-n", help="Top N nodes for centrality.")] = 50,
        output_dir: Annotated[pathlib.Path, typer.Option("--output-dir", help="Output directory for CSVs.")] = pathlib.Path(
            "rdf_graph_metrics_output"
        ),
        large_threshold: Annotated[int, typer.Option("--large-threshold", help="Threshold to use approx algorithms.")] = 10000,
):
    """Metrics command removed - placeholder to avoid CLI errors if invoked."""
    typer.echo('Error: The metrics command has been removed. Restore the metrics module if you need this functionality.',
               err=True)
    raise typer.Exit(code=1)


app.add_typer(ld_app, name="ld")
h5tbx = app


if __name__ == "__main__":
    h5tbx()
