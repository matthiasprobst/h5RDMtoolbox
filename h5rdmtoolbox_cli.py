import pathlib

import click


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


def _normalize_format(fmt):
    try:
        return _FORMAT_ALIASES[fmt.lower()]
    except KeyError as exc:
        valid_formats = ", ".join(sorted(_FORMAT_ALIASES))
        raise click.BadParameter(f"Use one of: {valid_formats}") from exc


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


class LegacyLDGroup(click.Group):
    """Route legacy `h5tbx ld FILE` calls to `h5tbx ld dump FILE`."""

    def resolve_command(self, ctx, args):
        if args:
            command_name = click.utils.make_str(args[0])
            if self.get_command(ctx, command_name) is None:
                args = ["dump", *args]
        return super().resolve_command(ctx, args)


@click.group(invoke_without_command=True)
@click.option('--fairify', type=str, help='Starts the app helping you to make the file FAIRer')
def h5tbx(fairify):
    if fairify:
        filename = pathlib.Path(fairify)
        from h5rdmtoolbox.gui.fairify import start
        print(f'Opening GUI to fairify the file {filename}')
        start(filename=filename)
        print('GUI closed')


@h5tbx.group(
    cls=LegacyLDGroup,
    invoke_without_command=True,
    no_args_is_help=True,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
def ld():
    """Linked-Data commands for serializing HDF5 files."""


@ld.command()
@click.argument('filename', type=click.Path(exists=True))
@click.option(
    '-o', '--output',
    type=click.Path(exists=False),
    help='Filename to write the serialized linked-data output to.'
)
@click.option("--format", type=str, help="Output format: ttl, turtle, jsonld, json-ld, or json.")
@click.option("--structural", type=bool, default=True, show_default=True,
              help="Include structural HDF5 RDF data.")
@click.option("--contextual", type=bool, default=True, show_default=True,
              help="Include contextual/user RDF data.")
@click.option("--file-uri", type=str, default=None,
              help="Base file URI to use for RDF subjects.")
@click.option("--graph", is_flag=True,
              help="Generates a graph and stores it in FILENAME-graph.html. Uses pyvis and kglab. "
                   "Please Make sure it is installed")
def dump(filename, output, format, structural, contextual, file_uri, graph):
    """Dump an HDF5 file as linked data."""
    if not structural and not contextual:
        raise click.ClickException("At least one of structural or contextual must be True.")

    fmt = _resolve_format(format, output)

    if output:
        output = pathlib.Path(output)
        if output.suffix.lower() not in _VALID_OUTPUT_EXTENSIONS:
            valid_extensions = ", ".join(sorted(_VALID_OUTPUT_EXTENSIONS))
            raise click.BadParameter(
                f"Output filename must use one of: {valid_extensions}",
                param_hint="'--output'",
            )
        content = _serialize(filename, fmt, structural=structural, contextual=contextual, file_uri=file_uri)
        with open(output, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        content = _serialize(filename, fmt, structural=structural, contextual=contextual, file_uri=file_uri)
        click.echo(content)

    if graph:
        from h5rdmtoolbox import build_pyvis_graph
        build_pyvis_graph(filename, output_filename=_graph_output_filename(filename))


def _serialize(filename, fmt, structural=True, contextual=True, file_uri=None):
    from h5rdmtoolbox import serialize
    return serialize(filename, fmt=fmt, indent=2, structural=structural, contextual=contextual, file_uri=file_uri)


@h5tbx.command()
@click.argument('filenames', nargs=-1, type=click.Path(exists=True))
@click.option('--host', type=str, default='127.0.0.1', help='Host interface to bind the server to')
@click.option('--port', type=int, default=8000, help='Port to run the server on')
@click.option('--no-structural', is_flag=True, default=False, help='Do not include structural RDF')
@click.option('--no-contextual', is_flag=True, default=False, help='Do not include contextual RDF')
@click.option('--file-uri', type=str, default=None, help='Base file URI to use for RDF subjects (must end with # or /)')
@click.option('--local-iri-pattern', multiple=True,
              help='External IRI pattern to resolve locally, e.g. "https://doi.org/10.5281/zenodo.*". Can be used multiple times.')
@click.option('--h5ext', multiple=True,
              help='HDF5 extension to discover in folders, e.g. ".h5" or "hdf5". Can be used multiple times.')
def serve(filenames, host, port, no_structural, no_contextual, file_uri, local_iri_pattern, h5ext):
    """Serve HDF5 file RDF data over HTTP (FastAPI/uvicorn)."""
    structural = not no_structural
    contextual = not no_contextual
    from h5rdmtoolbox.server import _normalize_hdf_extensions, run_server
    selected_filenames = [str(filename) for filename in filenames] if filenames else None
    h5_extensions = sorted(_normalize_hdf_extensions(h5ext)) if h5ext else None
    run_server(host=host, port=port, filenames=selected_filenames,
               structural=structural, contextual=contextual,
               file_uri=file_uri,
               local_iri_patterns=list(local_iri_pattern),
               h5_extensions=h5_extensions)


@h5tbx.command()
@click.argument('rdf_file', type=click.Path(exists=True))
@click.option('--format', 'rdf_format', type=str, default='turtle', help='RDF format (turtle, xml, nt, json-ld)')
@click.option('--directed', is_flag=True, help='Build directed graph')
@click.option('--include-literals', is_flag=True, help='Include literal values as nodes')
@click.option('--ignore-rdf-type', is_flag=True, help='Ignore rdf:type predicates')
@click.option('--top-n', type=int, default=50, help='Top N nodes for centrality')
@click.option('--output-dir', type=click.Path(), default='rdf_graph_metrics_output', help='Output directory for CSVs')
@click.option('--large-threshold', type=int, default=10000, help='Threshold to use approx algorithms')
def metrics(rdf_file, rdf_format, directed, include_literals, ignore_rdf_type, top_n, output_dir, large_threshold):
    """Metrics command removed - placeholder to avoid CLI errors if invoked."""
    raise click.ClickException('The metrics command has been removed. Restore the metrics module if you need this functionality.')


if __name__ == '__main__':
    h5tbx(obj={})
