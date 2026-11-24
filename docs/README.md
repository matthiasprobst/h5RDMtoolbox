:orphan:

# Documentation

Run these commands from the repository root with Python 3.10 or newer (required
by the pinned Sphinx 8.0.0 and the base package).
First install the documentation dependencies:

```bash
pip install -e .[complete-with-docs]
```

Then build the HTML documentation, treating warnings as errors:

```bash
python -m sphinx -W -b html docs docs/_build/html
```

Open `docs/_build/html/index.html` in your browser.

The knowledge graph notebook is excluded from execution during documentation
builds. To refresh its interactive outputs after editing it, install `pyvis`,
execute the notebook in Jupyter, and save it with both graph outputs present.
The graphs embed their visualization resources rather than linking to generated
files in the notebook's working directory.

To update the pdf, run

    python -m sphinx -b latex docs docs/_build/latex

and then run the generated make file in `docs/_build/latex` to build the PDF.

## Troubleshooting

* If the configured theme is missing, reinstall the documentation dependencies with
  `python -m pip install -e .[complete-with-docs]`.
* quickref of rst files: https://docutils.sourceforge.io/docs/user/rst/quickref.html
