"""Verify optional-feature failures are visible and CI reports prove execution."""

import builtins
import importlib.util
from pathlib import Path
import runpy

import pytest

from tests.check_test_report import require_passing_cases


@pytest.mark.parametrize('missing', ['fastapi', 'httpx'])
@pytest.mark.parametrize('required', [False, True])
def test_missing_server_dependency_skips_only_when_optional(monkeypatch, missing, required):
    original = importlib.util.find_spec

    def find_spec(name, *args, **kwargs):
        if name in ('fastapi', 'httpx'):
            return None if name == missing else object()
        return original(name, *args, **kwargs)

    monkeypatch.setattr(importlib.util, 'find_spec', find_spec)
    monkeypatch.setenv('H5RDMTOOLBOX_REQUIRE_SERVER_TESTS', '1' if required else '0')
    with pytest.raises(ImportError if required else pytest.skip.Exception, match=missing):
        runpy.run_path(str(Path(__file__).with_name('test_server.py')))


def test_broken_installed_server_dependency_is_not_skipped(monkeypatch):
    original = builtins.__import__
    original_find_spec = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, 'find_spec', lambda name, *args, **kwargs:
                        object() if name in ('fastapi', 'httpx') else original_find_spec(name, *args, **kwargs))

    def broken_import(name, *args, **kwargs):
        if name == 'fastapi.testclient':
            raise RuntimeError('broken installed dependency')
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', broken_import)
    with pytest.raises(RuntimeError, match='broken installed dependency'):
        runpy.run_path(str(Path(__file__).with_name('test_server.py')))


@pytest.mark.parametrize('xml', [
    '<testsuites/>',
    '<testsuite tests="0"/>',
    '<testsuite skipped="1"><testcase/></testsuite>',
    '<testsuite><testcase><skipped/></testcase></testsuite>',
    '<testsuite><testcase><failure/></testcase></testsuite>',
    '<testsuite><testcase><error/></testcase></testsuite>',
])
def test_report_rejects_missing_execution_or_nonpassing_cases(tmp_path, xml):
    report = tmp_path / 'report.xml'
    report.write_text(xml, encoding='utf-8')
    with pytest.raises(ValueError):
        require_passing_cases(report)


def test_report_counts_executed_cases(tmp_path):
    report = tmp_path / 'report.xml'
    report.write_text('<testsuites><testsuite tests="2" skipped="0" failures="0" errors="0">'
                      '<testcase name="first"/><testcase name="second"/></testsuite></testsuites>', encoding='utf-8')
    assert require_passing_cases(report) == 2
