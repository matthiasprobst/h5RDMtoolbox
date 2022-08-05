# x2hdf.piv2hdf.pivview

No matter if you want to convert a single snapshot, a plane or multiple planes (a case) into 
a single HDF file, there are some conversion settings to be aware of. The default settings 
are stored in a yaml file at your temporary user directory (see `core.pivview_yaml_config_filename`).

To handle different conversion tasks, three classes are available:
* `PIVSnapshot`
* `PIVPlane`
* `PIVCase`

They are inherited from `PIVNCConverter`. The all share some attributes and methods, with `convert()` being the 
most important and central of all. After initializing one of the above objects, it is `convert()` that actually starts 
the conversion process. With this setup, it is obvious, that the conversion process of `PIVPlane` 
will make use of the `convert()`-method of `PIVSnapshot`. The same is true for the conversion process of 
`PIVCase`.

When calling `convert()` you may overwrite some of them by passing a dictionary or overwrite all by passing 
a yaml filename.

Also, all conversions have in common that the shape of a dataset is 4 dimensional for scalar values and 5-dimensional 
for vector data (e.g. velocity). The dimensions are
* nz: number of planes
* nt: number of time steps (snapshots)
* ny: number of points in y-direction
* nx: number of points in x-direction
* nv: number of vector entries (only for 5D-data, e.g. velocity)

Thus, the shape of a dataset is (nz, nt, ny, nx) or (nz, nt, ny, nx, nv) respectively.

## Workflow of how to get from multiple nc files to a single HDF file
### 1. Building a snapshot HDF file
This is simple. The netCDF4 file is read in and variables are basically copied to the HDF file format. 
While doing so the dataset shape is adjusted to meet (nz, nt, ny, nx) and in case of the velocity for 
instance (nz, nt, ny, 3). In case of a snapshot `nz=1` and `nt=1`. Also instead of using "long_name" 
the attribute "description" is used to describe the variable (content). Instead of "units", the attribute
"unit" is chosen. However, this can be controlled via the yaml file!

Note, the `convert()` method of `PIVSnapshot` allows passing `create_hdf=False` which then will not 
create an HDF file. The netCDF4 data will be available in the instance of `PIVSnapshot` as `self.nc_data`, 
`self.nc_root_attr` and `self.nc_variable_attr`.

![../../../docs/source/x2hdf/imgs/snapshot_conversion.png](../../../docs/source/x2hdf/imgs/snapshot_conversion.png)
### 2. Building a plane
For building a plane HDF file the folder containing all netCDF4 files must be passed to `PIVPlane`.
To convert, call `convert()`. This will convert the very first snapshot of the provided list into an HDF5 file. This 
HDF file along with the number of netCDF4 files will provide all information needed, to initialize the plane HDF5 file 
and all the datasets with their respective shape (1, nt, ny, nx) and (1, nt, ny, nx, nv) respectively.

Next, a loop is iterating over all netCDF4 files, initializing a `PIVSnapshot` and calling its `convert()` method 
with `create_hdf` set to False. The available netCDF4 data is therefore not written to a "snapshot HDF file" but 
can directly be written to the correct position in the "plane HDF5 file" (with position we mean time step index).

After all datasets of all snapshots have been written to the plane HDF file, the time averages are 
computed and stored in a separate group called "timeAverages". As those datasets lost the time information, the 
resulting datasets are now one dimension smaller (`(1, ny, nx)` or `(1, ny, nx, nv)`).

![../../../docs/source/x2hdf/imgs/plane_conversion.png](../../../docs/source/x2hdf/imgs/plane_conversion.png)

### 3. Building a case
The principle to build a case is very similar to building a plane. The plane folders 
containing the netCDF4 files are provided during initialization of the `PIVCase` instance. The 
conversion process is similar to that of the plane. The first snapshot of every plane is converted to obtain 
the required dataset information. The number of snapshots is equal to the minimum number of snapshots of 
all planes. Thus, if one plane has more snapshots than another, those are not converted since the dataset must 
fit into one single array. In the future, those missing snapshots could be filled up with NaNs.
