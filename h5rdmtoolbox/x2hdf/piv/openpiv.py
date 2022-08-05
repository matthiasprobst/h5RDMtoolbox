import abc
from typing import Tuple, Dict
import h5py
import pandas as pd
import numpy as np
from .interface import PIVFile


class OpenPIVFile(PIVFile):

    def read_from_file(self, filename):
        """Read data from file."""

        data = pd.read_table(filename, )
        x_values = data["# x"].to_numpy()
        y_values = data["y"].to_numpy()

        for i, x in enumerate(x_values[0:-1]):

            if (x - x_values[i + 1]) > 0:
                break
        x = x_values[0:i + 1]
        y = y_values[0::i + 1]
        nx = len(x)
        ny = len(y)

        data_dict = {k: v.to_numpy().reshape((ny, nx)) for k, v in data.items() if k not in ('# x', 'y')}
        data_dict['x'] = x
        data_dict['y'] = y

        return data_dict, {}, {}

    def write_parameters(self):
        pass
