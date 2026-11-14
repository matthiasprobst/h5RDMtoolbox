# Testing

Install the src-layout project with `python -m pip install -e ".[test]"`.
Run `python -m pytest --cov=h5rdmtoolbox --cov-report=html` for broad validation,
or select an affected area. Python 3.10 through 3.13 is supported.

Fixtures isolate data/cache/log directories and restore configuration. Use
`tmp_path` for all generated files. The full suite can read public resources.
Wikidata requires `H5RDMTOOLBOX_RUN_WIKIDATA_TESTS=1`; live Zenodo uploads require
both `H5RDMTOOLBOX_RUN_ZENODO_UPLOAD_TESTS=1` and `ZENODO_SANDBOX_API_TOKEN`.
Ordinary CI has neither write tokens nor cleanup permissions. Mock-based cleanup
checks only permit explicitly supplied owned deposition IDs.

- `tests/test_readme_examples.py` executes the actual README code and compares RDF.
- `tests/ld/test_validation.py` tests layout replacements and zero-payload reads.
- `tests/wrapper/test_decoders.py` and `tests/database/test_calibration_policy.py`
  check calibrated/raw values and per-file/lazy policy propagation.
- `tests/catalog/test_validation_contract.py` checks explicitly requested validation.
- `tests/test_startup.py` checks lazy imports and first scientific use.
- `tests/test_distribution.py` builds an sdist and wheel, then imports outside the
  checkout; required build tools are in the test extra.

Use `python -m pylint src/h5rdmtoolbox --rcfile=.pylintrc` for linting and
`python -m sphinx -b html -D nb_execution_mode=off docs docs/_build/html` for docs.
