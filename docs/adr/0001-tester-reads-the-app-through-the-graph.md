---
status: accepted
---

# The Tester reads the application through the graph only

## Context

`generate-selenium-tests` reached the Appian MCP three times: `listApplications` to resolve which
application a ticket's Jira project corresponds to, then `listInterfaces` and `getInterface` to pull
SAIL source.

That server is a stdio `lcp_mcp_server` needing `LCP_URL`, `LCP_USERNAME` and `LCP_PASSWORD` in a
`.mcp.json` — and the only thing in the family that writes one is **Advisor's** `/setup`. So a
client who installed the Tester alone, which the family's
[ADR 0008](https://github.com/teamignyte/IADC/blob/main/docs/adr/0008-tester-ships-as-its-own-plugin-with-a-bundle.md)
makes a supported shape, had no Appian credentials and no way to get them. The plugin's standalone
gap was never the two hardcoded paths people noticed first; it was a live Appian login.

Meanwhile the skill **already seeds the graph** before pulling any SAIL, precisely so the trace is
scoped by real dependencies rather than discovered ad hoc. And the graph serves `get_sail`,
`list_nodes`, `find_nodes` and `record_model`. Everything the Appian MCP was being asked for was
already available from a server the skill had just seeded.

The application resolution was its own problem. It matched a Jira project name against Appian
application names by heuristic — "initials, partial name overlap, obvious abbreviation" — and
stopped to ask the user when more than one was plausible. A **Pipeline run** has nobody to ask.

## Decision

**The Tester reads the application through the graph and never calls the Appian MCP.**

| was | now |
|---|---|
| `listApplications` + heuristic matching | the application UUID, recorded in config |
| `listInterfaces` | `list_nodes` / `find_nodes` |
| `getInterface` | `get_sail` |

The application UUID becomes a recorded per-project value, resolved once and written down rather
than looked up per run. This is Advisor's **no-live-lookup** rule — established in its ADR 0003 and
preserved through its ADR 0010 — applied here for the first time. It assumes the per-app-repo model
the family already uses: one repo per Appian application, so one UUID.

## Considered options

- **Ship `.mcp.json` machinery for the `appian` server too.** Rejected: it would put a live Appian
  username and password in every Tester client repo in order to fetch data the graph already holds,
  and would duplicate Advisor's credential-safety prose into a second plugin.
- **Document the `appian` server as a prerequisite and let the user wire it.** Rejected: the worst
  standalone experience of the three, and it still leaves Appian credentials in the client repo.
- **Keep the live lookup but record only the credentials.** Rejected: it does not fix the
  **Pipeline run**, where the ambiguity prompt has nobody to answer it.

## Consequences

- **A Tester-only client repo holds no Appian credentials at all** — only a graph URL and its API
  key, written by `iadc-graph:setup` (family
  [ADR 0010](https://github.com/teamignyte/IADC/blob/main/docs/adr/0010-graph-plugin-owns-graph-configuration.md)).
- **The skill becomes runnable unattended.** Deleting the heuristic-matching block removes its
  stop-and-ask branch, which was the only thing in the resolution path that required a human.
- **SAIL now comes from the seeded export, not the live object.** The skill seeds fresh on every
  run, so the window is small — but it is not zero, and a design object edited mid-run will not be
  reflected. `report_changes` exists for the case where that matters.
- **Step 2a's reference to "iadc-graph's own Configuration block" is deleted.** That block no longer
  exists — Advisor's ADR 0010 stripped it and the marketplace mirror carries none — so the documented
  fallback had already gone stale.
- The ticket's Jira project is no longer needed at all: nothing else in the skill reads it, so step 1
  no longer retrieves it.
