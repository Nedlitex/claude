---
name: edit-app-base
description: >-
  Use whenever you are about to change ANYTHING inside an `app_base` checkout —
  including as a git submodule at `vendor/app_base` in a consumer repo (stock,
  edu). Covers the branch/HEAD rule, the consumer-shaped-defect test that
  app_base's own ~150 arch gates structurally cannot replace, the full gate set,
  the mandatory committee iteration, and the release/tag ordering. Triggers on:
  "fix app_base", "add X to app_base", "upstream this", "bump the pin",
  "release app-base-vN", or any edit under `vendor/app_base/`.
---

# Editing app_base

app_base is a GENERIC library extracted from a domain monolith and consumed by
several apps as a git submodule. It has ~150 architecture tests and still
shipped, in one week: three releases at the wrong version number, six releases
with no changelog entry (one of them BREAKING), an entire family of consumer
errors silently becoming HTTP 500s, and a crawler that could neither return
binary bytes nor set a User-Agent.

Those are not carelessness. They are the predictable output of a specific
structure, and this skill exists to counter that structure.

---

## The one thing to understand first

**Almost every app_base defect is invisible from inside app_base.**

| Defect | Why the in-repo suite cannot see it |
|---|---|
| Logger prefixes hardcoded `"app."` | app_base's own tests ARE named `app` |
| Consumer typed exceptions → opaque 500s | app_base has no domain exceptions |
| Crawler cannot return bytes / set headers | its fixture server needs neither |
| `apply_vector_search` demanded `state_col` | app_base has no vector table |
| Dead constants naming the origin domain's tables | nothing in app_base references them |
| Vestigial enum members with no implementation | nothing registers them |

So the governing question for every change is not "do the tests pass?" It is:

> **Would this defect be visible from inside app_base? If no, the test must be
> consumer-shaped.**

A consumer-shaped test boots a SECOND app — named something other than `app`,
with its own Extension, its own exception types, its own tables — through the
real `create_app()`. If your change touches anything a consumer configures,
names, subclasses or injects, an in-repo unit test cannot cover it.

---

## Non-negotiables

### 1. NEVER work on a detached HEAD

A submodule checks out detached by default. Committing there produces work
reachable from nothing, and a `git submodule update` silently discards it.

```bash
cd vendor/app_base
git status -sb | head -1          # "HEAD (no branch)" => STOP
git fetch --tags --prune origin
git checkout -b <type>/<slug> origin/main
```

Branch from `origin/main`, not from whatever the consumer's pin happens to be —
**main moves while you work.** Verified this session: a branch cut from the
consumer's pin found `origin/main` four commits and three tags ahead by the time
it was ready, with its intended version number already taken upstream.

### 2. Re-fetch before you push, and rebase — do not merge

```bash
git fetch --tags --prune origin
git log --oneline origin/main..HEAD          # your work
git log --oneline HEAD..origin/main          # what moved under you
comm -12 <(git diff --name-only $(git merge-base origin/main HEAD)..origin/main | sort) \
         <(git diff --name-only $(git merge-base origin/main HEAD)..HEAD | sort)
```

An empty overlap means a clean rebase. Rebase; keep history linear.
**Re-check the version number after rebasing** — someone else may have claimed it.

### 3. Establish the pre-existing failure baseline BEFORE you claim zero regressions

app_base's suite has environment-dependent failures (missing optional extras,
absent services). Without a baseline you will either chase phantom regressions
or hide real ones.

```bash
git stash && python -m pytest <the failing subset> -q  # baseline at base
git stash pop && python -m pytest <the same subset> -q # after
```

Report both. "Zero regressions" is only meaningful as a diff against a measured
baseline.

### 4. Never fork generic code into the consumer

If app_base is wrong, the fix is an app_base commit. A local copy in the
consumer is forbidden, always. If you cannot fix it now, register it as an
upstream item with `file:line` evidence and take a NARROW, single-file,
documented exception with its own arch test and a stated deletion condition.

---

## Gates — all of them, in this order

Find the real commands in app_base's own `CLAUDE.md`. Do **not** substitute the
consumer's test runner (the consumer's selector aims at the consumer's suite and
will report green for the wrong tests).

1. **The consumer-shaped test for your change** (see above). Write it first.
2. **Prove every new test RED.** Revert only the IMPLEMENTATION file, keep the
   contracts, and watch the test fail behaviourally — not with an `ImportError`,
   which proves nothing. Commit the pair RED-then-GREEN so the proof is in
   history.
3. **The full architecture suite** — `tests/architecture/`. ~150 gates; they are
   the repo's accumulated scar tissue and they are fast.
4. **The affected module suites**, plus anything importing what you changed.
5. **Type check and lint** exactly as pre-commit runs them. Check the ANALYZED
   FILE COUNT, never the zero — a type checker that resolved the wrong
   environment reports clean for an empty set.
6. **Committee review — mandatory, and iterate until it clears.** Run
   `/team-review` against the diff. app_base is consumed by multiple apps; a
   defect here multiplies across every one of them, and the cost of a bad
   release is paid by people who did not make the change. **One pass is not
   enough**: fix what it finds, re-run, and repeat until the findings are
   accepted or explicitly deferred with a reason. Do not push on the first pass.

---

## Release discipline

The tag/version defects all come from one ordering mistake: **tagging after the
suite ran.** The version-consistency gate is a no-op on an untagged HEAD — its
own docstring says so — so tagging afterwards means it never fires.

Release, in order:

1. Bump **both** version literals (`pyproject.toml`, `src/app_base/__init__.py`).
   **Re-check the number is still free** — `git tag --sort=-v:refname | head`.
2. Write the `## [X.Y.Z]` CHANGELOG entry. The file's own header promises
   **"every entry states what a consumer must do"** — honour it. An SPI bump
   without a changelog entry is how a consumer misses a required pin widen.
3. Commit both together.
4. **Run the whole suite with the version commit as HEAD.**
5. Tag only then, and push the tag.

**SPI bumps.** Bump `EXTENSION_SPI_VERSION` only when an `Extension` member
changes. Adding a capability to a module a consumer uses directly (crawler, DAL
helpers) is NOT an SPI change — forcing every consumer to re-vet every seam for
a change that cannot reach them is noise. State the reasoning in the changelog.

---

## Arch gates worth adding when you touch these areas

If your change is in a category below and the corresponding gate does not exist,
add it. These are the categories that produced real, shipped defects.

- **Anything naming the app** — assert the property (it tracks
  `app_name()`), never the string.
- **Anything a consumer subclasses, injects or registers** — assert a second,
  differently-named consumer works.
- **Any enum member / registry key** — assert every member has a producer, or is
  explicitly listed as reserved. A member nothing can produce is a lie in the
  schema.
- **Any identifier naming the origin domain** — a denylist test. Extraction
  leaves residue that nothing references and therefore nothing fails on.
- **Any request/policy/config field** — assert something READS it. An unread
  field is decoration that type-checks.
- **Any module a consumer imports** — it must not be underscore-private, or it
  must be re-exported publicly.

---

## The failure mode this skill exists to prevent

> A gate that is correct, well documented, and structurally unable to fire at
> the moment it matters.

The version gate no-ops on untagged HEADs. The impact map ships empty, so the
test selector silently falls back to a full-suite run and reports success. Both
are *correct code*. Both let the defect through.

When you add a gate, ask what would have to be true for it to fail — and then
check that condition can actually occur in the workflow that produced the bug.
