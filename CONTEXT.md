# IADC-Tester — Plugin Design

The working vocabulary for building and maintaining the `iadc-tester` plugin *itself*. This is
maintainer vocabulary; it is **not** the domain language of any client's Appian application, and it
is not a glossary of Appian or Selenium terms.

`CONTEXT-MAP.md` in the family umbrella has listed this context since the family was formed. This
file is the glossary it points at.

## Language

### Product and runtimes

**Plugin**:
The shippable artifact — the Claude Code plugin named `iadc-tester`: the `.claude-plugin/plugin.json`
manifest and everything under `skills/`. Installed by clients at project scope from the **Catalog**
in `IADC-Marketplace`, either alone or through the `iadc` bundle.

**Developer session**:
The plugin running in a person's Claude Code session, in an Appian app repo. Config is read from
files in that repo, and a missing value can be asked for.

**Pipeline run**:
The plugin running server-side in the Appian-initiated pipeline, seeded into a container image at
build time. There is **no user to ask** and possibly no repo to read, so every value must be
resolvable from the environment. The two runtimes are why this plugin ships no session hook and
carries no advisory posture — see the family's `ADR 0008` and `ADR 0009`.

### The Selenium harness

**Test harness**:
The extracted Appian Selenium API distribution. It is not documentation — it is the thing the tests
compile and run *inside*. A generated test file only works when it sits at the expected location
within this tree, which is why the harness is a configured value and not an incidental detail.
_Avoid_: "the Selenium files" (ambiguous — the harness, the Javadoc inside it, and the generated
tests are three different things)

**Harness path**:
The absolute filesystem path to the **Test harness** root. **Per-machine** — two developers on one
project have different answers, and in a **Pipeline run** it is a property of the image rather than
of any person. The standing example of a `.local`-tier value under the family's per-project-state
convention.

**Javadoc**:
The API reference carried inside the **Test harness**. It is the *authority* on whether a fixture
method exists: a method is confirmed against the Javadoc, never assumed from a plausible name. This
is the reason the harness must be present to generate tests, not only to run them.

**Test project folder**:
The folder within the **Test harness** where this application's generated tests live. Committed-tier:
the team agrees on one, even though the harness containing it is per-machine.

**Test repo**:
The git repository holding the generated test files — the durable home for them, separate from the
**Test harness** they execute inside. Committed-tier.

### Reconciliation

**Feature**:
A single application + workflow/action combination — "Add Rule in the Isaac Sandbox application".
The **unit of matching** between a ticket's acceptance criteria and the test suite: all criteria for
one workflow on one application stay together, and a feature resolves to exactly one test file.
Most tickets describe one feature. This is the term the whole reconciliation process is defined in.
_Avoid_: "test case", "scenario" (both suggest a single `@Test` method; a feature usually spans
several)

**Reconciliation**:
Matching a ticket's requirements against the existing suite and producing the minimal change:
already-covered requirements are left alone, genuinely new ones are added, and contradicting ones
get the smallest replacement that resolves the contradiction. Distinct from generating a suite from
scratch, which is the case where a **Feature** has no existing file.

## Conformance

This context defines only the terms above. Two bodies of vocabulary are used here and owned
elsewhere; neither is restated locally, and a duplicate definition is a defect rather than a nuance.

- **App Graph**, **Graph Snapshot**, **Graph Query MCP**, **Graph service**, **Object Test**,
  **Artifact** — owned by **Core**, used exactly as `IADC-Core/CONTEXT.md` defines them.
- **Per-project state** and its two tiers — a family **convention**, not a term of either product,
  owned by the umbrella at `docs/agents/per-project-state.md`.
