MINIMUM_DATASET_SHACL = """
@prefix sh:    <http://www.w3.org/ns/shacl#> .
@prefix dcat:  <http://www.w3.org/ns/dcat#> .
@prefix spdx:  <http://spdx.org/rdf/terms#> .
@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .
@prefix ex:    <http://example.org/ns#> .

ex:DatasetShape
  a sh:NodeShape ;
  sh:targetClass dcat:Dataset ;
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