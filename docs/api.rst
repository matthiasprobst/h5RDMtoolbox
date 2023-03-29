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

CF-like wrapper class
=====================

.. autosummary::
   :toctree: generated/

   h5rdmtoolbox.wrapper.cflike.File

Conventions
===========

Standard attributes
-------------------

.. autosummary::
    :toctree: generated/

    h5rdmtoolbox.conventions.registration.StandardAttribute
    h5rdmtoolbox.conventions.registration.register_standard_attribute

Standard names and tables
-------------------------

.. autosummary::
   :toctree: generated/

   h5rdmtoolbox.conventions.cflike.StandardName
   h5rdmtoolbox.conventions.cflike.StandardNameTable
   h5rdmtoolbox.conventions.cflike.StandardNameTable.check_syntax
   h5rdmtoolbox.conventions.cflike.StandardNameTable.check_units
   h5rdmtoolbox.conventions.cflike.StandardNameTable.from_web
   h5rdmtoolbox.conventions.cflike.StandardNameTable.from_gitlab
   h5rdmtoolbox.conventions.cflike.StandardNameTable.from_yaml
   h5rdmtoolbox.conventions.cflike.StandardNameTable.from_xml
   h5rdmtoolbox.conventions.cflike.StandardNameTable.get_registered