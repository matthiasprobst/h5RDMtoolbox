# Architecture and quality review: synthesis

Date: 2026-10-31. Source baseline: `9aeefcbcd75bea8836bad197c2ef0ac1dcffc71c`
on `feature/modernize-repository`.

The user approved two investigating/discussing subagents. They edited only their
assigned reports, exchanged findings, and started no additional agents. The
parent reviewed their reports and added the runtime/artifact checks below.

- [Architecture report](architecture.md): convention restoration, shared state,
  activation failure handling, import relationships, and compatibility options.
- [Quality report](quality.md): CI side effects, packaging, coverage gaps,
  optional dependencies, and documentation environment requirements.

## Verified evidence

The source baseline has a passing Windows/CPython 3.12.4 coverage run:
444 passed, 27 skipped. Sphinx with `-W` and notebook execution disabled also
passes. These checks establish local behavior, not installed-wheel correctness
or hosted CI coverage.

The parent built a wheel with `python -m pip wheel . --no-deps
--no-build-isolation --wheel-dir .playground/wheel-audit`. Its retained `build/lib`
contents introduced an archived LLM package. The parent preserved the build
directory under `.playground/wheel-audit/preexisting-build` and rebuilt with a
fresh build directory. The clean wheel excludes LLM and contains server assets
and CSS, but still lacks `codemeta.json` and the declared convention template.

Clean wheel SHA-256:
`1b7b3ebb5c621ccbabb87ee70e4f6d2e88c369eb619349819b4ec5eea474ea04`.
The quality reviewer independently inspected this artifact. The parent extracted
it and ran isolated Python with that package first on `sys.path`; its `__file__`
confirmed the artifact path. `get_package_meta()` raised `FileNotFoundError`
because it opens a checkout-parent `codemeta.json`.

The parent also reproduced same-object Convention nesting in a fresh process
with isolated application directories. Starting at `h5py`, two nested `with cv`
blocks left `review-nesting` active after both exits. The expected restoration
was `h5py`. The architecture report explains the overwritten restoration slot.

Neither agent nor parent executed the account cleanup script, uploaded anything,
installed the wheel, or triggered hosted CI. Wheel builds/artifacts and probe
application data stayed local. The existing automatic cleanup risk is established
from workflow/script control flow, not by deleting remote records.

## Agreed priorities and boundaries

1. **Contain CI remote writes.** Remove automatic account-wide Sandbox cleanup
   from ordinary checks. Keep ordinary jobs free of write credentials; opted-in
   tests should clean only their own created IDs in `finally`. Add PR validation
   after its job boundaries are explicit. Acceptance: inspect workflow structure
   and use mocks to prove unrelated IDs cannot be deleted; do not test by running
   a real account purge.
2. **Repair installed artifacts.** Preserve `get_package_meta()` and its metadata
   contract, ship metadata as a package resource from one authoritative source,
   and resolve declared/actual asset mismatches. Test a clean wheel and an sdist
   outside the checkout. Verify resource contents, metadata/version consistency,
   and absence of experiments or build leftovers. The unused template's absence
   is verified; a runtime dependency on that template is not established.
3. **Fix sequential Convention restoration.** Add independent local regressions
   for two/three same-instance nestings, distinct instances, exceptions, re-entry,
   signatures, and decoding. A per-entry stack of existing `use` managers can
   reuse restoration behavior while preserving `with cv as value` identity and
   immediate `use(...)` activation. Do not claim this makes global state safe
   across concurrent tasks or threads.
4. **Make coverage explicit.** Classify the 19 tests gated to unsupported Python
   3.14 before enabling them; separate pure behavior from remote operations.
   Remove repeated network probes from local convention setup. Provision a
   deliberate server-test environment and fail on broken installed dependencies
   rather than skipping an entire feature. Preserve supported Python/OS coverage.
5. **Continue measured cleanup.** Address decoder metadata cleanup and measured
   import costs in separate commits. Keep public import paths, shared registry
   and logger identities, RDF behavior, and supported Python versions intact.

Both agents agree on these correctness tracks. Their different specialization
priorities are complementary: architecture prioritizes sequential restoration;
quality identifies default CI cleanup as the first operational concern. No
substantive unresolved disagreement was reported. The initial description of
convention test connectivity setup was corrected in both reports: it is a
per-test probe with conditional assertions, not a class-wide skip.

## Decisions kept separate

Full concurrency/per-file convention behavior needs an explicit contract: current
class signatures and decoder selection are process-global despite a context-local
pointer. A lock around activation alone does not isolate later file operations.
Do not silently switch existing files to file-local decoding or change public
introspection semantics in a small restoration fix.

Whether default tests should include remote reads, and whether unused historical
assets remain distribution contracts, also needs deliberate treatment. Immediate
cleanup containment and the demonstrated metadata failure can be fixed without
settling those larger policies. README and production developer/user docs must
reflect each implemented outcome; these reports preserve the baseline evidence.
