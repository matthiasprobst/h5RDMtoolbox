"""Catalog initialization entry points share parsing and download behavior."""
from unittest.mock import Mock

import pytest

from h5rdmtoolbox.catalog import database_initialization, utils


@pytest.mark.parametrize('initialize', [database_initialization, utils.database_initialization])
def test_metadata_downloads_use_shared_configuration(tmp_path, monkeypatch, capsys, initialize):
    config = tmp_path / 'catalog.ttl'
    config.write_text('''
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
<https://example.org/dataset> a dcat:Dataset ;
    dcterms:identifier "sample" ;
    dcat:distribution [
        dcat:downloadURL <https://example.org/metadata.ttl> ;
        dcterms:title "metadata.ttl" ;
        dcat:mediaType "text/turtle"
    ] .
''', encoding='utf-8')
    download = Mock(return_value=['download-result'])
    monkeypatch.setattr(utils, 'download', download)

    assert initialize(config, tmp_path) == ['download-result']
    download.assert_called_once()
    options = download.call_args.kwargs
    assert options['download_directory'] == tmp_path
    resource, = options['web_resources']
    assert str(resource.download_url) == 'https://example.org/metadata.ttl'
    assert str(resource.identifier) == 'sample'
    assert capsys.readouterr().out == ''


@pytest.mark.parametrize('initialize', [database_initialization, utils.database_initialization])
def test_invalid_download_directory_prevents_download(tmp_path, monkeypatch, initialize):
    download = Mock()
    monkeypatch.setattr(utils, 'download', download)
    with pytest.raises(ValueError, match='does not exist'):
        initialize(tmp_path / 'unused.ttl', tmp_path / 'missing')
    download.assert_not_called()
