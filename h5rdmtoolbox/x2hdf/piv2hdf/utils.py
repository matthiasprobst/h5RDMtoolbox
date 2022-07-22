import json
import os
from re import sub as re_sub

import numpy as np
import vtk
from cv2 import imread as cv2imread
from pco_tools import pco_reader as pco
from psutil import virtual_memory


def _root_attribute_json_dumps(_dict):
    class NumpyEncoder(json.JSONEncoder):
        # from https://stackoverflow.com/questions/26646362/numpy-array-is-not-json-serializable
        def default(self, obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.generic):
                return obj.item()
            return json.JSONEncoder.default(self, obj)

    return json.dumps(_dict, cls=NumpyEncoder)


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
        unit.si.bases[0] == 's'


def is_length(unit):
    """
    Returns true if unit is a time unit, e.g. 'ms' or 's'
    """
    if unit == 'm':
        return True
    else:
        unit.si.bases[0] == 'm'


def remove_special_chars(input_string, keep_special='/_', replace_spaces='_'):
    """Generally removes all characters that are no number
    or letter. Per default, underscores and forward slashs
    are kept and spaces are replaced with underscores.

    Typically used to clean up dataset names that contain special
    characters or spaces which are not allowed for usage in
    natural naming. For this matter, spaces are not allowed in the
    name and should be replaced.

    Parameters
    ----------
    input_string : str
        String with special characters to be removed
    keep_special : str, optional
        Specifies which special characters to keep. Put them
        in one single string. Default is '/_'
    replace_spaces : string, optional
        The string that replaces spaces in the input string.
        Default is '_'. If no action wanted, put False

    Returns
    -------
    _cleaned_str : str
        Processed string without special characters and replaced
        spaces.
    """
    if keep_special:
        _cleaned_str = re_sub('[^a-zA-Z0-9%s ]' % keep_special, '', input_string)
    else:
        _cleaned_str = re_sub('[^a-zA-Z0-9 ]', '', input_string)
    if replace_spaces:
        return _cleaned_str.replace(' ', replace_spaces)
    else:
        return _cleaned_str


def load_img(img_file_path):
    """
    loads b16 or other file format
    :param img_file_path: path to image file
    :return: image as NxM-array
    """

    if os.path.isfile(img_file_path):
        if ".b16" in img_file_path:
            im_ = pco.load(img_file_path)
        else:
            im_ = cv2imread(img_file_path, -1)
        return im_
    else:
        raise FileNotFoundError


def rotate_xy(x, y, rad, center):
    if center[0] == 0:
        _x = x
    else:
        _x = x - center[0]

    if center[1] == 0:
        _y = y
    else:
        _y = y - center[1]

    Xr = np.cos(rad) * _x + np.sin(rad) * _y
    Yr = -np.sin(rad) * _x + np.cos(rad) * _y

    if center[0] != 0:
        Xr += center[0]
    if center[1] != 0:
        Yr += center[1]
    return Xr, Yr


def enough_memory(required_memory_in_bytes):
    # virtual_memory() returns bytes!
    return required_memory_in_bytes < virtual_memory()._asdict()['available']


# ------------------------------
# PIC Convergence functions:

def next_std(sum_of_x, sum_of_x_squared, n, xnew, ddof):
    """computes the standard deviation after adding one more data point to an array.
    Avoids computing the standard deviation from the beginning of the array by using
    math, yeah :-)

    Parameters
    ----------
    sum_of_x : float
        The sum of the array without the new data point
    sum_of_x_squared : float
        The sum of the squared array without the new data point
    n : int
        Number of data points without the new data point
    xnew : float
        The new data point
    ddof : int, optional=0
        Means Delta Degrees of Freedom. See doc of numpy.std().
    """
    sum_of_x = sum_of_x + xnew
    sum_of_x_squared = sum_of_x_squared + xnew ** 2
    n = n + 1  # update n
    return sum_of_x, sum_of_x_squared, np.sqrt(1 / (n - ddof) * (sum_of_x_squared - 1 / n * (sum_of_x) ** 2))


