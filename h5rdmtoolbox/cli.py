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
        print(f'GUI closed')


@h5tbx.command()
@click.argument('filename', type=click.Path(exists=True))
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
def ld(filename, output, format, graph):
    """Linked-Data command"""

    content = None

    def _serialize(filename):
        from h5rdmtoolbox import serialize
        return serialize(filename, fmt=format, indent=2)

    if output:
        output = pathlib.Path(output)
        if not format:
            format = output.suffix[1:]
        if output:
            valid_extension = (".jsonld", ".json-ld", ".ttl", ".turtle")
            if output.suffix not in valid_extension:
                raise ValueError(f"Please use one of the following extensions: {valid_extension}")
            if not content:
                content = _serialize(filename)
            with open(output, "w") as f:
                f.write(content)
    else:
        if not content:
            content = _serialize(filename)
        print(content)

    if graph:
        from h5rdmtoolbox import build_pyvis_graph
        build_pyvis_graph(filename, output_filename=filename.with_suffix("-graph.html"))


if __name__ == '__main__':
    h5tbx(obj={})
