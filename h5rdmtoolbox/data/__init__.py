# create Dummy Layout File (almost empty), which only defines, that the toolbox version
# should be stored in the file


if __name__ == '__main__':
    import h5py

    with h5py.File('EmptyLayout.hdf', 'w') as h5:
        h5.attrs['__h5rdmtoolbox__'] = '__version of this package'
