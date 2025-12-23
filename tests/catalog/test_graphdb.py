from unittest.mock import MagicMock
from unittest.mock import patch, Mock

import pandas as pd
import pytest

from h5rdmtoolbox.catalog.query.metadata_query import RemoteSparqlQuery
from h5rdmtoolbox.catalog.stores import GraphDB


def make_graphdb():
    return GraphDB(endpoint="http://localhost:7200",
                   repository="testrepo",
                   username="user",
                   password="pass")


@patch.object(GraphDB, "get_repository_info", return_value={})
@patch("requests.post")
def test_upload_file_success(mock_post, mock_repo_info, tmp_path):
    # Erfolgreicher Upload
    test_file = tmp_path / "test.ttl"
    test_file.write_text("@prefix ex: <http://example.org/> . ex:a ex:b ex:c .")
    mock_post.return_value = Mock(status_code=204)
    db = make_graphdb()
    assert db.upload_file(test_file) is True
    mock_post.assert_called_once()


@patch.object(GraphDB, "get_repository_info", return_value={})
@patch("requests.post")
def test_upload_file_not_found(mock_post, mock_repo_info):
    db = make_graphdb()
    with pytest.raises(FileNotFoundError):
        db.upload_file("notfound.ttl")
    mock_post.assert_not_called()


@patch.object(GraphDB, "get_repository_info", return_value={})
@patch("requests.post")
def test_upload_file_wrong_format(mock_post, mock_repo_info, tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("dummy")
    db = make_graphdb()
    with pytest.raises(ValueError):
        db.upload_file(test_file)
    mock_post.assert_not_called()


@patch.object(GraphDB, "get_repository_info", return_value={})
@patch("requests.post")
def test_upload_file_server_error(mock_post, mock_repo_info, tmp_path):
    test_file = tmp_path / "test.ttl"
    test_file.write_text("@prefix ex: <http://example.org/> . ex:a ex:b ex:c .")
    mock_post.return_value = Mock(status_code=500, text="Internal Server Error")
    db = make_graphdb()
    with pytest.raises(RuntimeError):
        db.upload_file(test_file)
    mock_post.assert_called_once()


@patch.object(GraphDB, "get_repository_info", return_value={})
def test_select_all(mock_repo_info):
    # SELECT_ALL als RemoteSparqlQuery
    SELECT_ALL = RemoteSparqlQuery(
        "SELECT * WHERE { ?s ?p ?o }",
        description="Selects all triples in the RDF database"
    )
    db = make_graphdb()

    # Replace the wrapper on the instance with a mock
    fake = MagicMock()
    fake.queryAndConvert.return_value = {
        "head": {"vars": ["s", "p", "o"]},
        "results": {
            "bindings": [
                {"s": {"value": "s1"}, "p": {"value": "p1"}, "o": {"value": "o1"}},
                {"s": {"value": "s2"}, "p": {"value": "p2"}, "o": {"value": "o2"}},
            ]
        },
    }
    db._wrapper = fake

    result = SELECT_ALL.execute(db)
    pd.testing.assert_frame_equal(
        result.data,
        pd.DataFrame(
            {
                "s": ["s1", "s2"],
                "p": ["p1", "p2"],
                "o": ["o1", "o2"],
            }
        )
    )
    # assert result.data["results"]["bindings"] == [
    #     {"s": {"value": "s1"}, "p": {"value": "p1"}, "o": {"value": "o1"}},
    #     {"s": {"value": "s2"}, "p": {"value": "p2"}, "o": {"value": "o2"}},
    # ]
    fake.setQuery.assert_called_once_with("SELECT * WHERE { ?s ?p ?o }")
    fake.queryAndConvert.assert_called_once()
