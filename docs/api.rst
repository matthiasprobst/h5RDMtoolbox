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
   :toctree: _build/generated/

   h5rdmtoolbox.wrapper.core.File

Conventions
===========

Layouts
-------

.. autosummary::
    :toctree: generated/

    h5rdmtoolbox.conventions.layout.core.Layout
    h5rdmtoolbox.conventions.layout.validators.Equal
    h5rdmtoolbox.conventions.layout.validators.Regex
    h5rdmtoolbox.conventions.layout.validators.Any
    h5rdmtoolbox.conventions.layout.validators.ExistIn
    h5rdmtoolbox.conventions.layout.validators.In



Standard attributes
-------------------

.. autosummary::
   :toctree: _build/generated/

   h5rdmtoolbox.conventions.standard_attributes.StandardAttribute
   h5rdmtoolbox.conventions.standard_attributes.StandardAttribute.get
   h5rdmtoolbox.conventions.standard_attributes.StandardAttribute.set

Standard names and tables
-------------------------

.. autosummary::
   :toctree: _build/generated/

   h5rdmtoolbox.conventions.standard_names.name.StandardName
   h5rdmtoolbox.conventions.standard_names.table.StandardNameTable
   h5rdmtoolbox.conventions.standard_names.table.StandardNameTable.from_web
   h5rdmtoolbox.conventions.standard_names.table.StandardNameTable.from_yaml
   h5rdmtoolbox.conventions.standard_names.table.StandardNameTable.from_xml
   h5rdmtoolbox.conventions.standard_names.table.StandardNameTable.from_zenodo