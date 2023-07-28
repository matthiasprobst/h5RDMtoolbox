try:
    from importlib.metadata import version as _version
except ImportError as e:
    raise ImportError('Most likely you have python<3.8 installed. At least 3.8 is required.') from e

__version__ = _version('h5rdmtoolbox')
