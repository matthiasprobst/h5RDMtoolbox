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

#
# @register_standard_attribute(H5Group, name='data_source_type')
# @register_standard_attribute(H5Dataset, name='data_source_type')
# class DataSourceTypeAttribute:
#     """Long name attribute"""
#
#     def set(self, data_source_type) -> None:
#         """Return data source type as DataSourceType"""
#         if data_source_type is None:
#             return DataSourceType.none
#         try:
#             self.attrs.create('data_source_type', DataSourceType[data_source_type.lower()].name)
#         except KeyError:
#             warnings.warn(f'Data source type is unknown to meta convention: "{data_source_type}"')
#             return DataSourceType.unknown
#
#     def get(self) -> DataSourceType:
#         """Get the data_source_type"""
#         dst = self.attrs.get('data_source_type')
#         if dst is None:
#             return DataSourceType['none']
#         return DataSourceType[dst]
#
#     def delete(self) -> None:
#         """Delete the data_source_type"""
#         self.attrs.__delitem__('data_source_type')
