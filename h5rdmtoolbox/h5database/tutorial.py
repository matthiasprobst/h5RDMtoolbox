import os

import numpy as np

from h5rdmtoolbox.h5wrapper import H5File


def build_test_repo(repo_dir, n_files: int = 100):
    """
    sample file with some groups, datasets and attributes
    Data is stored with actual names at correct hdf-path location,
    but the file is just not complete and data is randomly created
    and has no physical meaning.
    """

    def _get_pressure(v):
        """a random pressure curve. input volume rate [0, 0.1] and
        get a artificial pressure in return"""
        x = np.linspace(0, 0.1, 101)
        p = -60 / np.max(x) ** 2 * v ** 2 + 60
        return p

    _folders = ('d1', 'd2', 'd3', 'd1/d11', 'd1/d11/d111', 'd2/d21')
    folders = [os.path.join(repo_dir, _f) for _f in _folders]
    operators = ('Mike', 'Ellen', 'John', 'Susi')
    db_file_type = ('fan_case', 'piv_case')

    file_ids = range(n_files)
    vfrs = np.random.uniform(0, 0.1, n_files)
    for fid, vfr in zip(file_ids, vfrs):

        # select a random directory:
        ifolder = np.random.randint(0, len(_folders))
        # create folder if not exist:
        os.makedirs(folders[ifolder], exist_ok=True)

        filename = os.path.join(folders[ifolder], f'repofile_{fid:05d}.hdf')
        with H5File(filename, 'w') as h5:
            h5.attrs['operator'] = operators[np.random.randint(4)]
            __ftype__ = db_file_type[np.random.randint(2)]
            h5.attrs['__db_file_type__'] = __ftype__

            if __ftype__ == 'fan_case':
                op = h5.create_group('operation_point', attrs={'long_name': 'Operation point data group'})

                _ptot = _get_pressure(vfr)
                _ptot_vec = np.random.rand(100) - 0.5 + _ptot
                ds = op.create_dataset('ptot',
                                       data=_ptot_vec, attrs={'units': 'Pa', 'long_name': 'Pressure increase'})
                ds.attrs['mean'] = np.mean(_ptot_vec)
                ds.attrs['std'] = np.std(_ptot_vec)

                _vfr_vec = np.random.rand(100) - 0.5 + vfr
                ds = op.create_dataset('vfr',
                                       attrs={'units': 'm3/s', 'long_name': 'volume flow_utils rate'},
                                       data=_vfr_vec)
                ds.attrs['mean'] = np.mean(_vfr_vec)
                ds.attrs['std'] = np.std(_vfr_vec)
            else:
                zplanes, timesteps = 2, 5
                h5.create_dataset('u', attrs={'units': 'm/s', 'long_name': 'u-component'},
                                  shape=(zplanes, timesteps, 64, 86, 2))
                h5.create_dataset('v', attrs={'units': 'm/s', 'long_name': 'v-component'},
                                  shape=(zplanes, timesteps, 64, 86, 2))
                g = h5.create_group('timeAverages', long_name='time averaged data')
                g.create_dataset('u', attrs={'units': 'm/s', 'long_name': 'mean u-component'},
                                 shape=(zplanes, 64, 86, 2))
                g.create_dataset('v', attrs={'units': 'm/s', 'long_name': 'mean v-component'},
                                 shape=(zplanes, 64, 86, 2))
