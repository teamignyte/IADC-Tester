---
name: generate-selenium-tests
description: Sync Appian Selenium tests with a Jira ticket's requirements — updates existing test files where their feature already has one, and creates new JUnit test files where it doesn't. Use when the user gives a Jira ticket key and asks to sync, update, or reconcile tests with a ticket (e.g. "sync tests for IV-201", "update the test suite for the new Isaac Sandbox requirements"). The Appian application is read from this project's own configuration, not resolved from the ticket — the user does not need to name it. Internally invokes the iadc-graph skill to build a dependency graph of the relevant interface(s) before pulling any SAIL source, so the SAIL trace is scoped by the actual App Graph rather than discovered ad hoc.
argument-hint: [jira-ticket-key]
---

$1 is the Jira ticket

This skill reconciles a Jira ticket's requirements against the existing test
suite: matching requirements get left alone, new non-conflicting requirements
get added to an existing file, conflicting requirements get the minimal
necessary replacement, and requirements with no existing coverage get a new
file — all following the same JUnit 5 / Appian Selenium API conventions as
straightforward new-test generation.

Steps:

0. Resolve this project's configuration before doing anything else. Every value below
   resolves the same way — environment variable, then `docs/agents/tester.md` (or
   `docs/agents/tester.local.md` for the one machine-specific value), then ask the user —
   per the family's per-project-state convention. Check the environment variable for each
   value **first, before touching either file**: a pipeline run may set every one of the
   eight this way, with no repo to read and no user to ask, and that is a complete
   resolution on its own — proceed without either file existing. Only for a value with no
   environment variable set, read the matching file; a placeholder left standing (`<...>`)
   means it's still unset there. Only once *both* tiers have failed for a value is it time
   to ask the user — and only then, if neither config file exists at all, tell them to run
   `/iadc-tester:setup` first rather than answering one field at a time.

   - **Application UUID** — env `TEST_APPLICATION_UUID`, then `tester.md`.
   - **Test repo** — env `TEST_REPO`, then `tester.md`. The git repository holding the
     generated test files.
   - **Branch** — env `TEST_BRANCH`, then `tester.md`. The branch in the Test repo that
     generated files are pushed to.
   - **Test site URL** — env `TEST_SITE_URL`, then `tester.md`.
   - **Site web address** — env `IADC_SITE_URL`, then `tester.md`. The site's internal
     web address, used for `navigateToSite` once signed in.
   - **Test username** — env `TEST_USERNAME`, then `tester.md`.
   - **Site version** — env `TEST_SITE_VERSION`, then `tester.md`.
   - **Harness path** — env `TEST_HARNESS_PATH`, then `tester.local.md` (this one is
     machine-specific, not `tester.md`). The absolute filesystem path to the extracted
     Appian Selenium API distribution — read in step 6 for its Javadoc and
     `ExampleProjects` reference material only. Not needed to compile: generated tests
     compile against `appian-selenium-api.jar`, committed in the Test repo by
     `/iadc-tester:setup` (see step 8).

   `TEST_BROWSER`, `TEST_SITE_LOCALE` and `TEST_TIMEOUT` are not per-client — see step 6.

