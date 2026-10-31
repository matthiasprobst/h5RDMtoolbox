# Quality, CI, and packaging review

Reviewed on 2026-10-31 against `feature/modernize-repository`, commit
`9aeefcbcd75bea8836bad197c2ef0ac1dcffc71c`.

## Scope and evidence

This is an investigation report only. No production code, tests, configuration,
or Git history was changed by this reviewer. The parent supplied the verified
local result of 444 passed / 27 skipped on Windows CPython 3.12.4 and a successful
Sphinx `-W` build with notebook execution disabled. Those results are valuable,
but do not prove fresh-install, all-platform, or optional-feature coverage.

I independently inspected source, workflow definitions, installed dependency
metadata, AST counts of test gates, and the clean wheel built by the parent.
No external requests, uploads, cleanup scripts, dependency installation, or
publishing were executed by this reviewer.

## Findings

### Q1 - Automatic CI cleanup deletes unrelated Sandbox drafts (highest priority)

**Verified from source.** `.github/workflows/tests.yml:94-119` runs
`zenodo_cleanup` after the test job succeeds. There is no explicit integration
opt-in on this job, even though upload tests now require one. Its command runs
`tests/clean_zenodo_sandbox.py:6-19`, which lists the account's deposits and deletes
every unsubmitted draft. There is no per-run ownership filter, ID allowlist,
request timeout, or upper retry bound. The workflow provides Sandbox credentials.

This is an independent remote side effect of a successful push build. A green
test job does not establish ownership of all drafts in that account. I did not
execute this cleanup and did not inspect remote account contents.

**Recommendation:** remove automatic account-wide cleanup from ordinary CI.
Explicitly enabled integration tests should retain the IDs they create and clean
up those IDs in `finally` blocks. If an account-maintenance tool is retained,
give it a separate explicit workflow/command with documented ownership scope;
it must not be a normal test dependency.

**Acceptance:** ordinary push/PR workflows contain no cleanup command or Zenodo
write credentials; mocked cleanup tests prove unrelated IDs are untouched;
an opted-in test cleans its own ID even when assertions fail. No real deletion
is needed to test the ownership policy.

### Q2 - Installed-wheel metadata API is broken

**Verified from source and artifact; runtime reproduced by parent.**
`h5rdmtoolbox/__init__.py:67-71` opens `../codemeta.json` relative to the package
directory. That file lives at the checkout root, outside package data.
`tests/test_version.py:7,32` exercises this API from the checkout, where the file
exists, so it cannot expose the wheel failure.

The parent's clean artifact is
`.playground/wheel-audit/clean/h5rdmtoolbox-2.8.2-py3-none-any.whl`, SHA-256
`1b7b3ebb5c621ccbabb87ee70e4f6d2e88c369eb619349819b4ec5eea474ea04`.
My independent ZIP inspection confirms that it contains no `codemeta.json`.
The parent extracted this wheel, used isolated Python (`-I`) with the extracted
package first on `sys.path`, confirmed its `__file__`, and reproduced
`FileNotFoundError` from `get_package_meta()`.

**Recommendation:** retain the public function and ship/read metadata as a
package resource. Define one authoritative metadata source or a build-time copy
with a consistency check; avoid two manually maintained JSON copies. Do not
depend on the caller's working directory or a checkout parent directory.

**Acceptance:** build sdist and wheel from a clean source tree, exercise
`get_package_meta()` outside the checkout using the artifact, and assert version
consistency with package/distribution metadata. Check both wheel contents and
runtime behavior; an editable install is insufficient.

### Q3 - Resource declarations and local build state need artifact checks

**Verified archive/source mismatch.** `pyproject.toml:135` names
`conventions/html/template.html`, but the tracked file is
`h5rdmtoolbox/convention/html/template.html` (singular). The clean wheel omits it.
The current source search found no runtime consumer of this template, so a
runtime failure is **not** established merely from its omission. Correct the
declaration if the template is intended to be distributed, or explicitly remove
obsolete declarations/assets after checking their contract. Similar declared
`data/TbxLayout.hdf` and `data/EmptyLayout.hdf` files are absent from tracked data.
The clean wheel does contain `data/style.css` and server templates/static assets.

**Parent-observed build contamination:** its first working-tree wheel included
the archived experimental LLM package through retained `build/lib` contents.
After preserving the old build directory and rebuilding cleanly, the LLM entries
were absent; my independent clean-wheel inspection confirms this. This is evidence
of stale build-state contamination, not evidence that package discovery includes
`.playground/` directly.

**Recommendation:** perform release builds from clean, isolated source snapshots
and inspect the produced archive. Preserve local experiments/build artifacts
rather than recursively deleting unreviewed user directories. Add explicit
resource/forbidden-content assertions to artifact verification.

**Acceptance:** both a fresh checkout and a source distribution produce a wheel
with required assets, no `.playground/`, `.work/`, cached experimental packages,
test-generated files, or unrelated build leftovers. Keep evidence for both clean
and intentionally contaminated-working-tree scenarios.

### Q4 - Test version gates hide coverage throughout the supported matrix

**Verified by source and AST inspection.**
`tests/repository/test_zenodo.py:34` defines `TESTING_VERSIONS = (14,)`; all 18 test
methods carry that gate. `tests/conventions/test_references.py:9,29` similarly
gates its single test to 3.14. The project supports `>=3.9,<3.14` and CI tests
3.9-3.13, so these 19 tests cannot execute in the declared supported matrix.
The convention module additionally gates 13 of 35 methods to minor version 12.

