import argparse
import logging
import pathlib
import sys

import h5rdmtoolbox as h5tbx

logger = logging.getLogger('h5rdmtoolbox')

__this_dir__ = pathlib.Path(__file__).parent

fairify_path = __this_dir__.parent / 'gui'
sys.path.insert(0, str(fairify_path.resolve().absolute()))


def main():
    """command line interface"""
    parser = argparse.ArgumentParser(
        description='h5RDMtoolbox Command line interface'
    )

    # Add the arguments
    # parser.add_argument('input_file',
    #                     nargs=1, help='Input file HDF5 file path (e.g., my_file.hdf)')
    parser.add_argument('-l', '--loglevel', type=str, default='WARNING',
                        help='Set the log level, e.g. "DEBUG"')

    parser.add_argument('-d', '--dump', type=str,
                        help='Input file HDF5 file path (e.g., my_file.hdf)')

    parser.add_argument('-f', '--fairify', type=str,
                        help='Fairify the file (e.g., my_file.hdf)')

    args = parser.parse_args()

    # Set the log level
    logger.setLevel(args.loglevel)
    for h in logger.handlers:
        h.setLevel(args.loglevel)

    logger.debug(f'Command line arguments: {args}')

    if args.dump:
        filename = pathlib.Path(args.dump)
        if not filename.exists():
            raise FileNotFoundError(f'File not found: {filename}')
        h5tbx.dumps(filename)
    if args.fairify:
        filename = pathlib.Path(args.fairify)
        from fairify import start
        start(filename=filename)
        print(f'Opening GUI to fairify the file {filename}')
