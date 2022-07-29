import h5py

from . import ccl
from . import cfx
from .cfx import process_monitor_string

def cfx2hdf(cfx_filename, hdf_filename=None):
    """converts a Ansys-CFX case into an HDF5 file (not the field solution but
    settings and monitor data)"""
    cfx_case = cfx.CFXCase(cfx_filename)
    hdf_filename = ccl.CCLTextFile(cfx_case.ccl_filename).to_hdf(hdf_filename)
    monitor_data = cfx_case.latest.monitor.data

    scale_sub_names = ('ACCUMULATED TIMESTEP', 'CURRENT TIMESTEP', 'TIME', )
    scale_monitor_names = []
    scale_datasets = []

    with h5py.File(hdf_filename, 'r+') as h5:
        for k in monitor_data.keys():
            if any([scale_name in k for scale_name in scale_sub_names]):
                scale_monitor_names.append(k)
                meta_dict = process_monitor_string(k)
                ds = h5.create_dataset(name=f'{meta_dict["group"]}/{meta_dict["name"]}', data=monitor_data[k])
                ds.attrs['units'] = meta_dict['units']
                ds.make_scale()
                scale_datasets.append(ds)

        grp = h5.create_group('monitor')
        for k, v in monitor_data.items():
            if k not in scale_monitor_names:
                meta_dict = process_monitor_string(k)
                ds = grp.create_dataset(name=f'{meta_dict["group"]}/{meta_dict["name"]}', data=v)
                ds.attrs['units'] = meta_dict['units']
                ds.dims[0].attach_scale(h5['ACCUMULATED TIMESTEP'])
                for scale_dataset in scale_datasets:
                    ds.dims[0].attach_scale(scale_dataset)
                if meta_dict['coords']:
                    ds.attrs['COORDINATES'] = list(meta_dict['coords'].keys())
                    for kc, vc in meta_dict['coords'].items():
                        dsc = grp[meta_dict["group"]].create_dataset(kc, data=vc)  # NOTE: ASSUMING [m] is the default units but TODO check in CCL file what the base unit is!
                        dsc.attrs['units'] = 'm'

    return hdf_filename