1. Pull the acceptance criteria for $1 via the Atlassian MCP connector.
   Group the acceptance criteria into features, where a feature is a single application +
   workflow/action combination (e.g. "Add Rule in the Isaac Sandbox
   application," "Update Rule in the Isaac Sandbox application"). All
   acceptance criteria belonging to the same workflow/action on the same
   application stay together as one feature — do not split a single
   workflow's criteria into smaller pieces for matching purposes. A ticket
   most often describes just one feature this way, but a ticket that
   genuinely spans multiple distinct workflows or applications produces one
   feature per workflow/application combination, and each is matched and
   handled independently in step 3 onward. For requirements about a 
   field/button/component's presence or absence, see references/sail-tracing.md
   for how that differs from a requirement that only implies existence.

2. Use the application UUID resolved in step 0.

   2a. **Build the dependency graph before pulling any SAIL.** Once the
       application UUID is in hand, invoke the `iadc-graph:iadc-graph` skill
       (the doubled name is correct — it is the skill `iadc-graph` inside
       the plugin `iadc-graph`) to build the
       dependency graph for this application's relevant interface(s) —
       follow iadc-graph's own SKILL.md for its full sequence and reference
       files; do not skip or reorder any of it, and do not shortcut
       straight to a query tool. The only thing this skill overrides:
       when seeding, pass this project's application UUID (from step 0) as
       the `application_uuid` argument directly. If seeding fails because the
       `iadc` MCP server isn't configured yet, tell the user to run
       `/iadc-graph:setup` — that's the fix; nothing here works around it.
       Once seeded, use `list_nodes` — the structural-filter tool, and the
       direct replacement for the old `listInterfaces` call — to resolve
       the interface(s) relevant to each feature identified in step 1 to
       their graph nodes (`find_nodes` is iadc-graph's other discovery
       tool, for locating one already-named node by search — not what this
       enumeration needs). From there, walk each interface's dependencies
       (sub-interfaces, rules, record types, constants) per iadc-graph's
       own instructions. This dependency set is what step 2b reads SAIL
       for.

   2b. Read SAIL for every node in 2a's dependency set: `get_sail` for the
       interface(s), sub-interfaces, rules, and constants — a constant's
       own SAIL is typically empty, which is a real, expected answer there,
       not a failure. For a record type, use `record_model` instead: what a
       grid or field actually draws its values from is that record type's
       fields, views, actions and relationships, and `record_model` is the
       one-call read for exactly that substructure — `get_sail` doesn't
       return it. Read the full SAIL source returned, not just
       field/component/label names — see
       references/sail-tracing.md for how to trace rendered values,
       editability, and structural/behavioral grid properties (pagination,
       sort order, etc.), using 2a's dependency list as the scope and
       order for that trace rather than re-discovering references by
       re-reading SAIL top to bottom.

3. Search the Test repo resolved in step 0 (via the GitHub MCP
   connector) for existing test files relevant to each feature from step 1.
   Match by content, not just filename — a file's class name, business-
   description comment, and existing `@Test` methods are more reliable
   signals than the filename alone. A file matches a feature when it already
   tests that same application + workflow/action combination, even if the
   specific requirements within it differ. For each feature:
     - If an existing file already covers this feature's application +
       workflow/action → that file is the target for step 5 (editing), and
       *all* of this feature's requirements go there — do not split one
       feature's requirements across multiple files.
     - If no existing file covers it → it needs a new file, created the same
       way as steps 4-9 of a from-scratch test generation (scaffold, constants,
       `@BeforeAll`/`@AfterAll`, one or more `@Test` methods, cleanup).
   Most tickets describe a single feature and resolve entirely to one file
   (either one existing file to edit, or one new file to create). A ticket
   only produces both an edit and a new file — or edits to multiple existing
   files — when it genuinely spans more than one application/workflow
   feature per step 1's grouping; in that case, route each feature to its
   own target independently, rather than defaulting to a single file for the
   whole ticket.

4. For every existing file identified as a target in step 3, pull it into the
   current directory (via the GitHub MCP connector's file-read/download
   tool) and read it in full before making any edit. Do not edit a file you
   have not fully read. Make sure the file is saved in the current directory before moving on.

5. For each feature whose target is an existing file, reconcile the ticket's
   requirements against what the file already does. See
   references/test-merging.md for the full decision process, but the
   short version: requirements already covered are left untouched;
   genuinely new and non-conflicting requirements are added (to an existing
   `@Test` method if they extend the same save/output being verified there,
   or as a new `@Test` method if they verify a distinct behavior); and
   requirements that actually contradict something the file currently
   asserts or does get the minimal necessary replacement — only the
   specific contradicting lines, not the surrounding method or file.

   Every edit to an existing file must still follow the same conventions as
   new test generation:
     - JUnit 5 (`org.junit.jupiter.api.*`), using `assertEquals`/
       `assertTrue`/`assertFalse`, never a manually thrown `AssertionError`.
     - Click a field before writing to it, and guard the write per
       references/field-editability.md — a field's read-only appearance
       before being clicked is not reliable.
     - Any grid/list verification follows references/grid-verification.md —
       never assume a collection starts empty or at a known count; locate
       the exact record by its unique identifying value, and account for
       pagination. When selecting a row/entry, always use the variable set
       by that search — never hardcode a row/index literal.
     - Any step that navigates within the site (site pages, top-level menu
       items, etc.) follows references/site-navigation.md — confirm the
       navigation mechanism and exact name actually apply to this site
       rather than assuming a common Appian default, and prefer reusing a
       prior working navigation step over regenerating one from scratch.
     - Reuse the file's own existing `@BeforeAll`/`@AfterAll` setup and
       constants as-is if they already match the values below; do not
       duplicate setup or introduce a second fixture instance.

   Do not add validation-error checks, existence checks, or field-state
   checks beyond what the criteria explicitly require, even if they seem
   like reasonable defensive additions — this applies to additions to
   existing files just as much as to new ones.

6. For each feature whose target is a new file, create it following the same
   process as generating a test from scratch:
     - Create the empty file as (testname/description).java in the current
       directory, named to match its public class.
     - Read the Appian Selenium API reference materials at the Harness path
       resolved in step 0 — the ExampleProjects/appian-selenium-api-example-java
       folder for usage patterns, and the Javadoc/ folder for the full list of
       available methods. Confirm methods against the Javadoc rather than
       assuming; confirm whether the fixture exposes an editability check —
       see references/field-editability.md.
     - Declare `package autogen;` as the file's first line — the fixed package every
       generated test uses, matching the `src/test/java/autogen/` layout
       `/iadc-tester:setup` establishes in the Test repo (step 8 pushes there).
     - Structure it as a JUnit 5 test class: `private static SitesFixture
       fixture;` field, a `@BeforeAll` static setup method (construct,
       configure, log in), an `@AfterAll` static teardown method
       (`fixture.tearDown()`). No `main` method, no manual try/finally.
     - Use the values resolved in step 0 for these setup constants — do not
       substitute, guess, or invent alternatives regardless of what the
       ticket or application name might suggest:
       - `TEST_SITE_URL` — the Test site URL.
       - `IADC_SITE_URL` — the Site web address (used for
         navigation once signed in, via `navigateToSite`).
       - `TEST_USERNAME` — the Test username (the only username confirmed
         to have a matching entry in `users.properties`).
       - `TEST_SITE_VERSION` — the Site version.

       These three are not per-client — always use exactly these values:
       `TEST_BROWSER = "CHROME"`, `TEST_SITE_LOCALE = "en_US"`, `TEST_TIMEOUT = 60`.
     - Group related criteria into one `@Test` method where they verify the
       same underlying save/output; only split into separate `@Test`
       methods for genuinely distinct behaviors or outcomes.
     - Follow the same field-click/editability-guard and grid-verification
       rules from step 5 above.
     - Follow the same site-navigation rules from step 5 above
       (references/site-navigation.md) for every navigation step — do not
       assume a common Appian navigation tab/menu name applies to this site
       without confirming it.
     - Every `@Test` method that creates, modifies, or otherwise persists
       data (a new record, rule, row, etc.) must include cleanup for that
       specific data, in the test method itself or in
       `@AfterEach`/`@AfterAll` as appropriate — this is not optional or
       conditional on it seeming necessary. There are exactly two legitimate
       reasons to have no cleanup in a given `@Test` method, and no others:
         1. **Nothing was persisted.** The test's action doesn't create or
            modify any lasting data in the first place (e.g., a Cancel-path
            test that verifies nothing was saved, or a test that only reads
            existing data). Confirm this from what the test actually does,
            not from assumption — if the test submits/saves/creates
            anything, this exemption doesn't apply.
         2. **No mechanism exists to reverse it.** Something was persisted,
            but the Javadoc/example projects have no delete, deactivate, or
            other reversing action available for that object type — confirm
            this by actually checking the Javadoc, not by assuming one
            doesn't exist because it wasn't immediately obvious. When this
            is the reason cleanup is absent, say so directly with a comment
            at the point where cleanup would go (e.g., "// No cleanup
            mechanism available via this fixture for <object type>"),
            so the omission is a documented decision, not a silent gap.
       Do not skip cleanup for any other reason — not because a test
       appears to pass without it, because the leftover effect seems minor,
       or because other tests in the same file don't need it.
       Before any cleanup step that deletes, deactivates, or otherwise acts
       on a specific grid/list entry, re-locate that entry using the same
       search method used to find it earlier in the test, rather than
       reusing a previously saved row/index value directly.

7. Before finishing each file (new or edited), re-read it in full and
   confirm: every assertion maps to a specific acceptance criterion from the
   ticket (remove any that don't); every `populateFieldWith` (or equivalent)
   call — including ones inside shared helper methods used by multiple
   `@Test` methods — has the click-first step and an editability guard per
   references/field-editability.md, with no field assumed safe without it;
   every pagination-navigation loop (page-1 reset, page-through scanning)
   has a hard iteration cap per references/grid-verification.md, not just an
   exception/return-based exit condition; every clickable trigger (button or
   link-styled action) uses the fixture method matching its actual traced
   SAIL component per references/sail-tracing.md, not one inferred from its
   label or wording; every `@Test` method that creates
   or modifies persistent data has actual cleanup for that specific data —
   and for any method with no cleanup, confirm it falls under one of the
   two legitimate exemptions from step 6 (nothing was persisted, or no
   reversing mechanism exists per the Javadoc) and has a comment
   documenting which, rather than cleanup simply being missing; nothing was
   left half-edited from step 5's replacement process; and, for edited
   files, everything that wasn't supposed to change is still intact exactly
   as it was pulled in step 4.

8. Save each file (new or edited) then push it to `src/test/java/autogen/` in
   the Test repo resolved in step 0, on the Branch resolved in step 0, using the GitHub MCP
   server's file creation/update tool — not the repo root. `/iadc-tester:setup` establishes
   a Gradle build there whose default test source set is `src/test/java`; every generated
   file's own `package autogen;` (step 6) supplies the rest of the path, so this is where it
   must land to compile. Push each file individually so an edited file updates its existing
   repo entry rather than creating a duplicate.

Constraints:
- Do not run the tests.
- Do not comment on or update the Jira ticket.
- Only touch files whose corresponding feature was actually identified in
  steps 1 and 3 — do not modify unrelated test files while in the repo.
- Every generated or edited file must be a JUnit 5 test class
  (`org.junit.jupiter.api.*`), not a `main`-method-based script.
