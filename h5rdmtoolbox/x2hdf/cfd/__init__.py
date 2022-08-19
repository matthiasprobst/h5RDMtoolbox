import argparse
import pathlib

from .ansys.cfx import CFXCase


def cfx2hdf(cfx_filename: pathlib.Path) -> pathlib.Path:
    """Convert a CFX case into a HDF. This includes only meta data, monitor and user point data
    and no solution field data!

    Parameters
    ----------
    cfx_filename: pathlib.Path
        The filename of the CFX case

    Returns
    -------
    cfx_filename: pathlib.Path
        The generated HDF5 filename of the CFX case
    """
    cfx_case = CFXCase(cfx_filename)
    return cfx_case.hdf.generate(True)


def _cfx2hdf():
    """Command line interface method. A folder is expected"""
    import pathlib
    from .ansys import AnsysInstallation
    parser = argparse.ArgumentParser(description='PIV uncertainty estimation with CNN')

    # Add the arguments
    parser.add_argument('-f', '--file',
                        type=str,
                        required=False,
                        help='CFX file (*.cfx)')
    parser.add_argument('-inst', '--installation_directory',
                        type=str,
                        required=False,
                        default=None,
                        help='Path to installation directory of ansys cfx')

    args = parser.parse_args()

    ansys_inst = AnsysInstallation()
    if args.installation_directory is not None:
        ansys_inst.installation_directory = args.installation_directory

    installation_directory = ansys_inst.installation_directory
    if installation_directory is None:
        raise FileNotFoundError('Ansys installation directory is unknown. Run cfx2hdf -inst INST_DIR')

    if args.file is not None:
        cfx_filename = pathlib.Path(args.file)
        hdf_filename = cfx2hdf(cfx_filename)
        print(f'Generated {hdf_filename} from {cfx_filename}')
