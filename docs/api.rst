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

   wrapper.core.File
   wrapper.core.Dataset
   wrapper.core.Group
   wrapper.core.Group.create_from_yaml

Conventions
===========

Layouts
-------

.. autosummary::
    :toctree: generated/

    layout.core.LayoutSpecification
    layout.core.Layout



Standard attributes
-------------------

.. autosummary::
   :toctree: generated/

   convention.StandardAttribute
   convention.StandardAttribute.get
   convention.StandardAttribute.set

Standard names and tables
-------------------------

.. autosummary::
   :toctree: generated/

   convention.standard_names.name.StandardName
   convention.standard_names.table.StandardNameTable
   convention.standard_names.table.StandardNameTable.from_web
   convention.standard_names.table.StandardNameTable.from_yaml
   convention.standard_names.table.StandardNameTable.from_xml
   convention.standard_names.table.StandardNameTable.from_zenodo