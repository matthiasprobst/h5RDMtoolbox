"""Testing the standard attributes"""
import json
import pathlib
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.convention import hdf_ontology

__this_dir__ = pathlib.Path(__file__).parent


def remove_key_recursive(d, key_to_remove):
    if isinstance(d, dict):
        for key in list(d.keys()):
            if key == key_to_remove:
                del d[key]
            else:
                remove_key_recursive(d[key], key_to_remove)
    elif isinstance(d, list):
        for item in d:
            remove_key_recursive(item, key_to_remove)


class TestOntology(unittest.TestCase):

    def setUp(self):
        h5tbx.use(None)

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
        with h5tbx.File(mode='w') as h5:
            h5.create_dataset('ds', data=3.4)
            grp = h5.create_group('grp')
            sub_grp = grp.create_group('sub_grp')
            sub_grp.create_dataset('ds', data=3, dtype='i8')
            sub_grp['ds'].attrs['units'] = 'm/s'

        from h5rdmtoolbox.wrapper.jsonld import dump_file
        hdf_jsonld = dump_file(h5.hdf_filename, skipND=1)

        jsonld_dict = json.loads(hdf_jsonld)

        remove_key_recursive(jsonld_dict, '@id')
        print(json.dumps(jsonld_dict, indent=2))

        self.maxDiff = None
        print(jsonld_dict)
        self.assertDictEqual(jsonld_dict,
                             {"@context": {
                                 "owl": "http://www.w3.org/2002/07/owl#",
                                 "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                                 "hdf5": "http://purl.allotrope.org/ontologies/hdf5/1.8#"
                             },
                                 "@type": "hdf5:File",
                                 "hdf5:rootGroup": {
                                     "@type": "hdf5:Group",
                                     "hdf5:attribute": [],
                                     "hdf5:name": "/",
                                     "hdf5:member": [
                                         {
                                             "@type": "hdf5:Dataset",
                                             "hdf5:name": "/ds",
                                             "hdf5:size": "1",
                                             "hdf5:datatype": "H5T_FLOAT",
                                             "hdf5:value": "3.4"
                                         },
                                         {
                                             "@type": "hdf5:Group",
                                             "hdf5:name": "/grp",
                                             "hdf5:member": [
                                                 {
                                                     "@type": "hdf5:Group",
                                                     "hdf5:name": "/grp/sub_grp",
                                                     "hdf5:member": [
                                                         {
                                                             "@type": "hdf5:Dataset",
                                                             "hdf5:attribute": [
                                                                 {
                                                                     "@type": "hdf5:Attribute",
                                                                     "hdf5:name": "units",
                                                                     "hdf5:value": "m/s"
                                                                 }
                                                             ],
                                                             "hdf5:name": "/grp/sub_grp/ds",
                                                             "hdf5:size": "1",
                                                             "hdf5:datatype": "H5T_INTEGER",
                                                             "hdf5:value": "3.0"
                                                         }
                                                     ]
                                                 }
                                             ]
                                         },
                                         {
                                             "@type": "hdf5:Group",
                                             "hdf5:attribute": [
                                                 {
                                                     "@type": "hdf5:Attribute",
                                                     "hdf5:name": "__h5rdmtoolbox_version__",
                                                     "hdf5:value": f"{h5tbx.__version__}"
                                                 }
                                             ],
                                             "hdf5:name": "/h5rdmtoolbox"
                                         }
                                     ]
                                 }
                             }
                             )

        # get all group names with SPARQL:
        sparql_query = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX hdf5: <http://purl.allotrope.org/ontologies/hdf5/1.8#>
        
        SELECT ?ds_name ?ds_size
        WHERE {
            ?group rdf:type hdf5:Dataset .
            ?group hdf5:name ?ds_name .
            ?group hdf5:size ?ds_size .
        }
        """
        import rdflib
        g = rdflib.Graph()
        g.parse(data=hdf_jsonld, format='json-ld')
        results = g.query(sparql_query)

        # convert results to dataframe:
        import pandas as pd
        df = pd.DataFrame(results.bindings)
        print(df)
