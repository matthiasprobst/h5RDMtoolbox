.. currentmodule:: h5rdmtoolbox

.. _api:

#############
API reference
#############

This page provides an overview of h5rdmtoolbox's most important API classes and functions.
For more details and examples, refer to the relevant chapters in the main part of the
documentation.

Core Classes
============

The main wrapper classes that provide the enhanced HDF5 interface.

.. autosummary::
   :toctree: generated/

   wrapper.core.File
   wrapper.core.Dataset
   wrapper.core.Group

Conventions
===========

Conventions allow you to define and enforce standardized attributes for your HDF5 files.

.. autosummary::
   :toctree: generated/

   convention.core.Convention
   convention.core.use
   convention.StandardAttribute

Attributes
==========

Attribute management for HDF5 objects.

.. autosummary::
   :toctree: generated/

   wrapper.h5attr.Attribute

Database
========

Query HDF5 files directly or via MongoDB.

.. autosummary::
   :toctree: generated/

   database.FileDB
   database.FilesDB

Repository
=========

Upload and manage HDF5 files in online repositories.

.. autosummary::
   :toctree: generated/

   repository.upload_file

Layout
======

Validate HDF5 file structure.

.. autosummary::
   :toctree: generated/

   layout.Layout

Linked Data
===========

Work with RDF metadata in HDF5 files.

.. autosummary::
   :toctree: generated/

   ld.shacl.validate_hdf
   ld.get_ld

Utilities
=========

General utility functions.

.. autosummary::
   :toctree: generated/
   :no-index:

   utils.generate_temporary_filename
   utils.has_datasets
   utils.has_groups
