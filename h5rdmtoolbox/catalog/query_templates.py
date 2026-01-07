from typing import Union

import rdflib
from pydantic import HttpUrl, AnyUrl

from .core import SparqlQuery, RemoteSparqlQuery

GET_ALL_METADATA_CATALOG_DATASETS = SparqlQuery(
    query="""
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX spdx: <http://spdx.org/rdf/terms#>

SELECT ?dataset ?identifier ?download ?title ?checksumValue WHERE {
    ?dataset a dcat:Dataset ;
             dcterms:identifier ?identifier ;
             dcat:distribution ?dist .

    ?dist dcat:downloadURL ?download ;
          dcterms:title ?title ;
          dcat:mediaType ?media .

    OPTIONAL {
        ?dist spdx:checksum ?ck .
        ?ck spdx:checksumValue ?checksumValue .
    }

    FILTER(
        CONTAINS(LCASE(STR(?media)), "text/turtle") ||
        CONTAINS(LCASE(STR(?media)), "application/ld+json")
    )
}
""",
    description="Get all datasets in the catalog with their identifiers, download URLs, titles, and optional checksum values."
)


GET_ALL_WIKIDATA_ENTITIES = SparqlQuery(
    query="""SELECT DISTINCT ?wikidata_entity
WHERE {
  {
    ?wikidata_entity ?p ?o .
  }
  UNION
  {
    ?s ?p ?wikidata_entity .
  }

  FILTER(STRSTARTS(STR(?wikidata_entity), "http://www.wikidata.org/"))
}
""",
    description="Get all Wikidata entities that are instances of Wikimedia."
)


def get_wikidata_property_query(wikidata_entity: str) -> RemoteSparqlQuery:
    """
    Returns all direct triples (one-hop) for a Wikidata entity as (?property, ?value).
    Useful for importing into a local RDF store.

    Example inputs:
      - "Q131549102"
      - "wd:Q131549102"
      - "https://www.wikidata.org/wiki/Q131549102"
      - "http://www.wikidata.org/entity/Q131549102"
    """
    ent = str(wikidata_entity).strip()

    # Normalize to wd:Q... when possible
    if ent.startswith("http"):
        qid = ent.rsplit("/", 1)[-1]
        if qid.startswith("Q"):
            ent = f"wd:{qid}"
        else:
            ent = f"<{ent}>"
    elif ent.startswith("wd:"):
        pass
    elif ent.startswith("Q"):
        ent = f"wd:{ent}"
    else:
        # assume caller gave a valid SPARQL term already (e.g., <...> or prefix:name)
        ent = ent

    query = f"""
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX schema: <http://schema.org/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?property ?value
WHERE {{
  {ent} ?property ?value .

  # Optional: drop a few very common "plumbing" predicates that aren't useful to copy locally.
  # Comment this block out if you truly want everything.
  FILTER(?property NOT IN (
    rdf:type,
    schema:about,
    schema:isPartOf,
    wikibase:wikiGroup
  ))
}}
ORDER BY ?property ?value
"""
    return RemoteSparqlQuery(
        query=query,
        description=f"Direct property/value pairs for Wikidata entity {ent}"
    )


def get_properties(
        subject_uri: Union[str, HttpUrl, rdflib.URIRef],
        cls_uri: Union[str, HttpUrl, rdflib.URIRef] = None,
        limit: int = None
):
    """Returns a SPARQL query that selects all properties of the given subject URI. If cls_uri is provided,
    only properties for which the subject is of the given class are returned."""
    subject_uri = str(AnyUrl(subject_uri))
    if cls_uri is None:
        query_str = f"""
    PREFIX ssno: <https://matthiasprobst.github.io/ssno#>

    SELECT ?property ?value
    WHERE {{
        <{subject_uri}> ?property ?value .
    }}
    ORDER BY ?property
    """
    else:
        query_str = f"""
    SELECT ?property ?value
    WHERE {{
        <{subject_uri}> a {cls_uri} .
        <{subject_uri}> ?property ?value .
    }}
    ORDER BY ?property
    """
    if limit is not None:
        query_str += f"LIMIT {limit}\n"

    return SparqlQuery(
        query=query_str,
        description=f"Selects all properties of the target URI {subject_uri}"
    )

def get_distribution_to_hdf_dataset(
        hdf_dataset_uri: Union[str, HttpUrl, rdflib.URIRef]
):
    """Returns a SPARQL query that selects the distribution that represents a hdf:File, which contains
    a hdf:Dataset. Relation between File and RootGroup is hdf:rootGroup and between any Group and its member Datasets is hdf:member.
    This query assumes that the hdf:Dataset is uniquely contained in a single distribution."""
    hdf_dataset_uri = str(HttpUrl(hdf_dataset_uri))
    query_str = f"""
PREFIX hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#>
PREDIX dcat: <http://www.w3.org/ns/dcat#>
SELECT ?distribution ?downloadURL
WHERE {{
    ?distribution a dcat:Distribution ;
                  a hdf:File ;
                  dcat:downloadURL ?downloadURL ;
                  hdf:rootGroup ?rootGroup .

    ?rootGroup (hdf:member|^hdf:member)* <{hdf_dataset_uri}> .
}}
"""
    return SparqlQuery(
        query=query_str,
        description=f"Selects the distribution containing the HDF5 dataset {hdf_dataset_uri}"
    )