import pathlib

from .ansys.cfx import CFXCase

import argparse

def cfx2hdf(cfx_filename: pathlib.Path):
    cfx_case = CFXCase(cfx_filename)
    return cfx_case.hdf.generate(True)




def _cfx2hdf():
    """Command line interface method. A folder is expected"""
    import pathlib
    parser = argparse.ArgumentParser(description='PIV uncertainty estimation with CNN')

    # Add the arguments
    parser.add_argument('-f', '--file',
                        type=str,
                        required=False,
                        help='CFX file (*.cfx)')

    args = parser.parse_args()

    cfx_filename = pathlib.Path(args.file)
    hdf_filename = cfx2hdf(cfx_filename)
    print(f'Generated {hdf_filename} from {cfx_filename}')
