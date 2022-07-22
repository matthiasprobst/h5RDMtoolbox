from enum import Enum


class DataSourceType(Enum):
    """root attribute: data_source_type"""
    experimental = 1
    numerical = 2
    analytical = 3
    unknown = 4
    none = 5

    @staticmethod
    def get_attr_name():
        """Atribute name to be used in HDF5 files"""
        return 'data_source_type'


class DataSource(Enum):
    """root attribute: data_source"""
    particle_image_velocimetry = 1
    computational_fluid_dynamics = 2

    @staticmethod
    def get_attr_name():
        """Atribute name to be used in HDF5 files"""
        return 'data_source'
