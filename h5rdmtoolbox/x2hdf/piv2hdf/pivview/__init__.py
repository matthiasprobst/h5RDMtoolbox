"""
Snapshot: A *.nc file
Plane: Multiple *.nc file in a folder (one measurement plane)
Case: Multiple Plane folders (multiple planes)
"""



from .snapshot import PIVSnapshot
from .plane import PIVPlane, PIVMultiPlane

__all__ = ['PIVSnapshot', 'PIVPlane', 'PIVMultiPlane']