Do not simply change 14 to 12: the Zenodo methods mix local behavior, remote
reads, and remote mutations. Enabling them indiscriminately could bypass the
intent of the new upload opt-in policy.

**Recommendation:** split deterministic local contracts from service integration
tests. Replace Python-minor scheduling of remote operations with explicit markers
and genuine compatibility skips only where necessary. Classify all remote write
tests before removing their existing gates.

**Acceptance:** local URL parsing, metadata, token handling, and other pure
behavior run on every supported interpreter without credentials. All real writes
require their explicit gate. A marker/skip audit reports coverage actually run;
there are no tests gated exclusively to unsupported versions.

### Q5 - Convention test setup performs unnecessary repeated network probes

**Verified from source, corrected after full-body review.**
`tests/conventions/test_conventions.py:41-47` performs a five-second-timeout
`requests.get("https://zenodo.org")` in per-test `setUp`. It does **not** skip the
whole class: failures set `self.connected=False` and emit a warning. Methods at
`:346-347` and `:696-697` condition their behavior/assertions on that flag, so they
can finish successfully without exercising their intended remote path. Pure
local convention tests also pay for the probe. Availability checks do not verify
the later resource-specific requests.

**Recommendation:** remove the general probe from local setup. Mark the actual
remote tests and handle connection outcomes at the request boundary with an
explicit skip/failure policy. Keep new state-contract tests network-independent.

**Acceptance:** deterministic convention tests pass when all network access is
denied; remote tests either run meaningful assertions or report a visible skip.
No integration path silently passes through an empty conditional branch.

### Q6 - PR, server-feature, and artifact coverage are not guaranteed by CI

**Verified workflow/configuration facts:**

- `.github/workflows/tests.yml:8-18` declares push triggers only. No workflow file
  in the checkout adds a pull-request test trigger. External branch-protection
  settings were not inspected.
- The matrix has all supported Python versions and three OSes (`:24-25`), which
  should be preserved where dependency support permits it.
- CI installs editable `.[test]` (`:54`), not the built wheel. It performs no
  package-archive/resource smoke check.
- `.[test]` and `.[complete]` omit the `server` extra (`pyproject.toml:82-107`).
  All 82 test functions in `tests/test_server.py` are gated by
  `FASTAPI_AVAILABLE`; lines 10-15 catch **any** exception while importing
  `TestClient`. Thus missing dependencies or a broken import can hide the entire
  area behind the misleading reason "FastAPI not installed". The local green
  run had these optional dependencies; a fresh CI environment is a different
  claim. Exact fresh-run skip counts were not reproduced here.
- The server extra declares FastAPI/Uvicorn/Jinja2, but not HTTPX, which the
  TestClient path requires. An explicit server-test environment must supply its
  test dependency rather than relying on the reviewer's installed environment.

**Recommendation:** add PR validation with a deterministic core job, a deliberate
server-test environment, and an artifact smoke job. Move live integrations to
separate opt-in execution with scoped credentials. Narrow availability skips to
expected missing-optional-dependency cases; installed-but-broken imports should
fail visibly. Update README/testing/developer instructions with the final matrix.

**Acceptance:** CI configuration contains the PR event, the core job does not
receive write tokens, a server job asserts its tests executed, and artifact tests
import outside the checkout. Validate the workflow structure locally and report
that hosted CI execution remains unverified until it actually runs.

### Q7 - Documentation environment has a different Python floor

**Verified installed metadata and declarations.** The pinned Sphinx 8.0.0 requires
Python `>=3.10`; the base package permits Python 3.9. Read the Docs currently uses
3.10, so this does not show a broken hosted docs build. However, the generic docs
extra/setup commands do not explain their different interpreter requirement.

**Recommendation:** document Python 3.10+ for the current docs environment while
preserving the base Python range. Only change docs pins or the package support
range if that is an intentional compatibility decision.

## Discussion and prioritization

The architecture reviewer and I agree that default account-wide cleanup should
be removed/scoped immediately, independently of larger architecture work. We
also agree on a small sequential convention-nesting fix followed by an explicit
process-global state contract, rather than claiming that a `ContextVar` alone
provides thread safety. Acceptance should inspect decoding and method signatures
as well as the convention name. I recommended putting those regressions outside
the network-probing convention class. See `architecture.md` for the independently
investigated state findings; this report does not claim their runtime probe as
its own.

There was no substantive disagreement on this ordering. Full context-local or
per-file decoder semantics remain a separate compatibility/design decision.

Recommended independent implementation units:

1. Remove automatic broad cleanup; add safe PR job boundaries.
2. Repair packaged metadata/resource declarations and add a clean wheel smoke
   check. This is a demonstrated distribution bug, not a cosmetic refactor.
3. Restore deterministic tests now excluded by unsupported-version gates; isolate
   real service interactions and explicit optional server coverage.
4. Fix characterized sequential convention restoration and document shared state;
   defer concurrent-isolation redesign until its contract is decided.

## Limitations and open choices

This investigation did not change implementation, rerun the full suite, install
new dependencies, execute hosted CI, contact services, or verify all supported
Python/OS combinations. Artifact evidence is the local clean wheel specified
above; production dependency resolution in a fresh environment still needs its
own test. No assertion is made about live account contents or current GitHub
branch protection.

Open decisions: whether remote reads belong in the default test command or only
in a separate integration selection; how to express the optional server test
dependencies; whether the unused convention HTML template/layout declarations
are retained distribution assets; and whether future concurrency guarantees are
process-global, serialized, per-file, or fully context-local. None requires
silently changing public runtime APIs in the immediate correctness fixes.
