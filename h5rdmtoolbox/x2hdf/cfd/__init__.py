import argparse
import pathlib
from typing import Union, Dict

import h5py

from .ansys.cfx import CFXCase
from ...conventions.translations import from_yaml, translate_standard_names


def cfx2hdf(cfx_filename: pathlib.Path,
            snt: Union[pathlib.Path, Dict, None] = None,
            verbose: bool = False) -> pathlib.Path:
    """Convert a CFX case into a HDF. This includes only meta data, monitor and user point data
    and no solution field data!

    Parameters
    ----------
    cfx_filename: pathlib.Path
        The filename of the CFX case
    snt: pathlib.Path | Dict | None, optional=None
        Standard Name Translation Dictionary
    verbose: bool, optional=False
        Additional output

    Returns
    -------
    cfx_filename: pathlib.Path
        The generated HDF5 filename of the CFX case
    """
    cfx_case = CFXCase(cfx_filename)
    hdf_filename = cfx_case.hdf.generate(True)
    if snt:
        if isinstance(snt, Dict):
            sntdict = snt
        else:
            sntdict = from_yaml(snt)
        if sntdict:
            with h5py.File(hdf_filename, 'r+') as h5:
                translate_standard_names(h5, sntdict, verbose)
    return hdf_filename


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
    parser.add_argument('-snt', '--standard-name-translation',
                        type=str,
                        required=False,
                        help='File path to standard name translation. If not set, it will be searched for '
                             'snt.yml in the working directory. To suppress this, set "-ignsnt"')
    parser.add_argument("-ignsnt",
                        "--ignore-snt",
                        default=False,
                        action="store_true",
                        help='Ignore standard name translation files available int the folder')
    parser.add_argument("-v",
                        "--verbose",
                        default=False,
                        action="store_true",
                        help='Additional output')

    args = parser.parse_args()

    ansys_inst = AnsysInstallation()
    if args.installation_directory is not None:
        ansys_inst.installation_directory = args.installation_directory

    installation_directory = ansys_inst.installation_directory
    if installation_directory is None:
        raise FileNotFoundError('Ansys installation directory is unknown. Run cfx2hdf -inst INST_DIR')

    if args.file is not None:
        cfx_filename = pathlib.Path(args.file)
        parent = cfx_filename.parent
        # search for snt:
        snt_files = sorted(parent.glob('snt*.yml'))
        if not args.ignore_snt:
            if len(snt_files) > 0:
                snt_dict = from_yaml(snt_files[0])
                hdf_filename = cfx2hdf(cfx_filename, snt_dict, verbose=args.verbose)
            else:
                hdf_filename = cfx2hdf(cfx_filename)
        else:
            hdf_filename = cfx2hdf(cfx_filename)
        print(f'Generated {hdf_filename} from {cfx_filename}')
