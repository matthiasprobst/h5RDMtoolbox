IS_VALID_CATALOG_SHACL = """
@prefix sh:    <http://www.w3.org/ns/shacl#> .
@prefix dcat:  <http://www.w3.org/ns/dcat#> .
@prefix spdx:  <http://spdx.org/rdf/terms#> .
@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .
@prefix dcterms:   <http://purl.org/dc/terms/> .
@prefix ex:    <http://example.org/ns#> .

ex:CatalogShape
  a sh:NodeShape ;
  sh:targetClass dcat:Catalog ;
  
  sh:property [
    sh:path dcat:dataset ;
    sh:minCount 1 ;
    sh:node ex:DatasetShape ;
    sh:message "A dcat:Catalog must have at least one dcat:dataset, each conforming to DatasetShape." ;
  ] ;
  
  sh:property [
    sh:path dcat:version ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:message "A dcat:Catalog must have exactly one dcat:version." ;
  ] .

ex:DatasetShape
  a sh:NodeShape ;
  sh:targetClass dcat:Dataset ;
  
  # Require a dcterms:identifier
  sh:property [
    sh:path dcterms:identifier ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:message "A dcat:Dataset must have exactly one dcterms:identifier." ;
  ] ;

  sh:property [
    sh:path dcat:distribution ;
    sh:minCount 1 ;
    sh:node ex:DistributionShape ;
    sh:message "A dcat:Dataset must have at least one dcat:distribution, each conforming to DistributionShape." ;
  ] .


ex:DistributionShape
  a sh:NodeShape ;
  sh:targetClass dcat:Distribution ;

  # Require a downloadURL (IRI)
  sh:property [
    sh:path dcat:downloadURL ;
    sh:minCount 1 ;
    sh:nodeKind sh:IRI ;
    sh:message "A dcat:Distribution must have at least one dcat:downloadURL (IRI)." ;
  ] ;

  # Require a mediaType (IRI)
  sh:property [
    sh:path dcat:mediaType ;
    sh:minCount 1 ;
    sh:nodeKind sh:IRI ;
    sh:message "A dcat:Distribution must have at least one dcat:mediaType (IRI)." ;
  ] .

  # # Require at least one checksum (without structural validation)
  # sh:property [
  #   sh:path spdx:checksum ;
  #   sh:minCount 1 ;
  #   sh:message "A dcat:Distribution must have at least one spdx:checksum." ;
  # ] .
"""