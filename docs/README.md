# Documentation

Make sure to have installed all required dependencies in order to 
build the documentation
```bash
pip install -e "h5rdmtoolbox[docs]"
```

https://www.sphinx-doc.org/en/master/usage/installation.html

Run

    make clean

to remove the build directory.

Next, run

    sphinx-build -b html . _build

to create `index.html` in the `_build/` folder (You may need to install the theme first: `pip install sphinx_rtd_theme`)

To update the pdf, run

    sphinx-build -b latex . _build

and after that run the make file in the source folder to build the actual pdf.

View `_build/index.html` with your browser.

## Generating docs for github:

    make.bat github

## Troubleshooting

* error message: ```no theme named 'sphinx_rtd_theme' found (missing theme.conf?)```
  <br>Maybe theme is not installed. Try: ```python3 -m pip install sphinx_rtd_theme```
* quickref of rst files: https://docutils.sourceforge.io/docs/user/rst/quickref.html