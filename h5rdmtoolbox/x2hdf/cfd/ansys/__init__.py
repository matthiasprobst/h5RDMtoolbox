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


from dataclasses import dataclass


@dataclass
class AnsysInstallation:
    """Ansys Installation class to manage exe files"""

    cfx5pre: pathlib.Path = None
    cfx5cmds: pathlib.Path = None
    cfx5mondata: pathlib.Path = None
    cfx5solve: pathlib.Path = None

    def __post_init__(self):
        dotenv.load_dotenv(CFX_DOTENV_FILENAME)
        self.cfx5pre = self.get('cfx5pre')
        self.cfx5cmds = self.get('cfx5cmds')
        self.cfx5mondata = self.get('cfx5mondata')
        self.cfx5solve = self.get('cfx5solve')
        self.inst_dir = self.installation_directory

    def set_installation_directory(self, inst_dir):
        dotenv.load_dotenv(CFX_DOTENV_FILENAME)
        inst_dir = pathlib.Path(inst_dir)
        if not inst_dir.is_dir():
            raise NotADirectoryError()
        if not inst_dir.exists():
            raise FileNotFoundError(inst_dir)
        self.inst_dir = inst_dir
        for name in ('cfxpre', 'cfx5cmds', 'cfx5mondata', 'cfx5solve'):
            self.set(name, self.inst_dir / name)

    @property
    def dotenv_values(self):
        dotenv.load_dotenv(CFX_DOTENV_FILENAME)
        return dotenv.dotenv_values(CFX_DOTENV_FILENAME)

    @property
    def installation_directory(self):
        dotenv.load_dotenv(CFX_DOTENV_FILENAME)
        for name in ('cfx5pre', 'cfx5cmds', 'cfx5mondata', 'cfx5solve'):
            if name in dotenv.dotenv_values(CFX_DOTENV_FILENAME):
                self.inst_dir = pathlib.Path(dotenv.dotenv_values(CFX_DOTENV_FILENAME)[name]).parent
                return self.inst_dir
        return None

    @installation_directory.setter
    def installation_directory(self, inst_dir):
        dotenv.load_dotenv(CFX_DOTENV_FILENAME)
        inst_dir = pathlib.Path(inst_dir)
        if not inst_dir.is_dir():
            raise NotADirectoryError()
        if not inst_dir.exists():
            raise FileNotFoundError(inst_dir)
        self.inst_dir = inst_dir
        for name in ('cfx5pre', 'cfx5cmds', 'cfx5mondata', 'cfx5solve'):
            self.set(name, inst_dir / name)

    def set(self, name_exe, exe_path):
        dotenv.load_dotenv(CFX_DOTENV_FILENAME)
        exe_path = pathlib.Path(exe_path)
        if not exe_path.exists():
            raise FileNotFoundError(exe_path)
        if not CFX_DOTENV_FILENAME.exists():
            with open(CFX_DOTENV_FILENAME, 'w'):
                pass
        dotenv.set_key(CFX_DOTENV_FILENAME, name_exe, str(exe_path))

    @staticmethod
    def get(name_exe):
        """Return the path to name_exe, where name_exe is e.g. cfx5pre"""
        dotenv.load_dotenv(CFX_DOTENV_FILENAME)
        _path = os.environ.get(name_exe)
        if _path is not None:
            return pathlib.Path(_path)
        return _path

    @property
    def version(self):
        dotenv.load_dotenv(CFX_DOTENV_FILENAME)
        return ansys_version_from_inst_dir(self.get('cfx5pre'))

# if CFX_DOTENV_FILENAME.exists():
#     from dotenv import load_dotenv
#
#     load_dotenv(CFX_DOTENV_FILENAME)
#
# _cfx5pre = os.environ.get("cfx5pre")
# if _cfx5pre is None:
#     raise CFXExeNotFound(f'Exe cfx5pre not found. Not registered as environment variable. You may register '
#                          'a variable permanently in your bashrc or here create a dotenv-file here: '
#                          f'{CFX_DOTENV_FILENAME}')
# _cfx5cmds = os.environ.get("cfx5cmds")
# if _cfx5cmds is None:
#     raise FileNotFoundError(f'cfx5cmds not found. Not registered as environment variable')
# _cfx5mondata = os.environ.get("cfx5mondata")
# if _cfx5mondata is None:
#     raise FileNotFoundError(f'cfx5mondata not found. Not registered as environment variable')
# CFX5PRE = pathlib.Path(_cfx5pre)
# CFX5CMDS = pathlib.Path(_cfx5cmds)
# CFX5MONDATA = pathlib.Path(_cfx5mondata)
# ANSYSVERSION = ansys_version_from_inst_dir(CFX5PRE)
#
# dotenv.load_dotenv(CFX_DOTENV_FILENAME)
