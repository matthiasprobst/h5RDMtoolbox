# Convention state and module architecture review

Reviewed 2026-10-31 on `feature/modernize-repository`, source baseline
`9aeefcbcd75bea8836bad197c2ef0ac1dcffc71c`.

This is an independent source review and a discussion with the quality reviewer.
Only this report was edited. No product code, tests, configuration, or Git
references were changed. No service calls or runtime probes were executed by
this reviewer. Findings below distinguish facts established by control flow
from behavior that still needs a regression test.

## Findings and evidence

### 1. Sequential nesting of the same Convention object loses restoration state

**Source-proven and independently runtime-reproduced by the parent; highest-priority convention follow-up.**
[Convention.__enter__/__exit__](../../h5rdmtoolbox/convention/core.py#L259)
store one previous convention in `self._curr_cv`. With the same instance nested
twice, the inner entry overwrites the outer entry's previous convention:

```python
previous = h5tbx.convention.get_current_convention()
cv = h5tbx.convention.Convention(name="review-nesting", contact=h5tbx.__author_orcid__)
cv.register()
with cv as outer:
    assert outer is cv
    with cv as inner:
        assert inner is cv
    assert h5tbx.convention.get_current_convention() is cv
assert h5tbx.convention.get_current_convention() is previous
```

The last assertion is the proposed regression: from the inspected control flow,
the inner entry replaces `self._curr_cv` with `cv`, so both exits reactivate
`cv`. The parent reproduced the equivalent scenario in a fresh Python process
with isolated application directories: the initial convention was `h5py`, and
after two nested entries of `review-nesting` the actual convention was still
`review-nesting`, rather than the expected `h5py`. The example above was not run
by this reviewer. Ordinary nesting of distinct
Convention instances does not share that single restoration slot.

**Recommended compatible fix:** keep a per-entry restoration stack on each
Convention, or a stack of separate `use(...)` managers. Push only after
activation succeeds; pop once on exit, including exceptional exits. Preserve
`with cv as value` returning the Convention itself, and preserve the immediate
activation performed by constructing `h5tbx.use(...)`.

Both approaches solve sequential nesting with small changes. A previous-value
stack is the smaller implementation; a manager stack reuses existing activation
and restoration behavior. Neither is evidence of thread/task isolation. Do not
replace the context protocol with a method returning another object, or change
`use(...)` activation from construction time to entry time as part of this fix.

### 2. Context-local pointer and global operational state have different owners

**Verified architecture; consequences need explicit behavioral contracts.**

- [convention/cfg.py](../../h5rdmtoolbox/convention/cfg.py#L4) stores the active
  pointer in a ContextVar, but the registry is a normal shared dictionary.
- [_use](../../h5rdmtoolbox/convention/core.py#L739) deletes and inserts methods
  on shared wrapper classes and overwrites `ds_decoder.decoder_names`.
- [_add_signature](../../h5rdmtoolbox/convention/core.py#L463) replaces class
  methods through `setattr`; it also mutates shared docstring parsers.
- [decoder dispatch](../../h5rdmtoolbox/wrapper/ds_decoder.py#L106) reads the
  module-global decoder list, not the dataset's cached Convention.
- [File initialization](../../h5rdmtoolbox/wrapper/core.py#L2571) caches a
  Convention on the object, and [Group.standard_attributes](../../h5rdmtoolbox/wrapper/core.py#L526)
  uses the cached object's properties. By contrast,
  [process_standard_attributes](../../h5rdmtoolbox/wrapper/core.py#L158) consults
  the currently active pointer.

Thus the context-local name is not an isolated convention execution environment.
An interleaving of context A and context B can leave A's pointer intact while B
last changed global decoding or method signatures. `_use`'s early return when
the requested name already matches the context pointer can also leave those
global effects unreconciled. This mechanism follows from the source; a
deterministic interleaving regression should establish actual dataset/signature
effects before changing behavior.

The [getter docstring](../../h5rdmtoolbox/convention/core.py#L774) currently says
"thread-safe". The existing
[thread test](../../tests/conventions/test_conventions.py#L102) checks names in
two threads, not signatures, decoder outputs, or object metadata behavior.
Documentation should state the narrower context-local lookup guarantee and
the process-global activation effects.

**Open compatibility decision:** when a file opened under convention A is used
after B is activated, should its decoding and creation behavior follow A or B?
The code currently mixes ownership. A file-local design is attractive for
predictability, but silently changing decoder selection to `ds.convention`
could change existing applications. Characterize and specify this separately.

### 3. Failed activation can leave operational state partly changed

**Verified ordering; failure scenario not runtime-reproduced here.**
[_use](../../h5rdmtoolbox/convention/core.py#L743) removes current signatures,
clears decoder names, clears signatures across all registered conventions, and
calls the next Convention's `_add_signature` before publishing the new pointer.
There is no rollback if signature insertion fails midway. This can leave the
old context pointer alongside cleared or partial class signatures and empty
decoder selection.

Add a fault-injection regression and decide on transactional activation in its
own change. It should preserve the previous pointer, decoder behavior, relevant
method signatures/docstrings, and the original activation exception. Do not
combine rollback design with the small nesting correction.

### 4. Import boundaries are improved but still structurally cyclic

**Verified source relationships; cost ranking requires profiling.**

The direct `_cfg` and named-logger imports already added are useful and should
remain. The larger convention/wrapper cycle is still present:

```text
package facade -> convention -> convention.core -> wrapper.ds_decoder
                                   |
                                   -> standard_attributes -> wrapper.core
                                                            -> convention
```

[standard_attributes.py](../../h5rdmtoolbox/convention/standard_attributes.py#L15)
still imports configuration from the facade, imports concrete wrapper classes,
and creates shared signature/docstring mappings during import.
[convention.core](../../h5rdmtoolbox/convention/core.py#L19) also imports repository
and Zenodo integration code eagerly; its `from_zenodo` path is a candidate for
point-of-use imports. Importing
[database.lazy through the facade](../../h5rdmtoolbox/__init__.py#L51) executes
[database package initialization](../../h5rdmtoolbox/database/__init__.py#L5),
which imports the HDF database implementations.

Recommended sequence: profile the current package again, make only measured
point-of-use changes, then consider separating immutable convention definitions
from wrapper activation/signature composition. A generic import-rewriting pass
cannot remove the concrete class-registration cycle safely. Preserve concrete
class identity, public exports, introspection signatures, and first-use behavior.
No additional performance improvement is claimed from these candidates.

### 5. Startup has deliberate shared-state and filesystem effects

**Verified initialization behavior; not a proposal to remove all effects.**
[Facade initialization](../../h5rdmtoolbox/__init__.py#L11) loads user directories,
adds logger handlers, binds pint_xarray to the shared registry, registers and
selects `h5py`, installs exit cleanup, and sets an xarray display option.
[user.py](../../h5rdmtoolbox/user.py#L28) creates directories; constructing UserDir
also prunes old cache files. These are meaningful compatibility contracts for
startup work, not just import overhead.

The existing [startup test](../../tests/test_startup.py) verifies deferred engines,
first use, registry identity and default selection in a fresh process. Keep it
as a core acceptance check. Wheel checks should also exercise resources and
`get_package_meta`, whose [implementation](../../h5rdmtoolbox/__init__.py#L67)
looks for `../codemeta.json` relative to the installed package. The quality track
and parent are independently investigating distribution contents; this reviewer
did not build or install a wheel.

## Recommended order and acceptance criteria

1. **Correct sequential same-instance nesting.** Add a new network-independent
   test module. Cover two and three nested entries, distinct objects, body
   exceptions, subsequent re-entry, and the return identity of `with cv as value`.
   Assert restoration of active pointer, dataset decoding, and dynamic
   signatures where the conventions differ. Register conventions and decoders
   in memory, restore registries in fixtures, and use temporary HDF5 files.
2. **Narrow concurrency claims to current guarantees.** Update public docstrings,
   developer overview, README and agent instructions. Keep a distinction between
   name lookup and process-global activation. Add deterministic context
   interleaving tests; do not promote the existing name-only thread test into
   evidence of operational isolation.
3. **Improve activation failure safety separately.** Establish a rollback
   contract using a failing signature-activation test before implementing it.
4. **Profile and decouple measured import costs.** Measure fresh import and first
   use under the same environment; preserve shared registry and public APIs.
   Define immutable-convention/activation boundaries before a larger split.
5. **Treat full concurrency/file-local decoding as a separate design.** A lock
   around `_use` alone does not protect later HDF5 operations. A lock around an
   entire context can serialize threads, but is problematic across async awaits
   and still needs a declared contract. Context-local decoders alone do not
   make shared class signatures context-local. Explicit per-file behavior plus
   stable signatures or proxy/factory objects is a larger API/introspection
   decision, not a small ContextVar conversion.

## Discussion with the quality reviewer

Both reviewers agree on fixing sequential nesting before attempting full
context-local convention isolation. We agree acceptance tests must inspect
observable decoding and signatures, not only stored names. We did not identify
a substantive disagreement about that sequence.

The quality reviewer initially described the existing TestConventions class as
network-gated, then corrected that reading: its per-test `setUp` probes Zenodo
and sets `self.connected`; it does not skip the whole class. Several methods
also have Python-minor gates, and some remote assertions are conditional. The
correct recommendation remains a new independent module for local state tests,
avoiding repeated connectivity probes. See the quality report for exact gate
counts and evidence.

The quality reviewer independently prioritizes removing automatic account-wide
Sandbox cleanup from normal CI and testing installed wheel resources. These are
independent correctness tracks and can precede a larger convention redesign.
The parent reported reproducing an installed-wheel `get_package_meta()` failure;
that reproduction was not performed by this reviewer.

## Limits and remaining decisions

This reviewer did not execute runtime probes; the same-instance nesting
reproduction above was supplied by the parent. The review does not claim
full-suite verification, performance measurements, thread/task safety, or
installed-wheel correctness.
It did not inspect archived ideas or start further subagents. Source line
references describe the baseline commit and can move during implementation.
Before full isolation work, settle per-file versus active-context ownership and
whether dynamic global signatures remain a supported introspection contract.
