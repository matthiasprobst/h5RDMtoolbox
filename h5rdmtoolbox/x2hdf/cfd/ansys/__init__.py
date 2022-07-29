import logging
import os
import pathlib
from typing import Union

import dotenv

from .utils import ansys_version_from_inst_dir
from .... import user_config_dir

logger = logging.getLogger('cfdtoolkit')

PATHLIKE = Union[str, bytes, os.PathLike, pathlib.Path]

CFX_DOTENV_FILENAME = user_config_dir / 'cfx.env'
SESSIONS_DIR = pathlib.Path(__file__).parent.joinpath('session_files')


class CFXExeNotFound(FileNotFoundError):
    """raised if exe not found"""
    pass


if CFX_DOTENV_FILENAME.exists():
    from dotenv import load_dotenv
    load_dotenv(CFX_DOTENV_FILENAME)

_cfx5pre = os.environ.get("cfx5pre")
if _cfx5pre is None:
    raise CFXExeNotFound(f'Exe cfx5pre not found. Not registered as environment variable. You may refister '
                         'a variable permanently in your bashrc or here create a dotenv-file here: '
                         f'{CFX_DOTENV_FILENAME}')
_cfx5cmds = os.environ.get("cfx5cmds")
if _cfx5cmds is None:
    raise FileNotFoundError(f'cfx5cmds not found. Not registered as environment variable')
_cfx5mondata = os.environ.get("cfx5mondata")
if _cfx5mondata is None:
    raise FileNotFoundError(f'cfx5mondata not found. Not registered as environment variable')
CFX5PRE = pathlib.Path(_cfx5pre)
CFX5CMDS = pathlib.Path(_cfx5cmds)
CFX5MONDATA = pathlib.Path(_cfx5mondata)
ANSYSVERSION = ansys_version_from_inst_dir(CFX5PRE)

dotenv.load_dotenv(CFX_DOTENV_FILENAME)
