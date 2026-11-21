"""SQLite-backed HDF5 references and their RDF resource descriptions."""

import json
import logging
import pathlib
import sqlite3
from dataclasses import dataclass
from typing import Any, Union

import rdflib
from ontolutils.ex import dcat

from ..abstracts import DataStore
from ..queries import QueryResult, SQLQuery

logger = logging.getLogger("h5rdmtoolbox.catalog")


@dataclass
class DatabaseResource:
    """Stored resource identifier and its RDF metadata graph."""

    identifier: Any
    metadata: rdflib.Graph

    def serialize(self, format, **kwargs) -> str:
        return self.metadata.serialize(format=format, **kwargs)


class HDF5SqlDB(DataStore):
    """
    HDF5SQLDB is a SQL database interface that stores data in HDF5 files.
    """

    def __init__(
        self,
        data_dir: Union[str, pathlib.Path],
        db_path: Union[str, pathlib.Path] = None,
    ):
        if data_dir is not None and db_path is not None:
            raise ValueError("Specify either data_dir or db_path, not both.")
        if db_path is not None:
            db_path = pathlib.Path(db_path).resolve().absolute()
            if not db_path.exists():
                db_path.parent.mkdir(parents=True, exist_ok=True)
                db_path.touch()
            if not db_path.is_file():
                raise ValueError(f"Database path {db_path} is not a file.")
        else:
            data_dir = pathlib.Path(data_dir).resolve().absolute()
            assert data_dir.exists(), f"Data directory {data_dir} does not exist."
            assert data_dir.is_dir(), f"Data directory {data_dir} is not a directory."
            db_path = data_dir / "hdf5_files.db"

        self._hdf5_file_table_name = "hdf5_files"
        self._sql_base_uri = "http://local.org/sqlite3/"
        self._db_path = db_path
        self._endpointURL = rf"file://{self._db_path}"
        self._connection = self._initialize_database(self._db_path)
        self._filenames = {}
        self._expected_file_extensions = {".hdf", ".hdf5", ".h5"}

    def __repr__(self):
        return f"<{self.__class__.__name__} (Endpoint URL={self._endpointURL})>"

    def _upload_file(
        self, filename, validate: bool = False, skip_unsupported: bool = False
    ) -> DatabaseResource:
        _id = self._insert_hdf5_reference(self._connection, filename)
        return DatabaseResource(_id, metadata=self.generate_mapping_dataset(str(_id)))

    def execute_query(self, query: SQLQuery) -> QueryResult:
        cursor = self._connection.cursor()
        params = []

        if query.filters:
            for key, value in query.filters.items():
                query += f" AND {key} = ?"
                params.append(value)

        cursor.execute(query.sql_query, params)
        return cursor.fetchall()

    def _initialize_database(self, db_path: Union[str, pathlib.Path] = "hdf5_files.db"):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {self._hdf5_file_table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        )
        """)
        conn.commit()
        return conn

    def reset(self):
        logger.info(
            f"Resetting the database. Dropping table {self._hdf5_file_table_name}."
        )
        cursor = self._connection.cursor()
        cursor.execute(f"DROP TABLE {self._hdf5_file_table_name}")
        self._initialize_database(self._db_path)

    @classmethod
    def _insert_hdf5_reference(cls, conn, filename, metadata=None):
        filename = pathlib.Path(filename).resolve().absolute()
        cursor = conn.cursor()
        metadata_dump = json.dumps(metadata) or "{}"
        try:
            cursor.execute(
                """
            INSERT INTO hdf5_files (file_path, metadata)
            VALUES (?, ?)
            """,
                (str(filename), metadata_dump),
            )
            conn.commit()
            generated_id = cursor.lastrowid
            logger.debug(f"File {filename} inserted successfully.")
            return generated_id
        except sqlite3.IntegrityError:
            logger.error(f"File {filename} already exists.")

    def __del__(self):
        """Ensure the connection is closed when the object is deleted."""
        if self._connection:
            self._connection.close()

    def generate_data_service_serving_a_dataset(self, dataset_identifier: str):
        endpoint_url = self._endpointURL
        endpoint_url_file_name = endpoint_url.rsplit("/", 1)[-1]
        dataservice_id = f"{self._sql_base_uri}{endpoint_url_file_name}"
        data_service = dcat.DataService(
            id=dataservice_id,
            title="sqlite3 Database",
            endpointURL=endpoint_url,
            servesDataset=dcat.Dataset(
                id=f"{self._sql_base_uri}table/{self._hdf5_file_table_name}",
                title=f"SQL Table '{self._hdf5_file_table_name}'",
                identifier=self._hdf5_file_table_name,
                distribution=dcat.Distribution(
                    id=f"{self._sql_base_uri}12345",
                    identifier=dataset_identifier,
                    mediaType="application/vnd.sqlite3",
                ),
            ),
        )
        return data_service

    def generate_mapping_dataset(self, dataset_identifier: str):
        data_service = self.generate_data_service_serving_a_dataset(dataset_identifier)
        return rdflib.Graph().parse(
            data=data_service.model_dump_jsonld(), format="json-ld"
        )
