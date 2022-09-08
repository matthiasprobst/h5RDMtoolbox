# """Name identifier classes
#
# A name identifier class controls the usage of the HDF5 attribute "standard_name".
# The attribute "standard_name" is used in the HDF5 files for all name identifier classes although, for example,
# CGNS uses "name" in its convention.
# The attribute "standard_name" describes a dataset which can have any dataset name. Example: The dataset "u" (name "u")
# has the attribute standard_name="x_velocity". In this case the CF-convention is used, thus, "x_velocity" can be looked-
# up in the standard_name_table to get further information about the dataset. It is further linked to a specific units,
# here "m/s", which is also checked if the user creates the dataset "u".
# Examples for naming tables:
#     - standard name table (http://cfconventions.org/Data/cf-standard-names/current/build/cf-standard-name-table.html)
#     - CGNS data name convention (https://cgns.github.io/CGNS_docs_current/sids/dataname.html)
# """
# import re
# import xml.etree.ElementTree as ET
# from dataclasses import dataclass
# from datetime import datetime
# from pathlib import Path
# from typing import Tuple, Dict, Union, List
#
# import h5py
# import pandas as pd
# import yaml
# from IPython.display import display, HTML
# from pint.errors import UndefinedUnitError
# from pint_xarray import unit_registry as ureg
# from tabulate import tabulate
#
# from .utils import is_valid_email_address, dict2xml
# from .._user import user_dirs
# from ..errors import StandardizedNameError, EmailError
#
# STRICT = True
#
# CF_DATETIME_STR = '%Y-%m-%dT%H:%M:%SZ%z'
#
#
#
#
#
# def merge(list_of_snt: List[StandardNameTable], name: str, version_number: int, institution: str,
#           contact: str) -> StandardNameTable:
#     """Merge multiple standard name tables to a new one"""
#     if len(list_of_snt) < 2:
#         raise ValueError('List of standard name tables must at least contain two entries.')
#     _dict0 = list_of_snt[0]._dict
#     for snt in list_of_snt[1:]:
#         _dict0.update(snt._dict)
#     return StandardNameTable(name=name, table_dict=_dict0,
#                                  version_number=version_number,
#                                  institution=institution, contact=contact)
#
#
# Empty_Standard_Name_Table = StandardNameTable(name='EmptyStandardNameTable',
#                                                   table_dict={},
#                                                   version_number=0,
#                                                   institution=None,
#                                                   contact='none@none.none',
#                                                   last_modified=None,
#                                                   valid_characters='[^a-zA-Z0-9_]',
#                                                   pattern='^[0-9 ].*')
#
#
# class CFStandardNameTable(StandardNameTable):
#     """CF Standard Name Table"""
#
#     def __init__(self, table_dict: Union[Dict, None], version_number: int,
#                  institution: str, contact: str,
#                  last_modified: Union[str, None] = None,
#                  valid_characters: str = '[^a-zA-Z0-9_]',
#                  pattern: str = '^[0-9 ].*'):
#         name = 'CF-convention'
#         super().__init__(name, table_dict, version_number, institution,
#                          contact, last_modified, valid_characters, pattern)
#
#     def check_name(self, name, strict=False) -> bool:
#         """In addtion to check of base class, lowercase is checked first"""
#         if not name.islower():
#             raise StandardizedNameError(f'Standard name must be lowercase!')
#         return super().check_name(name, strict)
#
#
# class CGNSStandardNameTable(StandardNameTable):
#     """CGNS Standard Name Table"""
#
#     def __init__(self, table_dict: Union[Dict, None], version_number: int,
#                  institution: str, contact: str,
#                  last_modified: Union[str, None] = None,
#                  valid_characters: str = '[^a-zA-Z0-9_]',
#                  pattern: str = '^[0-9 ].*'):
#         name = 'CGNS-convention'
#         super().__init__(name, table_dict, version_number, institution,
#                          contact, last_modified, valid_characters, pattern)
#
#
# xml_dir = Path(__file__).parent / 'snxml'
#
#
# def standard_name_table_to_xml(snt: StandardNameTable, overwrite=False):
#     """writes standrad name table to package data"""
#     _xml_filename = xml_dir / f'{snt.name}-v{snt.version_number}.xml'
#     if overwrite:
#         return snt.to_xml(_xml_filename)
#     if not _xml_filename.exists():
#         snt.to_xml(_xml_filename)
#
#
# standard_name_table_to_xml(Empty_Standard_Name_Table)
