RDF and SHACL
=============

RDF annotations describe files, groups, datasets and attributes. The structural
graph represents HDF5 names, membership, dimensions, datatypes and filters; the
contextual graph contains the semantic annotations. Export using ``ld.get_ld``
or file ``serialize`` methods. The CLI supports ``h5tbx ld dump example.h5``.

Validation is explicit and uses standard SHACL files or RDFLib graphs:

.. code-block:: python

   from h5rdmtoolbox.validation import validate
   report = validate("measurement.h5", "shapes.ttl")
   print(report.conforms)
   for violation in report.violations:
       print(violation.hdf_path, violation.messages)

Metadata-only validation reads no dataset payloads, including nested datasets
with contextual data predicates. Opt in to scalar values with
``include_scalar_values=True``. Array contents remain in scientific analysis.
Invalid input and engine failures raise exceptions; a failed constraint returns
a nonconforming report. Open file handles stay open and caller graphs are not
modified. Ontology inference defaults to ``none`` and can be enabled explicitly.

Example shape requiring every dataset to have a name:

.. code-block:: turtle

   @prefix sh: <http://www.w3.org/ns/shacl#> .
   @prefix hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#> .
   @prefix ex: <https://example.org/> .
   ex:NamedDataset a sh:NodeShape; sh:targetClass hdf:Dataset;
       sh:property [sh:path hdf:name; sh:minCount 1] .

Use qualified counts for required dataset paths, ``sh:or``/``sh:in`` for
alternatives, and SHACL-SPARQL for conditional cross-object requirements. The
regressions in ``tests/ld/test_validation.py`` provide executable examples.