def next_mean(mu, n_mu, new_val):
    """Computes the mean of an array after adding a new value to it

    Parameters
    ----------
    mu : float
        Mean value of the array before adding the new value
    n_mu : int
        Number of values in the array before adding the new value
    new_val : float
        The new value
    """
    return (mu * n_mu + new_val) / (n_mu + 1)


def _transpose_and_reshape_input(x, axis):
    return x.transpose([axis, *[ax for ax in range(x.ndim) if ax != axis]]).reshape(
        (x.shape[axis], x.size // x.shape[axis]))


def _transpose_and_reshape_back_to_original(x, orig_shape, axis):
    ndim = len(orig_shape)
    transpose_order = np.zeros(ndim).astype(int)
    transpose_order[axis] = 0
    k = 1
    for j in range(ndim):
        if j != axis:
            transpose_order[j] = k
            k += 1
    return x.reshape([orig_shape[axis], *[orig_shape[ax] for ax in range(ndim) if ax != axis]]).transpose(
        transpose_order)


def running_mean(x: np.ndarray, axis: int = 0):
    if axis == -1:
        axis = x.ndim
    _x = _transpose_and_reshape_input(x, axis)
    xm = np.zeros_like(_x)
    m = _x[0, :]
    for i in range(1, _x.shape[0]):
        m = next_mean(m, i, _x[i, :])
        xm[i, :] = m
    return _transpose_and_reshape_back_to_original(xm, x.shape, axis)


def running_std(x: np.ndarray, axis: int, ddof=0):
    """shape of x : nt x ndata"""
    if axis == -1:
        axis = x.ndim
    _x = _transpose_and_reshape_input(x, axis)
    x2 = _x ** 2
    std = np.zeros_like(_x)
    sum_of_x = np.sum(_x[0:ddof + 1], axis=0)
    sum_of_x_squared = np.sum(x2[0:ddof + 1], axis=0)
    std[0:ddof + 1] = np.nan
    for i in range(ddof + 1, _x.shape[0]):
        sum_of_x, sum_of_x_squared, std[i, :] = next_std(sum_of_x, sum_of_x_squared, i, _x[i, :], ddof=ddof)
    return _transpose_and_reshape_back_to_original(std, x.shape, axis)


def running_relative_standard_deviation(x, axis, ddof=0):
    """Computes the running relative standard deviation using the running
    mean as normalization."""
    return running_std(x, axis, ddof) / running_mean(x, axis)


# ------------------------------

class PIVFlag():

    def __init__(self, value):
        self.value = value

    def __str__(self: int) -> str:
        return self.value


class PIVviewFlag(PIVFlag):
    _hex_dict = {"inactive": "0x0", "active": "0x1", "masked": "0x2",
                 "noresult": "0x4", "disabled": "0x8", "filtered": "0x10",
                 "interpolated": "0x20", "replaced": "0x40", "manualedit": "0x80"}

    _dict_int = {k: int(v, 16) for k, v in _hex_dict.items()}

    def __init__(self, value: int) -> None:
        super().__init__(value)
        self.flag_translation = {0: 'inactive',
                                 1: 'active',
                                 2: 'masked',
                                 4: 'noresult',
                                 8: 'disabed'}

    def __str__(self) -> str:

        for (k1, v1) in self._dict_int.items():
            if v1 == self.value:
                return k1

        for (k1, v1) in self._dict_int.items():
            for (k2, v2) in self._dict_int.items():
                if v1 + v2 == self.value and v1 != v2:
                    return "%s+%s" % (k1, k2)

        for (k1, v1) in self._dict_int.items():
            for (k2, v2) in self._dict_int.items():
                for (k3, v3) in self._dict_int.items():
                    if v1 + v2 + v3 == self.value and v1 != v2:
                        return "%s+%s+%s" % (k1, k2, k3)

        raise RuntimeError(f'Cannot interpret flag value {self.value}')
