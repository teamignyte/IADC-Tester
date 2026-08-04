---
name: setup
description: Configure the iadc-tester plugin for this Appian project — write the per-project test configuration into this repo, establish the Test repo's Gradle build and commit the Appian Selenium API jar generated tests compile against, then hand off to `/iadc-graph:setup` for the graph connection. Run after installing the plugin, before first use of `generate-selenium-tests`, and again whenever that skill reports this Test repo hasn't been through it yet.
disable-model-invocation: true
---

# Setup

Configure the plugin for the Appian project you're pointing it at. The plugin itself is installed
out of this repo, in a shared cache that is read-only and replaced on every update — so it holds
**no** per-project values and can ship **no** files here. This skill is what materializes them: it
collects the real values and **generates** the per-project state in this repo — and, in step 4,
generates the build the Test repo needs to compile what `generate-selenium-tests` pushes to it.

This is a prompt-driven skill, not a deterministic script. Explore, present what you found, confirm
with the user, then write. Take it one field at a time — one question, one answer, then the next.

## Process

### 1. Explore

Read the current state; don't assume:

- `docs/agents/tester.md` and `docs/agents/tester.local.md` — which exist from a prior run? Don't
  re-ask a field that already carries a real answer; only ask about one still showing its `<...>`
  placeholder.
- `.gitignore` — does it already have the `docs/agents/tester.local.md` entry?
- Are `mcp__iadc__*` tools (e.g. `mcp__iadc__seed`) present in this session? Their presence is
  useful context for step 6 — it means an entry already *looks* live — but it settles nothing on
  its own (a **tracked** `.mcp.json` can still pass this check) and it doesn't skip anything below.
  This skill has no other reason to read `.mcp.json` itself; `iadc-graph:setup` owns that file.

### 2. Establish the ignore rule for the one per-machine value

`docs/agents/tester.local.md` is the only file this skill writes that must never be committed — it
holds the Harness path, which differs per machine. **This step runs before that file is written**,
so a `git add -A` in the gap between the two never stages it.

Check whether `.gitignore` at the repo root already has each of these lines — check them
independently, not as a single block; a repo that already ignores `docs/agents/tester.local.md`
without the comment above it has the line that matters and needs nothing added:

```
# iadc-tester per-project state — personal to this machine, never committed
docs/agents/tester.local.md
```

- **Both lines already there** — nothing to add. Continue to step 3.
- **Either line is missing** — show the user exactly which line(s) are missing and get an explicit
  yes before adding them. Create `.gitignore` if it doesn't exist yet.
  - **Decline** — add nothing, and don't ask again this run. **Skip step 5 entirely this run
    too** — don't write `docs/agents/tester.local.md` ungitignored, which would make a
    machine-specific value trackable, the exact outcome the ignore rule exists to prevent. Say
    plainly what that means: the Harness path stays unset until the repo ignores that file (this
    run or a later one); `generate-selenium-tests` will ask for it directly until then.
    `docs/agents/tester.md` (step 3) is unaffected and proceeds normally.

### 3. Set the project values

