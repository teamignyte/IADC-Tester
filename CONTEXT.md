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
resolvable from the environment. This plugin ships no session hook and carries no
**Advisory posture** — neither is a consequence of running here specifically. The family's one
config-injecting session hook is Advisor's (`ADR 0009`); separately, writing code is this plugin's
whole purpose, the opposite of what that posture means (`ADR 0008`).

### The Selenium harness

**Test harness**:
The extracted Appian Selenium API distribution — it supplies the **Javadoc** that confirms which
fixture methods exist, and the `ExampleProjects` folder `generate-selenium-tests` reads for usage
patterns. Since IV-368 it no longer supplies what a generated test compiles against: that is
`appian-selenium-api.jar`, downloaded once by `/iadc-tester:setup` and committed into the **Test
repo** at a fixed path — see **Test project folder**.
_Avoid_: "the Selenium files" (ambiguous — the harness, the Javadoc inside it, and the generated
tests are three different things)

**Harness path**:
The absolute filesystem path to the **Test harness** root. Read only to reach the Javadoc and
`ExampleProjects` reference material during generation (`generate-selenium-tests` step 6) — since
IV-368, no longer to compile: that moved to the jar committed in the **Test repo**. **Per-machine**
— two developers on one project have different answers, and in a **Pipeline run** it is a property
of the image rather than of any person. The standing example of a `.local`-tier value under the
family's per-project-state convention.

**Javadoc**:
The API reference carried inside the **Test harness**. It is the *authority* on whether a fixture
method exists: a method is confirmed against the Javadoc, never assumed from a plausible name. This
is the reason the harness must be present to *generate* tests — since IV-368, no longer to compile
or run them.

**Test project folder**:
The fixed path inside the **Test repo** where generated tests are pushed to compile:
`src/test/java/autogen`, matching the `package autogen;` every generated file declares — Gradle's
`java` plugin default test source set, plus the package statement. Established once by
`/iadc-tester:setup`'s build file (IV-368), not asked as a per-project question, and **not
per-project state at all**: every **Test repo** gets the same answer, independent of wherever
**Harness path** points on any given machine. That settles IV-365's open question — it is neither
"inside" nor "outside" the harness, because the two no longer relate.

**Test repo**:
The git repository holding the generated test files, the Gradle build file that compiles them, and
the committed `appian-selenium-api.jar` they compile against — the durable home for all three,
separate from the **Test harness** a developer extracts locally to generate tests. Committed-tier.

### Reconciliation

**Feature**:
A single application + workflow/action combination — "Add Rule in the Isaac Sandbox application".
The **unit of matching** between a ticket's acceptance criteria and the test suite: all criteria for
one workflow on one application stay together, and a feature resolves to exactly one test file.
Most tickets describe one feature. This is the term the whole reconciliation process is defined in.
_Avoid_: "test case", "scenario" (both suggest a single `@Test` method; a feature may span
several)

**Reconciliation**:
Matching a ticket's requirements against the existing suite and producing the minimal change:
already-covered requirements are left alone, genuinely new ones are added, and contradicting ones
get the smallest replacement that resolves the contradiction. Distinct from generating a suite from
scratch, which is the case where a **Feature** has no existing file.

## Conformance

This context defines only the terms above. Three bodies of vocabulary are used here and owned
elsewhere; none is restated locally, and a duplicate definition is a defect rather than a nuance.

- **App Graph** — owned by **Core**, used exactly as `IADC-Core/CONTEXT.md` defines it.
- **Catalog** and **Advisory posture** — owned by **Advisor**, used exactly as
  `IADC-Advisor/CONTEXT.md` defines them.
- **Per-project state** and its two tiers — a family **convention**, not a term of either product,
  owned by the umbrella at `docs/agents/per-project-state.md`.
