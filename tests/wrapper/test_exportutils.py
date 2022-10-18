import pathlib
import shutil
import unittest

import numpy as np
import pandas as pd
import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.wrapper import exportutils
from h5rdmtoolbox.wrapper.cflike import H5File


class TestExportUtils(unittest.TestCase):

    def setUp(self) -> None:
        with H5File() as h5:
            h5.attrs['roota'] = 'root_attribute'
            grp = h5.create_group('grp')
            grp.attrs['roota'] = 'grp_attribute'
            grp = grp.create_group('subgrp')
            grp.attrs['roota'] = 'subgrp_attribute'
            ds = h5.create_dataset('mydataset', data=np.random.random((10,)),
                                   units='s', long_name='my long name')
            ds2 = h5.create_dataset('mydataset2', data=np.random.random((10, 20)),
                                    units='s', long_name='my long name')
            h5.create_dataset('x', data=np.linspace(0, 1, 11), units='m', make_scale=True,
                              long_name='xcoord')
            h5.create_dataset('y', data=np.linspace(0, 20, 21), units='m', make_scale=True,
                              long_name='ycoord')
            ds3 = h5.create_dataset('mydataset3', data=np.random.random((11, 21)),
                                    units='s', long_name='my long name', attach_scales=('y', 'x'))
            time = h5.create_dataset('time', data=[1.5, 2.312, 3], units='s', standard_name='time', make_scale=True)
            ds4 = h5.create_dataset('mydataset4', data=[4, 5, 6], units='Pa', long_name='ds4', attach_scales='time')
            self.hdf_filename = h5.hdf_filename

    def test_to_dataset_to_txt(self):
        with H5File(self.hdf_filename, 'r') as h5:
            exportutils.dataset_to_txt(h5['mydataset1'], filename=h5tbx.generate_temporary_filename(suffix='.txt'),
                                       overwrite=True)
            exportutils.dataset_to_txt(h5['mydataset2'], filename=h5tbx.generate_temporary_filename(suffix='.txt'),
                                       overwrite=True)
            txt3 = h5tbx.generate_temporary_filename(suffix='.txt')
            exportutils.dataset_to_txt(h5['mydataset3'], filename=txt3, overwrite=True)
            exportutils.dataset_to_txt(h5['mydataset4'], filename=h5tbx.generate_temporary_filename(suffix='.txt'),
                                       overwrite=True)

            df3 = pd.read_csv(txt3, header=8)
            np.array_equal(df3['mydataset3 [s]'].values.reshape((11, 21)),
                           h5['mydataset3'].values[:])

    def test_to_dataset_to_txt(self):
        test_folder = pathlib.Path('test')
        if test_folder.exists():
            shutil.rmtree(test_folder)
        with H5File(self.hdf_filename, 'r') as h5:
            exportutils.hdf_to_txt(h5, target_directory=h5tbx.generate_temporary_directory(), recursive=False)

    def test_grp_to_txt(self):
        with H5File(self.hdf_filename) as h5:
            exportutils.hdf_to_txt(h5, target_directory=h5tbx.generate_temporary_directory(),
                                   recursive=True, overwrite=True)
