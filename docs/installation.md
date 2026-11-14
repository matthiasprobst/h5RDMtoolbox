# Installation

Python 3.15 compatibility is experimental. CI tests it separately; current
scientific dependencies may require source builds, including h5py.

Python 3.10 through 3.14 is supported. The current documentation describes the
unreleased 3.0 API. To work with this version, clone the repository, check out the
3.0 development branch, and install from the repository root:

```bash
python -m pip install -e .
```

Optional dependencies can be installed with the following extras:

| Extra | Purpose | Development installation |
| --- | --- | --- |
| `catalog` | Catalog stores and SPARQL clients | `python -m pip install -e ".[catalog]"` |
| `notebook` | Rich notebook display | `python -m pip install -e ".[notebook]"` |
| `test` | Test and analysis dependencies | `python -m pip install -e ".[test]"` |
| `docs` | Sphinx documentation tools | `python -m pip install -e ".[docs]"` |

`python -m pip install h5RDMtoolbox` installs the published release. Use its
versioned documentation for existing 2.x workflows, or follow the
[migration guide](migration-3.md) to adapt them to 3.0.
