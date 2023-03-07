# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

sys.path.insert(0, os.path.abspath('../..'))

# -- Project information -----------------------------------------------------

project = 'h5RDMtoolbox'
copyright = '2022, Matthias Probst'
author = 'Matthias Probst'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.napoleon',
              'sphinx.ext.viewcode',
              "IPython.sphinxext.ipython_directive",
              "IPython.sphinxext.ipython_console_highlighting",
              "sphinx_copybutton",
              "nbsphinx"]

nbsphinx_allow_errors = False

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', 'tests', '**.ipynb_checkpoints']

autodoc_member_order = 'bysource'

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_book_theme'  # 'sphinx_rtd_theme'

tml_context = {
    "github_user": "matthiasprobst",
    "github_repo": "h5RDMtoolbox",
    "github_version": "main",
    "doc_path": "doc",
}

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = dict(
    repository_url="https://github.com/matthiasprobst/h5RDMtoolbox",
    repository_branch="main",
    path_to_docs="doc",
    use_edit_page_button=False,
    use_repository_button=True,
    use_download_button=True,
    use_issues_button=True,
    home_page_in_toc=False,
    extra_navbar="",
    navbar_footer_text="",
)
# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
