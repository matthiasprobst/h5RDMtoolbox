"""Public API for explicit SHACL validation of HDF5 metadata and RDF graphs."""

from .results import ValidationResult, Violation
from .service import validate

__all__ = ["validate", "ValidationResult", "Violation"]
