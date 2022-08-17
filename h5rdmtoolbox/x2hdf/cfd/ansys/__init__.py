import logging
import os
import pathlib
from typing import Union

import dotenv

from .utils import ansys_version_from_inst_dir
from ...._user import user_config_dir

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
    raise CFXExeNotFound(f'Exe cfx5pre not found. Not registered as environment variable. You may register '
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


class AnsysInstallation:
    """Ansys Installation class to manage exe files"""

    def __init__(self):
        dotenv.load_dotenv(CFX_DOTENV_FILENAME)

    @staticmethod
    def get_exe(name_exe):
        """Return the path to name_exe, where name_exe is e.g. cfx5pre"""
        _path = os.environ.get(name_exe)
        if _path is None:
            raise CFXExeNotFound(f'Exe {name_exe} not found. Not registered as environment variable. You may register '
                                 'a variable permanently in your bashrc or here create a dotenv-file here: '
                                 f'{CFX_DOTENV_FILENAME}')

    @property
    def version(self):
        return ansys_version_from_inst_dir(self.get_exe('cfx5pre'))

    @property
    def cfx5pre(self):
        return self.get_exe('cfx5pre')

    @property
    def cfx5cmds(self):
        return self.get_exe('cfx5cmds')

    @property
    def cfx5mondata(self):
        return self.get_exe('cfx5mondata')
