"""
Snapshot: A *.nc file
Plane: Multiple *.nc file in a folder (one measurement plane)
Case: Multiple Plane folders (multiple planes)
"""

from .plane import PIVPlane, PIVMultiPlane
from .snapshot import PIVSnapshot

__all__ = ['PIVSnapshot', 'PIVPlane', 'PIVMultiPlane']
