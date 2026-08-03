---
name: generate-selenium-tests
description: Sync Appian Selenium tests with a Jira ticket's requirements — updates existing test files where their feature already has one, and creates new JUnit test files where it doesn't. Use when the user gives a Jira ticket key and asks to sync, update, or reconcile tests with a ticket (e.g. "sync tests for IV-201", "update the test suite for the new Isaac Sandbox requirements"). The Appian application is determined automatically from the ticket's Jira project — the user does not need to name it. Internally invokes the iadc-graph skill to build a dependency graph of the relevant interface(s) before pulling any SAIL source, so the SAIL trace is scoped by the actual App Graph rather than discovered ad hoc.
argument-hint: [jira-ticket-key]
---

$1 is the Jira ticket

Repo: michael-tulino/AutomatedTesting
Branch: main

This skill reconciles a Jira ticket's requirements against the existing test
suite: matching requirements get left alone, new non-conflicting requirements
get added to an existing file, conflicting requirements get the minimal
necessary replacement, and requirements with no existing coverage get a new
file — all following the same JUnit 5 / Appian Selenium API conventions as
straightforward new-test generation.

Steps:

1. Pull the acceptance criteria for $1 via the Atlassian MCP connector. As
   part of this same lookup, also retrieve the ticket's Jira project (key and
   name) — this identifies which board/application area the ticket belongs
   to, and is used in step 2 to resolve the Appian application without the
   user needing to name it.
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

2. Use listApplications to get the full list of Appian applications, then
   determine which application the ticket's Jira project (from step 1)
   corresponds to. The Jira project name may be an abbreviation or partial
   match of the actual Appian application name (e.g., a Jira project called
   "IADC v2" may correspond to an Appian application named "Ignyte Appian
   Developer Copilot") — do not assume an exact string match. Use reasonable
   matching (initials, partial name overlap, obvious abbreviation) to
   identify the correct application. If more than one application is a
   plausible match, or none are, stop and ask which application to use
   rather than guessing.

   2a. **Build the dependency graph before pulling any SAIL.** Once the
       application is confirmed, invoke the iadc-graph skill to build the
       dependency graph for this application's relevant interface(s) —
       follow iadc-graph's own SKILL.md for its full sequence and reference
       files; do not skip or reorder any of it, and do not shortcut
       straight to a query tool. The only thing this skill overrides:
       when seeding, pass this ticket's already-resolved application UUID
       (from above) as the `application_uuid` argument directly, rather
       than reading it from iadc-graph's own Configuration block — that
       block is only a fallback default for when iadc-graph is invoked
       standalone with no UUID already in hand, which isn't the case here.
       Once seeded, resolve each relevant interface (from listInterfaces
       below) to a graph node and walk its dependencies (sub-interfaces,
       rules, record types, constants) per iadc-graph's own instructions.
       This dependency set is what guides step 2b below: it tells you
       which objects actually need a getInterface (or equivalent) call,
       instead of discovering references ad hoc while reading SAIL text.

   2b. Use listInterfaces scoped to that application's UUID. Call
       getInterface on the interface(s) relevant to each feature identified
       in step 1 **and on every additional node 2a's graph identified as a
       dependency of those interfaces** (sub-interfaces, referenced rules,
       record types feeding grid/field values). Read the full SAIL source
       returned, not just field/component/label names — see
       references/sail-tracing.md for how to trace rendered values,
       editability, and structural/behavioral grid properties (pagination,
       sort order, etc.), using 2a's dependency list as the scope and
       order for that trace rather than re-discovering references by
       re-reading SAIL top to bottom.

3. Search the michael-tulino/AutomatedTesting repo (via the GitHub MCP
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
     - Read the Appian Selenium API reference materials at
       C:\Users\tulin\Downloads\Ignyte\Appian Selenium API Combined Files 5302025
       — the ExampleProjects\appian-selenium-api-example-java folder for
       usage patterns, and the Javadoc\ folder for the full list of
       available methods. Confirm methods against the Javadoc rather than
       assuming; confirm whether the fixture exposes an editability check —
       see references/field-editability.md.
     - Structure it as a JUnit 5 test class: `private static SitesFixture
       fixture;` field, a `@BeforeAll` static setup method (construct,
       configure, log in), an `@AfterAll` static teardown method
       (`fixture.tearDown()`). No `main` method, no manual try/finally.
     - Always use these exact values for the setup constants — do not
       substitute, guess, or invent alternatives regardless of what the
       ticket or application name might suggest:
       - `TEST_SITE_URL = "https://ignytedemo.appiancloud.com/suite"`
       - `IADC_SITE_URL = ignyte-appian-developer-copilo` (used for
         navigation once signed in, via `navigateToSite`).
       - `TEST_USERNAME = "automated.tester"` (the only username confirmed
         to have a matching entry in `users.properties`).
       - `TEST_BROWSER = "CHROME"`, `TEST_SITE_VERSION = "24.3"`,
         `TEST_SITE_LOCALE = "en_US"`, `TEST_TIMEOUT = 60`.
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

8. Save each file (new or edited) then push it to the root of
   michael-tulino/AutomatedTesting on the main branch, using the GitHub MCP
   server's file creation/update tool. Push each file individually so an
   edited file updates its existing repo entry rather than creating a
   duplicate.

Constraints:
- Do not run the tests.
- Do not comment on or update the Jira ticket.
- Only touch files whose corresponding feature was actually identified in
  steps 1 and 3 — do not modify unrelated test files while in the repo.
- Every generated or edited file must be a JUnit 5 test class
  (`org.junit.jupiter.api.*`), not a `main`-method-based script.
