.. currentmodule:: h5rdmtoolbox

.. _api:

#############
API reference
#############

This page provides an auto-generated summary of h5rdmtoolbox's API. For more details
and examples, refer to the relevant chapters in the main part of the
documentation.

Base wrapper class
==================

.. autosummary::
   :toctree: generated/

   h5rdmtoolbox.wrapper.core.File

Conventions
===========

Layouts
-------

.. autosummary::
    :toctree: generated/

    h5rdmtoolbox.layout.core.LayoutSpecification
    h5rdmtoolbox.layout.core.Layout



Standard attributes
-------------------

.. autosummary::
   :toctree: generated/

   h5rdmtoolbox.convention.StandardAttribute
   h5rdmtoolbox.convention.StandardAttribute.get
   h5rdmtoolbox.convention.StandardAttribute.__setter__

Standard names and tables
-------------------------

.. autosummary::
   :toctree: generated/

   h5rdmtoolbox.convention.standard_names.name.StandardName
   h5rdmtoolbox.convention.standard_names.table.StandardNameTable
   h5rdmtoolbox.convention.standard_names.table.StandardNameTable.from_web
   h5rdmtoolbox.convention.standard_names.table.StandardNameTable.from_yaml
   h5rdmtoolbox.convention.standard_names.table.StandardNameTable.from_xml
   h5rdmtoolbox.convention.standard_names.table.StandardNameTable.from_zenodo