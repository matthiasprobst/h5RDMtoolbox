"""Check CI boundaries and scoped cleanup using mocks only."""

import json
from pathlib import Path
from unittest.mock import Mock, call

import pytest
import requests
import toml
import yaml
from packaging.specifiers import SpecifierSet

from tests.clean_zenodo_sandbox import delete_sandbox_deposits


@pytest.fixture
def sandbox_api(monkeypatch):
    delete = Mock()
    monkeypatch.setattr(requests, 'delete', delete)
    monkeypatch.setattr(requests, 'get', Mock(side_effect=AssertionError('No account listing allowed')))
    token = Mock(return_value='test-token')
    monkeypatch.setattr('h5rdmtoolbox.repository.zenodo.tokens.get_api_token', token)
    return delete, token


def test_cleanup_deletes_only_explicit_ids(sandbox_api):
    delete, token = sandbox_api
    delete_sandbox_deposits([42, 123, 42])
    assert delete.call_args_list == [
        call(f'https://sandbox.zenodo.org/api/deposit/depositions/{value}',
             headers={'Authorization': 'Bearer test-token'}, timeout=30)
        for value in (42, 123)
    ]
    token.assert_called_once_with(sandbox=True)
    assert delete.return_value.raise_for_status.call_count == 2


@pytest.mark.parametrize('ids', [[], ['42'], [42, -1], [0], [True], [1.5], ['../../other'], '42'])
def test_cleanup_validates_all_ids_before_requests(sandbox_api, ids):
    delete, token = sandbox_api
    with pytest.raises((ValueError, TypeError)):
        delete_sandbox_deposits(ids)
    delete.assert_not_called()
    token.assert_not_called()


def test_cleanup_stops_on_http_error(sandbox_api):
    delete, _ = sandbox_api
    delete.return_value.raise_for_status.side_effect = requests.HTTPError('forbidden')
    with pytest.raises(requests.HTTPError):
        delete_sandbox_deposits([42, 123])
    assert delete.call_count == 1


def test_cleanup_requires_credentials(sandbox_api):
    delete, token = sandbox_api
    token.return_value = None
    with pytest.raises(ValueError, match='token'):
        delete_sandbox_deposits([42])
    delete.assert_not_called()


def test_default_ci_has_pr_checks_and_no_zenodo_writes():
    path = Path(__file__).parents[1] / '.github/workflows/tests.yml'
    text = path.read_text(encoding='utf-8')
    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    assert {'push', 'pull_request', 'workflow_dispatch'} <= set(workflow['on'])
    assert workflow['permissions'] == {'contents': 'read'}
    assert workflow['env']['H5RDMTOOLBOX_RUN_ZENODO_UPLOAD_TESTS'] == '0'
    assert 'zenodo_cleanup' not in workflow['jobs']
    assert 'clean_zenodo_sandbox.py' not in text
    assert 'secrets.ZENODO' not in text
    assert workflow['jobs']['test']['strategy']['fail-fast'] == 'false'
    assert workflow['jobs']['test']['strategy']['matrix']['python-version'] == [
        '3.10', '3.11', '3.12', '3.13',
    ]
    steps = workflow['jobs']['server']['steps']
    assert any('.[test-server]' in step.get('run', '') for step in steps)
    required_step = next(step for step in steps if 'tests/test_server.py' in step.get('run', ''))
    assert required_step['env']['H5RDMTOOLBOX_REQUIRE_SERVER_TESTS'] == '1'
    report_step = next(step for step in steps if 'tests.check_test_report' in step.get('run', ''))
    assert steps.index(report_step) > steps.index(required_step)
    assert 'if' not in report_step and 'continue-on-error' not in report_step


def test_ci_python_matrix_matches_package_support():
    repository = Path(__file__).parents[1]
    project = toml.load(repository / 'pyproject.toml')['project']
    supported = SpecifierSet(project['requires-python'])
    workflow = yaml.load((repository / '.github/workflows/tests.yml').read_text(encoding='utf-8'),
                         Loader=yaml.BaseLoader)
    matrix = workflow['jobs']['test']['strategy']['matrix']
    assert matrix['os'] == ['ubuntu-latest', 'macos-latest', 'windows-latest']
    assert matrix['python-version'] == ['3.10', '3.11', '3.12', '3.13']
    assert workflow['jobs']['test']['runs-on'] == '${{ matrix.os }}'
    assert '3.9' not in supported
    assert '3.14' not in supported
    assert all(version in supported for version in matrix['python-version'])
    classifiers = {value.removeprefix('Programming Language :: Python :: ')
                   for value in project['classifiers']
                   if value.startswith('Programming Language :: Python :: ')}
    assert classifiers == set(matrix['python-version'])
    codemeta = json.loads((repository / 'codemeta.json').read_text(encoding='utf-8'))
    assert set(codemeta['programmingLanguage']) == {'Python 3'} | {
        f'Python {version}' for version in matrix['python-version']
    }
