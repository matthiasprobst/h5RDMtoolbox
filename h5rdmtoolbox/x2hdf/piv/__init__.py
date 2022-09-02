import argparse

from . import openpiv
from . import pivview
from .interface import PIVSnapshot, PIVPlane, PIVMultiPlane
from .pivview import PIVViewNcFile
from ..._user import user_dirs

if (user_dirs['root'] / 'piv2hdf.yaml').exists():
    from ._config import read_yaml_file

    config = read_yaml_file(user_dirs['root'] / 'piv2hdf.yaml')
else:
    from ._config import DEFAULT_CONFIGURATION

    config = DEFAULT_CONFIGURATION


def use(yaml_file):
    """changes the current global configuration. Passing 'default' set the default values"""
    if yaml_file == 'default':
        from ._config import DEFAULT_CONFIGURATION
        _config = DEFAULT_CONFIGURATION
    else:
        from ._config import read_yaml_file
        _config = read_yaml_file(yaml_file)
    config.update(_config)


# def pivview2hdf(source_folder: pathlib.Path, nproc: int = 1):
def pivview2hdf():
    """Command line interface method. A folder is expected"""
    import pathlib
    parser = argparse.ArgumentParser(description='PIV uncertainty estimation with CNN')

    # Add the arguments
    parser.add_argument('-s', '--source',
                        type=str,
                        required=False,
                        help='Folder or file. Folder must contain nc files or folder with nc files.')
    parser.add_argument('-o', '--outputfile',
                        type=str,
                        nargs='?',
                        default=None,
                        help='Output HDF5 filename.')
    parser.add_argument('-n', '--nproc',
                        type=int,
                        nargs='?',
                        default=1,
                        help='Number of processors')
    parser.add_argument('-c', '--config',
                        type=str,
                        nargs='?',
                        default=None,
                        help='Configuration filename.')
    parser.add_argument('-r', '--recording_time',
                        type=float,
                        nargs='?',
                        default=0.,
                        help='Recording time in [s].')
    parser.add_argument('-freq', '--recording_frequency',
                        type=float,
                        nargs='?',
                        default=0.,
                        help='Recording frequency in [Hz].')
    parser.add_argument("-wdc",
                        "--write_default_config",
                        default=None,
                        action="store_true")
    parser.add_argument("-ov",
                        "--overwrite",
                        default=False,
                        action="store_true")
    parser.add_argument('-f', '--file',
                        type=str,
                        required=False,
                        default=None,
                        help='File name (for configuration)')

    args = parser.parse_args()

    if args.write_default_config:
        if args.file is None:
            trg_cfg_filename = pathlib.Path.cwd() / './piv2hdf_config.yml'
        else:
            trg_cfg_filename = args.file
        from ._config import write_config
        print(f'writing default config to {trg_cfg_filename}')
        write_config(trg_cfg_filename, config=DEFAULT_CONFIGURATION, overwrite=args.overwrite)
        return

    args_dict = vars(args)
    source_path = pathlib.Path(args_dict['source'])
    if not source_path.exists():
        raise FileExistsError(f'Source not found: {source_path}')

    if args.config:
        from ._config import read_yaml_file
        from ...conventions.identifier import StandardizedNameTable
        config = read_yaml_file(pathlib.Path(args.config))
        config['standardized_name_table'] = StandardizedNameTable.from_versionname(
            config['standardized_name_table'])
    else:
        config = None

    if source_path.is_file():
        if not source_path.suffix == '.nc':
            raise ValueError('Source file must be a netCDF4 file!')

        snapshot = PIVSnapshot(PIVViewNcFile(source_path), recording_time=args_dict['recording_time'])
        hdf_filename = snapshot.to_hdf(hdf_filename=args_dict['outputfile'], config=config)
        print(f'Snapshot file {hdf_filename} created')
    else:
        nc_files = sorted(source_path.glob('*.nc'))
        if len(nc_files) > 0:
            plane = PIVPlane([PIVViewNcFile(ncf) for ncf in nc_files],
                             recording_time_or_frequency=args_dict['recording_frequency'])
        else:
            raise NotADirectoryError(f'Not a pivview plane. No nc files found!')
        hdf_filename = plane.to_hdf(hdf_filename=args_dict['outputfile'], config=config)
        print(f'Snapshot file {hdf_filename} created')


__all__ = ['PIVSnapshot', 'PIVPlane', 'PIVMultiPlane']
