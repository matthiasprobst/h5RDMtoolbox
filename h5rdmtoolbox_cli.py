import pathlib

import click


@click.group(invoke_without_command=True)
@click.option('--fairify', type=str, help='Starts the app helping you to make the file FAIRer')
def h5tbx(fairify):
    if fairify:
        filename = pathlib.Path(fairify)
        from h5rdmtoolbox.gui.fairify import start
        print(f'Opening GUI to fairify the file {filename}')
        start(filename=filename)
        print('GUI closed')


@h5tbx.group(invoke_without_command=True)
@click.argument('filename', type=click.Path(exists=True), required=False)
@click.option(
    '-o', '--output',
    type=click.Path(exists=False),
    help='Filename to write the JSON-LD data to.'
)
@click.option("--format", type=str, help="The output format, e.g. jsonld.",
              default="ttl")
@click.option("--graph", is_flag=True,
              help="Generates a graph and stores it in OUTPUT-graph.html. Uses pyvis and kglab. "
                   "Please Make sure it is installed")
@click.pass_context
def ld(ctx, filename, output, format, graph):
    """Linked-Data command. If called without subcommand, behaves like the previous `ld` command and
    serializes the given FILENAME to the requested format or to OUTPUT when provided.
    """
    if ctx.invoked_subcommand is not None:
        return

    if filename is None:
        raise click.UsageError('FILENAME is required when calling `h5tbx ld` without a subcommand')

    content = None

    def _serialize(filename):
        from h5rdmtoolbox import serialize
        return serialize(filename, fmt=format, indent=2)

    if output:
        output = pathlib.Path(output)
        if not format:
            format = output.suffix[1:]
        valid_extension = (".jsonld", ".json-ld", ".ttl", ".turtle")
        if output.suffix not in valid_extension:
            raise ValueError(f"Please use one of the following extensions: {valid_extension}")
        if not content:
            content = _serialize(filename)
        with open(output, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        if not content:
            content = _serialize(filename)
        click.echo(content)

    if graph:
        from h5rdmtoolbox import build_pyvis_graph
        build_pyvis_graph(filename, output_filename=pathlib.Path(filename).with_suffix("-graph.html"))


@ld.command()
@click.argument('filename', type=click.Path(exists=True))
@click.option('--format', type=str, default='turtle', help='Output format: turtle (ttl) or json-ld')
def dump(filename, format):
    """Dump the HDF5 file as linked-data in the requested format (default: turtle)."""
    from h5rdmtoolbox import serialize
    fmt = format
    if fmt in ('ttl', 'turtle'):
        fmt = 'ttl'
    elif fmt in ('jsonld', 'json-ld', 'json'):
        fmt = 'json-ld'
    content = serialize(filename, fmt=fmt, indent=2)
    click.echo(content)


@h5tbx.command()
@click.argument('filename', type=click.Path(exists=True))
@click.option('--host', type=str, default='127.0.0.1', help='Host interface to bind the server to')
@click.option('--port', type=int, default=8000, help='Port to run the server on')
@click.option('--no-structural', is_flag=True, default=False, help='Do not include structural RDF')
@click.option('--no-contextual', is_flag=True, default=False, help='Do not include contextual RDF')
@click.option('--file-uri', type=str, default=None, help='Base file URI to use for RDF subjects (must end with # or /)')
def server(filename, host, port, no_structural, no_contextual, file_uri):
    """Start a small RDF HTTP server exposing the file's RDF (FastAPI/uvicorn)."""
    structural = not no_structural
    contextual = not no_contextual
    filename = pathlib.Path(filename)
    from h5rdmtoolbox.server import run_server
    run_server(host=host, port=port, filename=str(filename), structural=structural, contextual=contextual,
               file_uri=file_uri)


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
