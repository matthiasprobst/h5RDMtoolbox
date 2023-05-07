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
   h5rdmtoolbox.wrapper.core.File.check

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
    :toctree: generated/

    h5rdmtoolbox.conventions.standard_attribute.StandardAttribute
    h5rdmtoolbox.conventions.standard_attribute.StandardAttribute.get
    h5rdmtoolbox.conventions.standard_attribute.StandardAttribute.set

Standard names and tables
-------------------------

.. autosummary::
   :toctree: generated/

   h5rdmtoolbox.conventions.standard_name.StandardName
   h5rdmtoolbox.conventions.standard_name.StandardNameTable
   h5rdmtoolbox.conventions.standard_name.StandardNameTable.check_syntax
   h5rdmtoolbox.conventions.standard_name.StandardNameTable.check_units
   h5rdmtoolbox.conventions.standard_name.StandardNameTable.from_web
   h5rdmtoolbox.conventions.standard_name.StandardNameTable.from_gitlab
   h5rdmtoolbox.conventions.standard_name.StandardNameTable.from_yaml
   h5rdmtoolbox.conventions.standard_name.StandardNameTable.from_xml
   h5rdmtoolbox.conventions.standard_name.StandardNameTable.get_registered