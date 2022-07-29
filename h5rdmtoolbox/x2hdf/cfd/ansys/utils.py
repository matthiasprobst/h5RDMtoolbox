import pathlib
import re


def change_suffix(filename: pathlib.Path, new_suffix: str) -> pathlib.Path:
    """Reads a filename (must not exist) and exchanges the suffix with the new given one"""
    filename = pathlib.Path(filename)
    if new_suffix[0] != '.':
        new_suffix = '.' + new_suffix
    return filename.parent.joinpath(f'{filename.stem}{new_suffix}')


def ansys_version_from_inst_dir(instdir: pathlib.Path) -> str:
    instdir = pathlib.Path(instdir)
    p = re.compile('v[0-9][0-9][0-9]')

    for part in instdir.parts:
        if p.match(part) is not None:
            return f'{part[1:3]}.{part[-1]}'