Collect these and write them into **`docs/agents/tester.md`**, from this skill's
[tester-config-template.md](./tester-config-template.md) — never into any `SKILL.md` (plugin
skills are shared, read-only, and replaced on update; the family's per-project-state convention).
`generate-selenium-tests` reads this file at the point of use, as its own step 0.

**On a repo that already has real values here** — a prior run — don't re-ask a field that already
carries a real answer; only ask about one still showing its `<...>` placeholder. **If a `Test
project folder` line is still there from a run before IV-368, delete it** — nothing reads that
field any more (see step 4): the layout is now fixed at `src/test/java/autogen/`, established by the
build file rather than recorded as a per-project answer, so a leftover line here is stale, not
merely unread.

**Keep the template's field labels verbatim** — `Application UUID`, `Test repo` (+ `Branch`),
`Test site URL`, `Site web address`, `Test username`, `Site version` in `tester.md`, and
`Harness path` in `tester.local.md` (step 5) — `generate-selenium-tests` matches on those exact
labels; rename or reword one and the value simply stops being found.

Fill every value **in place**, replacing the `<...>` placeholder with a real answer. Never invent a
value, and never delete a line unless the template says to.

- **Application UUID** — the Appian application these tests cover, and the seed target for the
  `iadc` graph. Take it from the user; this plugin doesn't configure a live Appian connection to
  look it up itself.
- **Test repo** (+ **Branch**) — the git repository, and the branch on it, that the generated
  test files are pushed to. Step 4 uses this same repo and branch to establish the build that
  compiles them — resolve it here first.
- **Test site URL** — the full URL used to sign in.
- **Site web address** — the site's internal web address, used for navigation once signed in.
- **Test username** — the Appian username these tests sign in as. Must have a matching entry in
  that project's `users.properties`.
- **Site version** — the Appian site version under test.

None of these fields has a deliberate "doesn't apply" answer — every one applies to every project
this plugin runs against, so leave a field the user can't answer yet as its `<...>` placeholder
rather than inventing a value.

**Per-person override:** none of these is a per-person value — the whole point of this tier is that
the team agrees on one answer for each. If a user's answer genuinely differs from what's already
committed here, that's a question for the team, not a `.local` override.

### 4. Establish the build in the Test repo

Generated tests declare `package autogen;` and import
`com.appiancorp.ps.automatedtest.fixture.SitesFixture` — pushed as bare `.java` source, none of
that compiles: there is no build file, no `autogen/` directory, and nothing on the classpath. It
compounds for a Test repo this plugin already pushed to before IV-368: Gradle's `java` plugin
compiles only `src/test/java`, so once the build file below exists, every file still sitting at the
Test repo's *root* is silently excluded from it — `gradle test` would report success having
compiled none of them. This step fixes all of that, in the **Test repo** (+ **Branch**) resolved in
step 3 — a different repo from the one this session is running in. It's the first thing this skill
writes there, via the GitHub MCP connector rather than a local file write; if that connector isn't
connected, this step fails outright the same way `generate-selenium-tests` step 8's push already
assumes it — this skill doesn't configure or check that connector any more than that one does.

**Check first**, with the GitHub MCP connector's file-read tool:

- Do `build.gradle` and `settings.gradle` already exist at the Test repo's root on the Branch? If
  so, leave them alone — don't re-fetch or overwrite anything a maintainer may have hand-edited.
- Does `lib/appian/appian-selenium-api.jar` exist there, **and does it match the pinned size and
  sha256 below** — not existence alone. A same-named file that doesn't match is either corrupt
  (e.g. written through a path that mangled it as text) or left over from an older pin; either way
  it needs replacing, not skipping.

All three present and matching means a prior run (or a maintainer) already did this — say so and go
straight to the root-level check below. Otherwise, fill in whatever's missing or mismatched:

- **The jar.** `appian-selenium-api.jar` has no Maven artifact — the vendor
  (`gitlab.com/appian-oss/appian-selenium-api`, Apache License 2.0) distributes it only as a
  generic GitLab package. Download it — e.g. `curl -L -o appian-selenium-api.jar
  <url>` — from:

  ```
  https://gitlab.com/api/v4/projects/appian-oss%2Fappian-selenium-api/packages/generic/FCS/20260725/appian-selenium-api.jar
  ```

  This URL needs **no authentication** — it's a public package on a public project. **Pinned:
  `FCS/20260725`, `367,045` bytes, sha256
  `80dcc7560f026aba27bc74de5a242eef4d1e80e5350e465e91a83aa55cdcece8`.** A maintainer moving to a
  newer release edits the version in the URL *and every place the size and sha256 are repeated* —
  the pin statement here, the confirm-after-push instruction later in this same bullet, step 8's
  Verify check, and `build.gradle.template`'s header comment — the same lag-never-lead pinning the
  family already uses for the mirrored graph skill (never track "latest"). Missing any one of them
  would defeat the check above: matching size/hash is what lets an existing Test repo's *next* setup
  run notice its jar is now stale and replace it, instead of either a stale number passing against
  itself or a correctly-updated jar failing a check that never got updated. Push the downloaded file
  to `lib/appian/appian-selenium-api.jar` in the Test repo, on the Branch, with the GitHub MCP
  connector's file creation/update tool.

  **This is a committed binary, deliberately.** The alternative — a developer downloading it by
  hand, onto a machine-specific path nothing else can see — is the defect IV-368 removes. Committing
  it is what lets a fresh clone of the Test repo compile this dependency with no network access and
  no login. Say this plainly to the user; `build.gradle.template`'s own header comment says it again
  at the point a Test-repo reader — who may never see this skill's prose — will actually find it.

  A binary written through a text/UTF-8 path comes out corrupt but still *exists*, so "the file is
  there" doesn't confirm the push worked. Where the GitHub MCP connector's tools expose a size or
  hash without a full download, use that; otherwise pull the content back — the same way
  `generate-selenium-tests` step 4 already pulls existing test files — and check it locally. Either
  way, confirm `367,045` bytes before treating this bullet as done.

- **The build file.** Push `skills/setup/build.gradle.template`'s content, unedited, to
  `build.gradle` in the Test repo, on the Branch, and `skills/setup/settings.gradle.template`'s
  content, unedited, to `settings.gradle`, on the Branch. Copy them verbatim — don't regenerate
  their content from memory. The
  dependency versions inside are measured against the vendor's own build of this exact jar, not
  guessed; changing them here would silently drop that guarantee.

**Then, regardless of whether either check above found anything to do, list the Test repo's root
on the Branch** for `.java` files sitting directly there. Nothing before this ticket ever pushed a file anywhere
else in this repo, so each is presumed to be a test this plugin generated before IV-368 and is now
silently excluded from the build for the reason above — but confirm that from its content rather
than deleting on the presumption alone. For each:
  - Read its content (GitHub MCP file-read tool).
  - Confirm it actually looks like one of this plugin's own generated tests — it imports
    `com.appiancorp.ps.automatedtest.fixture.SitesFixture`, or already declares `package autogen;`
    somewhere in it — before treating it as safe to migrate. If it matches neither signal, it isn't
    one of ours: leave it in place and list it in step 7's review instead of moving it.
  - If it doesn't already declare `package autogen;` before its first type declaration — check the
    file's content, not just whether line 1 is exactly that string; a file whose first line is the
    business-description comment `generate-selenium-tests` step 3 matches on still declares
    `package autogen;` on the line beneath it — prepend `package autogen;` as a new first line.
    Skip this for a file that already declares it anywhere; prepending regardless would write a
    second, uncompilable package declaration.
  - Push that content to `src/test/java/autogen/` under the same filename, via the GitHub MCP
    connector's file creation/update tool, then remove the root copy with its file-delete tool.
  - If no delete tool is available, don't leave this silent: list the file in step 7's review as
    moved but not removed, and tell the user to delete the root copy by hand once they've confirmed
    the new one is right. Two copies of the same test is a worse, quieter state than one copy the
    user still has to remove.

**This establishes the layout, not just the files.** `build.gradle` applies Gradle's `java` plugin
and declares no custom source sets, so it defaults to Gradle's standard test source root,
`src/test/java`. A file declaring `package autogen;` must sit in `src/test/java/autogen/` under
that root to compile — that fixed path is what `generate-selenium-tests` step 8 now pushes to, and
what the migration above just moved every pre-existing file to as well. It is **Test project
folder**, settled: always this path, inside the Test repo, unrelated to wherever **Harness path**
(step 5) points on this or any other machine — `docs/agents/tester.md` no longer carries a `Test
project folder` field, because there is no longer a project-specific question to record an answer
for.

**To build:** `gradle test` from the Test repo's root compiles and runs everything under
`src/test/java/autogen/`, and needs a JDK 11+ and Gradle itself installed locally — this repo ships
no wrapper. `gradle compileTestJava` checks compiling alone, with no live site needed.

### 5. Set the machine value

**Only if step 2's ignore rule is in place** (already there, or just accepted) — collect the
**Harness path**: the absolute filesystem path to the extracted Appian Selenium API distribution on
this machine. It is read only for the Javadoc and `ExampleProjects` reference material
`generate-selenium-tests` step 6 reads during generation — since step 4 above, no longer for
compiling. Write it into **`docs/agents/tester.local.md`**, from this skill's
[tester-local-config-template.md](./tester-local-config-template.md).

If step 2 was declined, this step doesn't run this session — step 2 already said so.

### 6. Hand off to `/iadc-graph:setup` for the graph connection

`generate-selenium-tests` reaches the graph over the `iadc` MCP server, configured in this repo's
`.mcp.json`. This skill does not configure that server itself: writing that entry means writing a
credential, and `iadc-graph:setup` is the one place in the family that does — installed
automatically as this plugin's declared dependency, and running its own credential-safety sequence
(family ADR 0010, "the graph plugin owns graph configuration"). That skill carries
`disable-model-invocation: true`: Claude cannot invoke it, only the user can, by typing the command.

**Tell the user to run `/iadc-graph:setup`, unconditionally.** If step 1 already saw `mcp__iadc__*`
tools present, say that too — an entry already looks live — but say it *alongside* the instruction,
not instead of it: tool presence doesn't rule out a **tracked** `.mcp.json`, which
`iadc-graph:setup` checks for and warns about (a committed credential is readable from git history
even after the file is untracked) and this skill has no way to check itself, since it never reads
that file. Say plainly that it can wait: before, during, or after this setup, in its own session,
since nothing here depends on it. That skill never silently overwrites a working entry. This skill
neither writes that entry nor waits on the other one.

### 7. Review everything this run touched

Re-show, in one place, everything the run touched, so the user sees the whole shape of it before you
call setup done:

- **`docs/agents/tester.md`** — every field, or a note that a field is still a placeholder and why.
- **`docs/agents/tester.local.md`** — written, or deliberately skipped because step 2's ignore rule
  was declined.
- **The `.gitignore` line** — added, already present, or declined.
- **The Test repo's build** — `lib/appian/appian-selenium-api.jar`, `build.gradle` and
  `settings.gradle`: freshly written, already present from an earlier run, or replaced because the
  jar didn't match the pinned size/hash.
- **Root-level `.java` files** — every one found and moved into `src/test/java/autogen/`; any that
  couldn't be removed automatically and still need deleting by hand; and any left in place because
  they didn't match the generated-test signal.
- **The `iadc` handoff** — told to the user (always), noting whether step 1 already saw a
  live-looking entry.

### 8. Verify

- `docs/agents/tester.md` exists and every field carries a real answer — any `<...>` still standing
  means that field is genuinely unset, not done.
- If `docs/agents/tester.local.md` was written, confirm it's actually ignored:
  `git check-ignore docs/agents/tester.local.md` succeeds. If step 2's ignore rule was declined,
  this file was never written (step 5) — nothing to check.
- With the GitHub MCP connector's file-read tool, confirm `build.gradle` and `settings.gradle`
  exist at the Test repo's root on the Branch, and that `lib/appian/appian-selenium-api.jar` exists
  there at `367,045` bytes — step 4 claiming to have written or found them isn't the same as them
  being there, and existence alone would miss a binary corrupted in transit.
- Confirm no `.java` file remains at the Test repo's root unless step 7 already accounts for it —
  moved in step 4, listed there as needing manual removal, or listed there as left in place because
  it didn't match the generated-test signal, not silently unaccounted for.
- Remind the user to run `/iadc-graph:setup` if they haven't yet — step 6 already told them once;
  repeat it here since this is close to the last thing they read. Don't call `generate-selenium-tests`
  ready to use: it also needs the Atlassian and GitHub connectors, which this skill neither
  configures nor checks. Say that plainly instead of claiming a readiness this skill hasn't
  established.

### 9. Done

Tell the user setup is complete, and how to use what step 4 just established: `gradle test` from
the Test repo's root compiles and runs everything under `src/test/java/autogen/` (a JDK 11+ and
Gradle itself must be installed locally — no wrapper is shipped). They can edit
`docs/agents/tester.md`, `docs/agents/tester.local.md`, and the Test repo's `build.gradle` directly
later — re-run this skill to re-point the plugin at a different Appian project, or whenever
`generate-selenium-tests` reports that the Test repo hasn't been through this step yet.
