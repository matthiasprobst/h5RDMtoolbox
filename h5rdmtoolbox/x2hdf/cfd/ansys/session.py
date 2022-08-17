import logging
import os
import pathlib
import shutil
import tempfile
from typing import Union

from . import PATHLIKE, AnsysInstallation
from . import logger
from .cmd import call_cmd
from .utils import change_suffix

logger = logging.getLogger('x2hdf')

SESSIONS_DIR = pathlib.Path(__file__).parent.joinpath('session_files')


def importccl(cfx_filename: PATHLIKE, ccl_filename: Union[PATHLIKE, None] = None,
              ansys_version: str = None) -> pathlib.Path:
    """imports a .ccl file into a .cfx file"""
    if ansys_version is None:
        ansys_version = AnsysInstallation().version
    if ccl_filename is None:
        ccl_filename = change_suffix(cfx_filename, '.ccl')
    cfx_filename = pathlib.Path(cfx_filename)
    if not cfx_filename.exists():
        raise FileExistsError(f'CFX case file (.cfx) not found: {cfx_filename}')
    if not ccl_filename.exists():
        raise FileExistsError(f'CCL file (.ccl) not found: {cfx_filename}')

    logger.debug(f'Importing ccl file into case file: "{ccl_filename} --> {cfx_filename}')

    mtime_before = cfx_filename.stat().st_mtime
    _orig_session_filename = SESSIONS_DIR.joinpath('importccl.pre')
    _tmp_session_filename = copy_session_file_to_tmp(_orig_session_filename)
    replace_in_file(_tmp_session_filename, '__cfxfilename__', str(cfx_filename))
    replace_in_file(_tmp_session_filename, '__cclfilename__', str(ccl_filename))
    replace_in_file(_tmp_session_filename, '__version__', ansys_version)

    play_session(_tmp_session_filename)
    # now check if .cfx file modification time has changed
    if cfx_filename.stat().st_mtime <= mtime_before:
        raise ValueError('Failed importing ccl file')
    return cfx_filename


def cfx2def(cfx_filename: PATHLIKE, def_filename: Union[PATHLIKE, None] = None,
            ansys_version: str = None) -> pathlib.Path:
    if ansys_version is None:
        ansys_version = AnsysInstallation().version
    if def_filename is None:
        def_filename = cfx_filename.parent.joinpath(f'{cfx_filename.stem}.def')

    _orig_session_filename = SESSIONS_DIR.joinpath('cfx2def.pre')
    _tmp_session_filename = copy_session_file_to_tmp(_orig_session_filename)
    replace_in_file(_tmp_session_filename, '__cfxfilename__', str(cfx_filename))
    replace_in_file(_tmp_session_filename, '__deffilename__', str(def_filename))
    replace_in_file(_tmp_session_filename, '__version__', ansys_version)
    play_session(_tmp_session_filename, wait=True)
    return def_filename


def change_timestep_and_write_def(cfx_filename: PATHLIKE, def_filename: PATHLIKE, timestep: float,
                                  ansys_version: str = None):
    """changes timestep in *.cfx fil and writes solver file *.def"""
    if ansys_version is None:
        ansys_version = AnsysInstallation().version
    _orig_session_filename = SESSIONS_DIR.joinpath('change_timestep_and_write_def.pre')
    _tmp_session_filename = copy_session_file_to_tmp(_orig_session_filename)
    replace_in_file(_tmp_session_filename, '__cfxfilename__', str(cfx_filename))
    replace_in_file(_tmp_session_filename, '__timestep__', str(timestep))
    replace_in_file(_tmp_session_filename, '__deffilename__', str(def_filename))
    replace_in_file(_tmp_session_filename, '__version__', ansys_version)
    play_session(_tmp_session_filename)


def change_timestep(cfx_filename: PATHLIKE, timestep: float,
                    ansys_version: str = None):
    """changes timestep in *.cfx file. DOES NOT WRITE THE *.DEF FILE!"""
    if ansys_version is None:
        ansys_version = AnsysInstallation().version
    _orig_session_filename = SESSIONS_DIR.joinpath('change_timestep.pre')
    _tmp_session_filename = copy_session_file_to_tmp(_orig_session_filename)
    replace_in_file(_tmp_session_filename, '__cfxfilename__', str(cfx_filename))
    replace_in_file(_tmp_session_filename, '__timestep__', str(timestep))
    replace_in_file(_tmp_session_filename, '__version__', ansys_version)
    play_session(_tmp_session_filename)


def random_tmp_filename(ext=''):
    """Generates a random file path in directory strudaset/.tmp with filename tmp****.hdf where **** are random
    numbers. The file path is returned but the file itself is not created until used.

    Returns
    --------
    random_fpath: `string`
        random file path
    """

    if not ext == '':
        if "." not in ext:
            ext = f'.{ext}'

    tmpdir = pathlib.Path(tempfile.TemporaryDirectory().name)
    if not tmpdir.exists():
        tmpdir.mkdir()
    random_fpath = tmpdir.joinpath(f"tmp{ext}")
    while os.path.isfile(random_fpath):
        random_fpath = tmpdir.joinpath(f"tmp{ext}")

    return random_fpath


def copy_session_file_to_tmp(session_filename: PATHLIKE) -> PATHLIKE:
    """copies `session_filename` to user temp directory where
    it is stored under a random filename"""
    random_fpath = random_tmp_filename(".pre")
    src = session_filename
    dest = random_fpath
    logger.debug(f'Copying {src} to {dest}')
    shutil.copy2(src, dest)
    return random_fpath


def replace_in_file(filename, keyword, new_string):
    """replaces keyword with 'new_string'. If keyword appears
    multiple times, it is replaced multiple times."""
    new_string = str(new_string)

    with open(filename) as f:
        s = f.read()
        if keyword not in s:
            raise KeyError('"{keyword}" not found in {filename}.'.format(**locals()))

    with open(filename, 'w') as f:
        logger.debug('Changing "{keyword}" to "{new_string}" in {filename}'.format(**locals()))
        s = s.replace(keyword, new_string)
        f.write(s)


def play_session(session_file: PATHLIKE,
                 cfx5pre: Union[PATHLIKE, None] = None,
                 wait: bool = True) -> None:
    """
<<<<<<< HEAD
    Runs AnsysInstallation().cfx5pre session file
=======
    Runs cfx5pre session file
>>>>>>> dev-cfx2hdf

    Parameters
    ----------
    AnsysInstallation().cfx5pre : Union[str, bytes, os.PathLike, pathlib.Path], optional
        path to AnsysInstallation().cfx5pre exe.
        Default takes from config file
    """
    if cfx5pre is None:
        _cfx5path = AnsysInstallation().cfx5pre
    else:
        _cfx5path = pathlib.Path(cfx5pre)

    if not _cfx5path.exists():
        raise FileExistsError(f'Could not find cfx5pre exe here: {_cfx5path}')

    session_file = pathlib.Path(session_file)

    cmd = f'"{_cfx5path}" -batch "{session_file}"'
    call_cmd(cmd, wait=wait)
    return cmd
