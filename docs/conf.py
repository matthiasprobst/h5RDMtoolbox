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
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

# -- Project information -----------------------------------------------------

project = "h5RDMtoolbox"
copyright = "2024, Matthias Probst"
author = "Matthias Probst"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "IPython.sphinxext.ipython_directive",
    "IPython.sphinxext.ipython_console_highlighting",
    "sphinx_copybutton",
    # "nbsphinx",
    "sphinx_design",
    "myst_nb",
    "sphinxcontrib.bibtex",
]

# Execute self-contained examples on every build in an isolated temporary
# directory. Examples that intentionally need network access, credentials,
# external services, or optional visualization packages retain their checked-in
# outputs and are explicitly excluded from execution.
nb_execution_mode = "force"
nb_execution_in_temp = True
nb_execution_timeout = 60
nb_execution_excludepatterns = [
    "**/gettingstarted/quickoverview.ipynb",
    "**/practical_examples/knowledge_graph.ipynb",
    "**/practical_examples/metadata4ing.ipynb",
    "**/practical_examples/nexus.ipynb",
    "**/practical_examples/photon_hdf5.ipynb",
    "**/userguide/catalog/catalog.ipynb",
    "**/userguide/convention/creating_a_new_convention.ipynb",
    "**/userguide/database/mongoDB.ipynb",
    "**/userguide/misc/Visualization.ipynb",
    "**/userguide/repository/zenodo.ipynb",
    "**/userguide/wrapper/FAIRAttributes.ipynb",
]

# These sites reject automated HEAD requests or are stale links inherited from
# h5py docstrings. They are not actionable documentation links in this project.
linkcheck_ignore = [
    r"https://en\.wikipedia\.org/.*",
    r"https://(?:portal|support)\.hdfgroup\.org/display/HDF5/.*",
]

# path to the bibtex file:
bibtex_bibfiles = ["references.bib"]

# Napoleon configurations
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_use_param = False
napoleon_use_rtype = False
napoleon_preprocess_types = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    "_build",
    "jupyter_execute",
    ".jupyter_cache",
    "README.md",
    "Thumbs.db",
    ".DS_Store",
    "tests",
    "userguide/ld/generated",
    "userguide/misc/generated",
    "**.ipynb_checkpoints",
    "colab",
    "webinars",
    "beyond/Validation-with-SHACL.ipynb",
]

autodoc_member_order = "bysource"

autosummary_generate = True
autodoc_typehints = "none"

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_book_theme"  # 'sphinx_rtd_theme'
html_logo = "_static/new_icon.svg"
html_title = "h5RDMtoolbox Documentation"

html_context = {
    "github_user": "matthiasprobst",
    "github_repo": "h5RDMtoolbox",
    "github_version": "main",
    "doc_path": "docs",
    "default_mode": "light",
}

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = dict(
    repository_url="https://github.com/matthiasprobst/h5RDMtoolbox",
    repository_branch="main",
    path_to_docs="docs",
    use_edit_page_button=False,
    use_repository_button=True,
    use_download_button=True,
    use_issues_button=True,
    home_page_in_toc=False,
)
# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
