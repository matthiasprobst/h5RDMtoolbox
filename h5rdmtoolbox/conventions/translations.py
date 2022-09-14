# import pathlib
# from os.path import basename
# from pathlib import Path
# from typing import Dict
#
# import h5py
#
#
#
#
#
# def update(dataset, translation_dict):
#     name = Path(dataset.name).name.lower()
#     if name in translation_dict:  # pivview_to_standardnames_dict:
#         dataset.attrs.modify('standard_name', translation_dict[name])
#
#
# class H5StandardNameUpdate:
#     def __init__(self, translation_dict):
#         self._translation_dict = translation_dict
#
#     def __call__(self, name, h5obj):
#         if isinstance(h5obj, h5py.Dataset):
#             update(h5obj, self._translation_dict)
#
#
# def translate_standard_names(root: h5py.Group, translation_dict: Dict,
#                              verbose: bool = False):
#     """Iterate through root recursively and add or update
#     standard names according to the translation dictionary,
#     which provides a translation of names to standard names
#     where 'names' are the dataset names found during
#     iteration through the file"""
#
#     def sn_update(name, node):
#         if isinstance(node, h5py.Dataset):
#             if node.name in translation_dict:
#                 node.attrs['standard_name'] = translation_dict[node.name]
#                 if verbose:
#                     print(f'{name} -> {translation_dict[name]}')
#             elif basename(node.name) in translation_dict:
#                 node.attrs['standard_name'] = translation_dict[basename(node.name)]
#                 if verbose:
#                     print(f'{name} -> {translation_dict[basename(node.name)]}')
#
#     root.visititems(sn_update)
#
#
# def update_pivview_standard_names(root: h5py.Group, recursive=True):
#     """Updates standard names of datasets for PIVview data in
#     an HDF5 group. Does it recursively per default"""
#     h5snu = H5StandardNameUpdate(pivview_to_standardnames_dict)
#     if recursive:
#         root.visititems(h5snu)
#     else:
#         for ds in root:
#             if isinstance(ds, h5py.Dataset):
#                 update(ds, pivview_to_standardnames_dict)
