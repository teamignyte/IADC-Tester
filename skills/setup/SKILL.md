---
name: setup
description: Configure the iadc-tester plugin for this Appian project — write the per-project test configuration into this repo, then hand off to `/iadc-graph:setup` for the graph connection. Run once per app repo after installing the plugin, before first use of `generate-selenium-tests`.
disable-model-invocation: true
---

# Setup

Configure the plugin for the Appian project you're pointing it at. The plugin itself is installed
out of this repo, in a shared cache that is read-only and replaced on every update — so it holds
**no** per-project values and can ship **no** files here. This skill is what materializes them: it
collects the real values and **generates** the per-project state in this repo.

This is a prompt-driven skill, not a deterministic script. Explore, present what you found, confirm
with the user, then write. Take it one field at a time — one question, one answer, then the next.

## Process

### 1. Explore

Read the current state; don't assume:

- `docs/agents/tester.md` and `docs/agents/tester.local.md` — which exist from a prior run? Don't
  re-ask a field that already carries a real answer; only ask about one still showing its `<...>`
  placeholder.
- `.gitignore` — does it already have the `docs/agents/tester.local.md` entry?
- `.mcp.json` — does an `iadc` entry already exist and work? Check whether tools named
  `mcp__iadc__*` (e.g. `mcp__iadc__seed`) are available in this session — their presence means the
  entry was already live when this session started. If so, step 5 below is already satisfied.

### 2. Establish the ignore rule for the one per-machine value

`docs/agents/tester.local.md` is the only file this skill writes that must never be committed — it
holds the Harness path, which differs per machine. **This step runs before that file is written**,
so a `git add -A` in the gap between the two never stages it.

Check whether `.gitignore` at the repo root already contains this exact line:

```
# iadc-tester per-project state — personal to this machine, never committed
docs/agents/tester.local.md
```

- **Already there** — nothing to add. Continue to step 3.
- **Missing** — show the user the line and get an explicit yes before adding it. Create
  `.gitignore` if it doesn't exist yet.
  - **Decline** — add nothing, and don't ask again this run. **Skip step 4 entirely this run
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
carries a real answer; only ask about one still showing its `<...>` placeholder.

**Keep the template's field labels verbatim** — `Application UUID`, `Test repo` (+ `Branch`),
`Test project folder`, `Test site URL`, `Site web address`, `Test username`, `Site version` —
`generate-selenium-tests` matches on those exact labels; rename or reword one and the value simply
stops being found.

Fill every value **in place**, replacing the `<...>` placeholder with a real answer. Never invent a
value, and never delete a line unless the template says to.

- **Application UUID** — the Appian application these tests cover, and the seed target for the
  `iadc` graph. Take it from the user; this plugin doesn't configure a live Appian connection to
  look it up itself.
- **Test repo** (+ **Branch**) — the GitHub repository, and the branch on it, that the generated
  test files are pushed to.
- **Test project folder** — where this application's generated tests must sit. Record the user's
  answer as given. How it relates to the Harness path (step 4) is a separate, still-open question —
  don't tell the user it sits inside or outside the harness tree; this skill only collects the
  value.
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

### 4. Set the machine value

**Only if step 2's ignore rule is in place** (already there, or just accepted) — collect the
**Harness path**: the absolute filesystem path to the extracted Appian Selenium API distribution on
this machine. Write it into **`docs/agents/tester.local.md`**, from this skill's
[tester-local-config-template.md](./tester-local-config-template.md).

If step 2 was declined, this step doesn't run this session — step 2 already said so.

### 5. Hand off to `/iadc-graph:setup` for the graph connection

`generate-selenium-tests` reaches the graph over the `iadc` MCP server, configured in this repo's
`.mcp.json`. This skill does not configure that server itself: writing that entry means writing a
credential, and `iadc-graph:setup` is the one place in the family that does — installed
automatically as this plugin's declared dependency, and running its own credential-safety sequence
(family ADR 0010, "the graph plugin owns graph configuration"). That skill carries
`disable-model-invocation: true`: Claude cannot invoke it, only the user can, by typing the command.

**Tell the user to run `/iadc-graph:setup`** — unless step 1 already found a working `iadc` entry
(`mcp__iadc__*` tools present in this session), in which case say so instead and skip the ask:
`iadc-graph:setup` also skips itself when it finds a working entry, so a user with both
`iadc-advisor` and `iadc-tester` installed is never asked for the same URL and key twice.

### 6. Review everything this run touched

Re-show, in one place, everything the run touched, so the user sees the whole shape of it before you
call setup done:

- **`docs/agents/tester.md`** — every field, or a note that a field is still a placeholder and why.
- **`docs/agents/tester.local.md`** — written, or deliberately skipped because step 2's ignore rule
  was declined.
- **The `.gitignore` line** — added, already present, or declined.
- **The `iadc` handoff** — told to the user, or skipped because a working entry already exists.

### 7. Verify

- `docs/agents/tester.md` exists and every field carries a real answer — any `<...>` still standing
  means that field is genuinely unset, not done.
- If `docs/agents/tester.local.md` was written, confirm it's actually ignored:
  `git check-ignore docs/agents/tester.local.md` succeeds. If step 2's ignore rule was declined,
  this file was never written (step 4) — nothing to check.
- Tell the user which command to run next — `/iadc-graph:setup`, if step 5 didn't already find a
  working entry — and that `generate-selenium-tests` is otherwise ready to use.

### 8. Done

Tell the user setup is complete. They can edit `docs/agents/tester.md` and
`docs/agents/tester.local.md` directly later — re-run this skill only to re-point the plugin at a
different Appian project.
