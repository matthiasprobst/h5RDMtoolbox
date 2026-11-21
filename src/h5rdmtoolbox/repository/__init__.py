import pathlib
from typing import Union

from .interface import RepositoryInterface


def upload_file(repo: RepositoryInterface,
                filename: Union[str, pathlib.Path],
                **kwargs) -> None:
    """Upload a file to the repository."""
    repo.upload_file(filename,  **kwargs)
