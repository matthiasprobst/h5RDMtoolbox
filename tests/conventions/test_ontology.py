"""Testing the standard attributes"""
import pathlib
import unittest
from typing import Iterable, Tuple, Any

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.convention import hdf_ontology

__this_dir__ = pathlib.Path(__file__).parent


class TestOntology(unittest.TestCase):

    def test_Attribute(self):
        attr = hdf_ontology.Attribute(name='standard_name',
                                      value='x_velocity')
        print(attr.model_dump_jsonld())

    def test_Dataset(self):
        ds = hdf_ontology.Dataset(
            name='/grp1/grp2/ds1',
            attribute=[
                hdf_ontology.Attribute(name='standard_name',
                                       value='x_velocity')],
            size=100)
        print(ds.model_dump_jsonld())

    def test_Group(self):
        grp = hdf_ontology.Group(
            name='/grp1/grp2',
            attribute=[
                hdf_ontology.Attribute(name='standard_name',
                                       value='x_velocity')],
            member=[
                hdf_ontology.Dataset(
                    name='/grp1/grp2/ds1',
                    attribute=[
                        hdf_ontology.Attribute(name='standard_name',
                                               value='x_velocity')],
                    size=100),
                hdf_ontology.Group(
                    name='/grp1/grp2/grp3',
                    attribute=[
                        hdf_ontology.Attribute(name='standard_name',
                                               value='x_velocity')],
                    member=[
                        hdf_ontology.Dataset(
                            name='/grp1/grp2/grp3/ds2',
                            attribute=[
                                hdf_ontology.Attribute(name='standard_name',
                                                       value='x_velocity')],
                            size=100)])])
        print(grp.model_dump_jsonld())

    def test_RootGroup(self):
        grp = hdf_ontology.Group(
            name='/',
            attribute=[
                hdf_ontology.Attribute(name='standard_name',
                                       value='x_velocity')],
            member=[
                hdf_ontology.Dataset(
                    name='/ds1',
                    attribute=[
                        hdf_ontology.Attribute(name='standard_name',
                                               value='x_velocity')],
                    size=100),
                hdf_ontology.Group(
                    name='/grp1',
                    attribute=[
                        hdf_ontology.Attribute(name='standard_name',
                                               value='x_velocity')],
                    member=[
                        hdf_ontology.Dataset(
                            name='/grp1/ds2',
                            attribute=[
                                hdf_ontology.Attribute(name='standard_name',
                                                       value='x_velocity')],
                            size=100)])])
        print(grp.model_dump_jsonld())

    def test_File(self):
        rootGroup = hdf_ontology.Group(
            name='/grp1'
        )

        grp = hdf_ontology.Group(
            name='/',
            attribute=[
                hdf_ontology.Attribute(name='version',
                                       value='1.0.0')]
        )

        file = hdf_ontology.File(
            rootGroup=rootGroup,
            member=[
                grp
            ]
        )
        print(file.model_dump_jsonld())

    def test_hdf_to_jsonld(self):
        data = {}

        def _build_attributes(attrs: Iterable[Tuple[str, Any]]):
            attrs = [hdf_ontology.Attribute(name=k, value=v) for k, v in attrs.items() if not k.isupper()]
            return attrs

        def _build_dataset_onto_class(ds):
            attrs = _build_attributes(ds.attrs)
            params = dict(name=ds.name, value=ds[()], size=ds.size, attribute=attrs)
            if not attrs:
                params.pop('attribute')
            ontods = hdf_ontology.Dataset(**params)
            data[ds.parent.name].append(ontods)

        def _build_group_onto_class(grp):
            attrs = _build_attributes(grp.attrs)
            params = dict(name=grp.name, attribute=attrs)
            if not attrs:
                params.pop('attribute')
            ontogrp = hdf_ontology.Group(**params)
            if grp.parent.name not in data:
                data[grp.parent.name] = [ontogrp, ]
            else:
                data[grp.parent.name].append(ontogrp)

        def _build_onto_classes(name, node):
            if isinstance(node, h5tbx.Dataset):
                return _build_dataset_onto_class(node)
            return _build_group_onto_class(node)

        with h5tbx.File(mode='w') as h5:
            h5.create_dataset('ds', data=3.4)
            grp = h5.create_group('grp')
            sub_grp = grp.create_group('sub_grp')

        with h5tbx.File(h5.hdf_filename, mode='r') as h5:
            root = hdf_ontology.Group(name='/', attribute=_build_attributes(h5.attrs))
            data['/'] = []

            h5.visititems(_build_onto_classes)

        latest_grp = root
        print(data)
        for k, v in data.items():
            if k != latest_grp.name:
                for m in latest_grp.member:
                    if m.name == k:
                        latest_grp = m
                        break
            for obj in v:
                if latest_grp.member is None:
                    latest_grp.member = [obj, ]
                else:
                    latest_grp.member.append(obj)

        file = hdf_ontology.File(rootGroup=root)
        print(file.model_dump_jsonld())
