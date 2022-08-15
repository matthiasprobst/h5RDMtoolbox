# import pathlib
# import shutil
# from pathlib import Path
# from typing import Tuple
#
# from h5rdmtoolbox.utils import generate_temporary_directory
#
# try:
#     from netCDF4 import Dataset as ncDataset
# except ImportError:
#     raise ImportError('Package netCDF4 is not installed.')
#
# testdir = Path(__file__).parent.joinpath('data')
#
#
# def get_plane_directory(name: str) -> pathlib.Path:
#     """Return the path to the respective example PIV plane"""
#     _av = ('piv_challenge',)
#     if name.lower() not in _av:
#         raise ValueError(f'Plane name {name} not in list of available names: {_av}')
#
#     if name.lower() == 'piv_challenge':
#         return testdir / 'PIV/piv_challenge1_E/'
#
#
# def get_multiplane_piv_dirs() -> Tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
#     """Copies the piv_challenge1_E data to three directories in the tmp directory
#     Two planes have three nc files, one plane has 2 nc files only"""
#
#     def _set_z_in_nc(nc_filename, z_val):
#         with ncDataset(nc_filename, 'r+') as nc:
#             nc.setncattr('origin_offset_z', z_val)
#             for k, v in nc.variables.items():
#                 if 'coord_min' in nc[k].ncattrs():
#                     coord_min = nc[k].getncattr('coord_min')
#                     coord_min[-1] = z_val
#                     nc[k].setncattr('coord_min', coord_min)
#                     coord_max = nc[k].getncattr('coord_max')
#                     coord_max[-1] = z_val
#                     nc[k].setncattr('coord_max', coord_max)
#
#     src_dir = get_plane_directory('piv_challenge')
#     nc_files = sorted(src_dir.glob('*[0-9].nc'))
#
#     plane0 = generate_temporary_directory(prefix='mplane/')
#     _ = shutil.copy2(src_dir / 'piv_parameters.par', plane0.joinpath('piv_parameter.par'))
#     dst = shutil.copy2(nc_files[0], plane0.joinpath('f0.nc'))
#     _set_z_in_nc(dst, -5.)
#     dst = shutil.copy2(nc_files[1], plane0.joinpath('f1.nc'))
#     _set_z_in_nc(dst, -5.)
#     dst = shutil.copy2(nc_files[2], plane0.joinpath('f2.nc'))
#     _set_z_in_nc(dst, -5.)
#
#     plane1 = generate_temporary_directory(prefix='mplane/')
#     _ = shutil.copy2(src_dir / 'piv_parameters.par', plane1.joinpath('piv_parameter.par'))
#     dst = shutil.copy2(nc_files[3], plane1.joinpath('f0.nc'))
#     _set_z_in_nc(dst, 0.)
#     dst = shutil.copy2(nc_files[4], plane1.joinpath('f1.nc'))
#     _set_z_in_nc(dst, 0.)
#     dst = shutil.copy2(nc_files[5], plane1.joinpath('f2.nc'))
#     _set_z_in_nc(dst, 0.)
#
#     plane2 = generate_temporary_directory(prefix='mplane/')
#     _ = shutil.copy2(src_dir / 'piv_parameters.par', plane2.joinpath('piv_parameter.par'))
#     dst = shutil.copy2(nc_files[6], plane2.joinpath('f0.nc'))
#     _set_z_in_nc(dst, 10.)
#     dst = shutil.copy2(nc_files[7], plane2.joinpath('f1.nc'))
#     _set_z_in_nc(dst, 10.)
#
#     return plane0, plane1, plane2
#
#
# def get_snapshot_nc_file(name: str, i: int = 1) -> pathlib.Path:
#     _av = ('piv_challenge',)
#     if name.lower() not in _av:
#         raise ValueError(f'Plane name {name} not in list of available names: {_av}')
#     if 8 < i < 1:
#         raise ValueError(f'Snapshot index must be between 0 and 8, not {i}')
#     if name.lower() == 'piv_challenge':
#         return testdir / f'PIV/piv_challenge1_E/E00A{i}.nc'
