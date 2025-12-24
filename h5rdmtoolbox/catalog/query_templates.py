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

get_all_wikidata_entities = SparqlQuery(
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
    """e.g. wd:Q131549102"""
    if str(wikidata_entity).startswith("http"):
        wikidata_entity = f"<{wikidata_entity}>"
    else:
        wikidata_entity = f"wd:{wikidata_entity}"
    query = f"""
SELECT * WHERE {{
   {wikidata_entity} ?property ?value .

  OPTIONAL {{
    ?value rdfs:label ?valueLabel .
    FILTER(LANG(?valueLabel) IN ("de", "en"))
  }}

  # literal values: keep only english
  FILTER(
    !isLiteral(?value) ||
    (isLiteral(?value) && LANG(?value) IN ("en"))
  )

  # remove rows where valueLabel is None
  FILTER(BOUND(?valueLabel))
}}
ORDER BY ?property
"""
    return RemoteSparqlQuery(query=query,
                             description=f"Searches all properties of Wikidata entity {wikidata_entity}")
