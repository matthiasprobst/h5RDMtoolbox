"""Testing the standard attributes"""
import json
import pathlib
import unittest

import h5rdmtoolbox as h5tbx
import rdflib
from h5rdmtoolbox.convention.ontology import HDF5, Attribute, Dataset, Group, File

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
        attr = Attribute(name='standard_name',
                                      value='x_velocity')
        print(attr.model_dump_jsonld())

    def test_Dataset(self):
        ds = Dataset(
            name='/grp1/grp2/ds1',
            attribute=[
                Attribute(name='standard_name',
                                       value='x_velocity')],
            size=100)
        print(ds.model_dump_jsonld())

    def test_Group(self):
        grp = Group(
            name='/grp1/grp2',
            attribute=[
                Attribute(name='standard_name',
                                       value='x_velocity')],
            member=[
                Dataset(
                    name='/grp1/grp2/ds1',
                    attribute=[
                        Attribute(name='standard_name',
                                               value='x_velocity')],
                    size=100),
                Group(
                    name='/grp1/grp2/grp3',
                    attribute=[
                        Attribute(name='standard_name',
                                               value='x_velocity')],
                    member=[
                        Dataset(
                            name='/grp1/grp2/grp3/ds2',
                            attribute=[
                                Attribute(name='standard_name',
                                                       value='x_velocity')],
                            size=100)])])
        print(grp.model_dump_jsonld())

    def test_RootGroup(self):
        grp = Group(
            name='/',
            attribute=[
                Attribute(name='standard_name',
                                       value='x_velocity')],
            member=[
                Dataset(
                    name='/ds1',
                    attribute=[
                        Attribute(name='standard_name',
                                               value='x_velocity')],
                    size=100),
                Group(
                    name='/grp1',
                    attribute=[
                        Attribute(name='standard_name',
                                               value='x_velocity')],
                    member=[
                        Dataset(
                            name='/grp1/ds2',
                            attribute=[
                                Attribute(name='standard_name',
                                                       value='x_velocity')],
                            size=100)])])
        print(grp.model_dump_jsonld())

    def test_File(self):
        rootGroup = Group(
            name='/grp1'
        )

        grp = Group(
            name='/',
            attribute=[
                Attribute(name='version',
                                       value='1.0.0')]
        )

        file = File(
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
        g = rdflib.Graph()
        g.parse(data=hdf_jsonld, format='json-ld')
        results = g.query(sparql_query)

        # convert results to dataframe:
        import pandas as pd
        df = pd.DataFrame(results.bindings)
        print(df)

    def test_jsonld_to_hdf(self):
        jsonld = """
{
    "@context": 
        {
            "@import": "https://w3id.org/nfdi4ing/metadata4ing/m4i_context.jsonld",
            "local": "https://local-domain.org/"
        },
    "@graph": [
        {
            "@id": "local:alex",
            "@type": "person",
            "has ORCID ID": "0000-0000-0123-4567",
            "first name": "Alexandra",
            "last name": "Test"
        }
    ]
}
"""
        with h5tbx.File() as h5:
            h5.create_group('metadata')
            h5tbx.jsonld.to_hdf(h5.metadata, data=jsonld)
            self.assertEqual(h5.metadata.person.attrs['first name'], 'Alexandra')
            self.assertEqual(h5.metadata.person.rdf.predicate['has ORCID ID'],
                             "http://w3id.org/nfdi4ing/metadata4ing#orcidId")
            self.assertEqual(h5.metadata.person.attrs['has ORCID ID'], '0000-0000-0123-4567')

        jsonld_str = h5tbx.dump_jsonld(
            h5.hdf_filename,
            context={"@import": "https://w3id.org/nfdi4ing/metadata4ing/m4i_context.jsonld"},
            resolve_keys=True
        )
        json_dict = json.loads(jsonld_str)
        print(jsonld_str)
        i = 0
        for g in json_dict['@graph']:
            if isinstance(g['@type'], list) and 'prov:Person' in g['@type']:
                i += 1
                self.assertEqual(g["foaf:firstName"], 'Alexandra')
                self.assertEqual(g["foaf:lastName"], 'Test')
                self.assertEqual(g["m4i:orcidId"], '0000-0000-0123-4567')
            elif isinstance(g['@type'], list) and 'schema:SoftwareSourceCode' in g['@type']:
                i += 1
                self.assertEqual(g['schema:softwareVersion'], "1.2.3a2")
        self.assertEqual(i, 2)

        jsonld_str = h5tbx.dump_jsonld(
            h5.hdf_filename,
            context={"@import": "https://w3id.org/nfdi4ing/metadata4ing/m4i_context.jsonld"},
            resolve_keys=False
        )
        json_dict = json.loads(jsonld_str)
        i = 0
        for g in json_dict['@graph']:
            if isinstance(g['@type'], list) and 'prov:Person' in g['@type']:
                i += 1
                self.assertEqual(g["first name"], 'Alexandra')
                self.assertEqual(g["last name"], 'Test')
                self.assertEqual(g["has ORCID ID"], '0000-0000-0123-4567')
                self.assertEqual(json_dict['@context']['first name'], str(rdflib.FOAF.firstName))
                self.assertEqual(json_dict['@context']['last name'], str(rdflib.FOAF.lastName))
                self.assertEqual(json_dict['@context']['has ORCID ID'], "http://w3id.org/nfdi4ing/metadata4ing#orcidId")
            elif isinstance(g['@type'], list) and 'schema:SoftwareSourceCode' in g['@type']:
                i += 1
                self.assertEqual(g['__h5rdmtoolbox_version__'], "1.2.3a2")
                self.assertEqual(json_dict['@context']['__h5rdmtoolbox_version__'],
                                 "https://schema.org/softwareVersion")
        self.assertEqual(i, 2)
