from pathlib import Path

import h5py

cfx_to_standard_name = {'accumulated timestep': 'accumulated_timestep',
                        'current timestep': 'current_timestep',
                        'time': 'time',
                        'x': 'x_coordinate',
                        'y': 'y_coordinate',
                        'z': 'z_coordinate',
                        }

pivview_to_standardnames_dict = {'time': 'time',
                                 'u': 'x_velocity',
                                 'v': 'y_velocity',
                                 'w': 'z_velocity',
                                 'x': 'x_coordinate',
                                 'y': 'y_coordinate',
                                 'ix': 'x_pixel_coordinate',
                                 'iy': 'y_pixel_coordinate',
                                 'z': 'z_coordinate',
                                 'velmag': 'magnitude_of_velocity',
                                 'dx': 'x_displacement',
                                 'piv_peak1_dx': 'x_displacement_of_peak1',
                                 'piv_peak2_dx': 'x_displacement_of_peak2',
                                 'piv_peak3_dx': 'x_displacement_of_peak3',
                                 'dy': 'y_displacement',
                                 'piv_peak1_dy': 'y_displacement_of_peak1',
                                 'piv_peak2_dy': 'y_displacement_of_peak2',
                                 'piv_peak3_dy': 'y_displacement_of_peak3',
                                 'dz': 'z_displacement',
                                 'piv_snr_data': 'signal_to_noise',
                                 'piv_flags': 'piv_flag',
                                 'valid': 'validation_flag',
                                 'piv_peak1_corr': 'piv_correlation_value',
                                 'piv_peak2_corr': 'piv_correlation_value',
                                 'piv_peak3_corr': 'piv_correlation_value',
                                 'piv_correlation_coeff': 'piv_correlation_coefficient',
                                 'piv_3c_residuals': 'least_square_residual_of_z_displacement_reconstruction',
                                 'tke': 'turbulent_kinetic_energy',
                                 'dudx': 'x_derivative_of_x_velocity',
                                 'dudy': 'y_derivative_of_x_velocity',
                                 'dudz': 'z_derivative_of_x_velocity',
                                 'dvdx': 'x_derivative_of_y_velocity',
                                 'dvdy': 'y_derivative_of_y_velocity',
                                 'dvdz': 'z_derivative_of_y_velocity',
                                 'dwdx': 'x_derivative_of_z_velocity',
                                 'dwdy': 'y_derivative_of_z_velocity',
                                 'dwdz': 'x_derivative_of_z_velocity',
                                 'uu': 'xx_reynolds_stress',
                                 'uv': 'xy_reynolds_stress',
                                 'uw': 'xz_reynolds_stress',
                                 'vv': 'yy_reynolds_stress',
                                 'vw': 'yz_reynolds_stress',
                                 'ww': 'zz_reynolds_stress'}

pivview_to_cgns_dict = {'time': 'Time',
                        'u': 'VelocityX',
                        'v': 'VelocityY',
                        'w': 'VelocityZ',
                        'x': 'CoordinateX',
                        'y': 'CoordinateY',
                        'ix': 'PixelCoordinateX',
                        'iy': 'PixelCoordinateY',
                        'z': 'CoordinateZ',
                        'velmag': 'VelocityMagnitude',
                        'dx': 'DisplacementX',
                        'piv_peak1_dx': 'Peak1DisplacementX',
                        'piv_peak2_dx': 'Peak2DisplacementX',
                        'piv_peak3_dx': 'Peak3DisplacementX',
                        'dy': 'DisplacementY',
                        'piv_peak1_dy': 'Peak1DisplacementY',
                        'piv_peak2_dy': 'Peak2DisplacementY',
                        'piv_peak3_dy': 'Peak3DisplacementY',
                        'dz': 'DisplacementZ',
                        'piv_snr_data': 'SignalToNoise',
                        'piv_flags': 'PivFlag',
                        'valid': 'ValidationFlag',
                        'piv_peak1_corr': 'PivCorrelatioValue',
                        'piv_peak2_corr': 'PivCorrelationValue',
                        'piv_peak3_corr': 'PivCorrelationValue',
                        'piv_correlation_coeff': 'PivCorrelationCoefficient',
                        # 'piv_3c_residuals': 'least_square_residual_of_z_displacement_reconstruction',
                        'tke': 'TurbulentEnergyKinetic',
                        'uu': 'ReynoldsStressXX',
                        'uv': 'ReynoldsStressXY',
                        'uw': 'ReynoldsStressXZ',
                        'vv': 'ReynoldsStressYY',
                        'vw': 'ReynoldsStressYZ',
                        'ww': 'ReynoldsStressZZ'}


def update(dataset, translation_dict):
    name = Path(dataset.name).name.lower()
    if name in translation_dict:  # pivview_to_standardnames_dict:
        dataset.attrs.modify('standard_name', translation_dict[name])


class H5StandardNameUpdate:
    def __init__(self, translation_dict):
        self._translation_dict = translation_dict

    def __call__(self, name, h5obj):
        if isinstance(h5obj, h5py.Dataset):
            update(h5obj, self._translation_dict)


def update_standard_names(root: h5py.Group, recursive=True):
    """Updates standard names of datasets for PIVview data in
    an HDF5 group. Does it recursively per default"""
    h5snu = H5StandardNameUpdate(pivview_to_standardnames_dict)
    if recursive:
        root.visititems(h5snu)
    else:
        for ds in root:
            if isinstance(ds, h5py.Dataset):
                update(ds, pivview_to_standardnames_dict)
