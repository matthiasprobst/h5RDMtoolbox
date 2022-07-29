import logging
import os
from enum import Enum
from pathlib import Path

import dotenv

from . import CFX_DOTENV_FILENAME, CFX5MONDATA
from .cmd import call_cmd

dotenv.load_dotenv(CFX_DOTENV_FILENAME)

logger = logging.getLogger('__package__')


def generate_userpoints_file(target: Path) -> Path:
    """generates a user point CSV file"""

    target_filename = Path(target)
    if target_filename.suffix not in ('.res', '.dir'):
        raise ValueError('Can only perform user point extraction on *.res or *.dir file paths, '
                         f'but got {target_filename}')

    # target file is either *.res file or a dictionary *.dir in case simulation is still running
    basedir = target_filename.parent
    out_filename = Path.joinpath(basedir, "userpoints.csv")
    cmd = f'{CFX5MONDATA} -{target_filename.suffix[1:]} %{target_filename} -out %{out_filename}' \
          f' -nocoeffloops -varrule "CATEGORY = USER POINT"'
    if not out_filename.exists():
        raise RuntimeError(f'Failed running bash script "{cmd}"')
    os.system(cmd)
    return out_filename


class MonitorCategory(Enum):
    ALL = 1
    COMBINED = 2
    MONITOR = 3
    FORCE = 4
    IMBALANCE = 5
    MOMENT = 6
    USER_POINT = 7

    def __repr__(self):
        return f'{self.name.replace("_", " ")}'

    def __str__(self):
        return f'{self.name.replace("_", " ")}'


def get_monitor_data_by_category(target: Path, category: MonitorCategory = MonitorCategory.ALL,
                                 out: Path = 'userpoints.csv', units: bool = True) -> Path:
    """writes monitor data from a *.res or *.dir file to *.out file using the same base name"""

    target_filename = Path(target)

    if target_filename.suffix not in ('.res', '.dir'):
        raise ValueError('Can only perform user point extraction on *.res or *.dir file paths, '
                         f'but got {target_filename}')

    target_parent = target_filename.parent
    if out is None:
        out_filename = Path.joinpath(target_parent, 'userpoints.csv')
    else:
        out_filename = Path(out)

    _units = ''
    if units:
        _units = '-units'

    if category.value:  # ==1 ==ALL
        cmd = f'"{CFX5MONDATA}" -{target_filename.suffix[1:]} "{target_filename}" -out' \
              f' "{out_filename}" {_units}'
    else:
        cmd = f'"{CFX5MONDATA}" -{target_filename.suffix[1:]} "{target_filename}" ' \
              f'-varrule "CATEGORY = {str(category).replace("_", " ")}" -out {out_filename} {_units}'

    logger.info(f'Generating user points file from "{target_filename.name}"')
    logger.debug(f'Generating user points file with bash str: {cmd}')

    call_cmd(cmd, wait=True)
    if not out_filename.exists():
        raise RuntimeError(f'Failed running bash script "{cmd}"')

    return out_filename
