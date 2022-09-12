from pint import Unit

time_dimensionality = Unit('s').dimensionality
length_dimensionality = Unit('m').dimensionality

try:
    import vtk
except ImportError:
    ImportError('Package vtk not installed. Either install it '
                'separately or install the repository with pip install h5RDMtolbox [piv]')


# unused method:
# def _root_attribute_json_dumps(_dict):
#     class NumpyEncoder(json.JSONEncoder):
#         # from https://stackoverflow.com/questions/26646362/numpy-array-is-not-json-serializable
#         def default(self, obj):
#             if isinstance(obj, np.ndarray):
#                 return obj.tolist()
#             elif isinstance(obj, np.generic):
#                 return obj.item()
#             return json.JSONEncoder.default(self, obj)
#
#     return json.dumps(_dict, cls=NumpyEncoder)


def read_structXML_wrapper(xmlFile):
    """
    This quick helper loads an existing vtr and converts it to a vtk dataset
    to use in mayavi. Add it with pipeline.add_dataset.

    Parameters
    ----------
    xmlFile : str
        Input stl data to load.

    Returns
    -------
    data : vtkRectilinearGrid
        Loaded XML data file.
    """
    reader = vtk.vtkXMLRectilinearGridReader()
    reader.SetFileName(xmlFile)
    reader.Update()
    data = reader.GetOutput()
    return data


def is_time(unit):
    """
    Returns true if unit is a time unit, e.g. 'ms' or 's'
    """
    if unit == 's':
        return True
    else:
        return unit.dimensionality == time_dimensionality


def is_length(unit):
    """
    Returns true if unit is a time unit, e.g. 'ms' or 's'
    """
    if unit == 'm':
        return True
    else:
        return unit.dimensionality == length_dimensionality
