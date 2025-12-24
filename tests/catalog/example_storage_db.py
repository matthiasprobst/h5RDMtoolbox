import pathlib
from typing import Type

import pandas as pd

from h5rdmtoolbox.catalog import DataStore, Query



class CSVDbQuery(Query):
    def __init__(self, query: str, description: str = None):
        super().__init__(query, description)
        self.query = query

    def execute(self, query, description=None, *args, **kwargs):
        raise NotImplementedError("CSVDbQuery does not support execution.")


class CSVDatabase(DataStore):

    def __init__(self):
        self._filenames = []
        self.tables = {}
        self._expected_file_extensions = {".csv", }

    @property
    def query(self) -> Type[CSVDbQuery]:
        return CSVDbQuery

    @property
    def expected_file_extensions(self):
        return self._expected_file_extensions

    def upload_file(self, filename) -> bool:
        filename = pathlib.Path(filename)
        assert filename.exists(), f"File {filename} does not exist."
        assert filename.suffix in self._expected_file_extensions, f"File type {filename.suffix} not supported"
        if filename.resolve().absolute() in self._filenames:
            return True
        self._filenames.append(filename.resolve().absolute())

        table_name = filename.name

        self.tables[table_name] = pd.read_csv(filename)
        return True

    def execute_query(self, query: Query):
        raise NotImplementedError("CSVDatabase does not support queries.")

    def get_all(self, table_name):
        return self.tables[table_name]
