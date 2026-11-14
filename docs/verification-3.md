# 3.0 implementation verification

## Functional checks

The full suite on Windows/Python 3.12.4 passed with **417 passed, 24 skipped**
and 68% statement coverage under the repository coverage configuration. This
includes the README examples, raw RDF storage contract, calibration policies,
SHACL layouts, catalog integration, and an sdist-built wheel exercised outside
the checkout. The skipped cases include external-service opt-ins and platform
conditions; live Zenodo uploads were not enabled. Other supported Python versions
and operating systems remain for the GitHub Actions matrix to verify.

Pylint remains nonzero: 8.74/10 versus the captured 2.9.0 baseline of 8.75/10.
Existing diagnostics remain, and splitting wrappers changes some type-inference
warnings. This is not a lint-clean release. The documentation build uses Sphinx
with warnings treated as errors and notebook execution disabled; legacy notebooks
are excluded from the 3.0 build.

## Performance evidence

Measured on Windows with CPython 3.12.4.
Nine fresh processes per version, alternating baseline/new order, isolated application
directories, identical interpreter and installed dependencies. Baseline: v2.9.0.
The fixture contains one 1000 x 200 float dataset. Memory is Windows peak working set.
Timings are medians in seconds; repeated workloads are totals for the stated count.

| Measurement | v2.9.0 | 3.0 implementation | Change |
| --- | ---: | ---: | ---: |
| import | 7.8421 | 0.1404 | -98.2% |
| import_peak_mib | 205.1133 | 24.4141 | -88.1% |
| first_scientific_use | 0.0107 | 3.0536 | +28435.1% |
| slicing_100 | 0.0905 | 0.1115 | +23.1% |
| rdf_10 | 0.0742 | 0.0952 | +28.3% |
| first_validation | 0.0934 | 0.0787 | -15.8% |
| shacl_100 | 0.1441 | 0.1988 | +38.0% |
| catalog_10 | 0.1157 | 0.1096 | -5.2% |
| import_plus_first_use | 7.8568 | 3.1198 | -60.3% |
| peak_mib | 208.8789 | 198.8125 | -4.8% |

Plain import and combined import/first scientific use improve substantially.
First-use time alone increases because heavy dependencies are now loaded there.
Peak memory after all measured features falls from about 209 MiB to 199 MiB.

The measured slicing, RDF extraction, and repeated SHACL validation times exceed
the 10% regression target on this fixture. Earlier measurements of slicing and
RDF extraction varied substantially; these local timings do not establish
cross-platform performance. Repeated SHACL validation adds approximately 0.55 ms
per call on the small graph used here. No timing threshold is enforced in CI.

The CLI already deferred package loading in 2.9.0. Separate nine-process CLI
help medians were 1.193 s and 1.224 s, including process and test-runner startup.
