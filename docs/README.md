:orphan:

# Documentation

Run these commands from the repository root. First install the documentation dependencies:

```bash
pip install -e .[complete-with-docs]
```

Then build the HTML documentation, treating warnings as errors:

```bash
python -m sphinx -W -b html docs docs/_build/html
```

Open `docs/_build/html/index.html` in your browser.

To update the pdf, run

    python -m sphinx -b latex docs docs/_build/latex

and then run the generated make file in `docs/_build/latex` to build the PDF.

## Troubleshooting

* If the configured theme is missing, reinstall the documentation dependencies with
  `python -m pip install -e .[complete-with-docs]`.
* quickref of rst files: https://docutils.sourceforge.io/docs/user/rst/quickref.html
