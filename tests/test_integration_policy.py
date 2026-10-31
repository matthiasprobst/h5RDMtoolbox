"""Exercise collection policy without contacting external services."""

import pathlib

import pytest

pytest_plugins = ["pytester"]


@pytest.mark.parametrize("opt_in,token,expected", [
    (None, "test-token", "skipped"),
    ("0", "test-token", "skipped"),
    ("1", None, "skipped"),
    ("1", "test-token", "passed"),
])
def test_live_upload_requires_opt_in_and_token(pytester, monkeypatch, opt_in, token, expected):
    for name, value in (
        ("H5RDMTOOLBOX_RUN_ZENODO_UPLOAD_TESTS", opt_in),
        ("ZENODO_SANDBOX_API_TOKEN", token),
    ):
        monkeypatch.delenv(name, raising=False)
        if value is not None:
            monkeypatch.setenv(name, value)
    monkeypatch.setenv("H5RDMTOOLBOX_RUN_WIKIDATA_TESTS", "1")
    pytester.makeconftest(pathlib.Path(__file__).with_name("_integration.py").read_text(encoding="utf-8"))
    pytester.makeini("[pytest]\nmarkers =\n    zenodo_upload: live uploads\n    wikidata: remote queries\n")
    pytester.makepyfile('''
        import pathlib
        import pytest

        @pytest.mark.zenodo_upload
        @pytest.mark.wikidata
        def test_upload():
            pathlib.Path("upload-executed").touch()
    ''')
    result = pytester.runpytest_subprocess("-q", "-rs")
    result.assert_outcomes(**{expected: 1})
    assert (pytester.path / "upload-executed").exists() == (expected == "passed")
