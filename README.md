# IADC-Tester

The **`iadc-tester`** Claude Code plugin — part of the [IADC](https://github.com/teamignyte/IADC)
family.

It syncs an Appian application's Selenium test suite with a Jira ticket's requirements: updating
existing test files where a feature already has one, and creating new JUnit files where it doesn't.
You give it a ticket key; it works out the rest.

```
/generate-selenium-tests IV-201
```

The Appian application under test comes from this project's own configuration
(`docs/agents/tester.md`) — you don't name it.
Before pulling any SAIL, the skill builds a dependency graph of the relevant interfaces through the
**`iadc-graph`** skill, so the SAIL trace is scoped by the actual App Graph rather than discovered
ad hoc.

## Layout

```
.claude-plugin/plugin.json          the manifest
skills/generate-selenium-tests/     SKILL.md + references/
```

`skills/` is **auto-discovered** — it is deliberately not declared in `plugin.json`. Declaring
skills or hooks there as well registers the same paths twice, and the plugin then installs
successfully but loads nothing. `claude plugin validate` does not catch it.

## The graph dependency

`plugin.json` declares `dependencies: ["iadc-graph"]`, so installing this plugin also installs the
graph skill, pinned to the sha of the **deployed** graph server. That is not an extra requirement
imposed on the skill — its own frontmatter already states that it invokes `iadc-graph` before
pulling SAIL source.

The dependency is deliberately **unversioned**. It tracks whatever the marketplace entry provides,
which is the sha pin, so every consumer moves together when that pin moves. See the family's
[ADR 0003](https://github.com/teamignyte/IADC/blob/main/docs/adr/0003-shared-skills-ship-as-pinned-marketplace-plugins.md)
and [ADR 0008](https://github.com/teamignyte/IADC/blob/main/docs/adr/0008-tester-ships-as-its-own-plugin-with-a-bundle.md).

## Installing

This plugin is listed in the `ignyte` catalog and is installed from there, not from this repo:

```bash
claude plugin marketplace add https://github.com/teamignyte/IADC-Marketplace.git --scope project
claude plugin install iadc-tester@ignyte --scope project
```

`iadc-graph` comes with it. To get the advisory architect as well, install `iadc@ignyte`, the
bundle that pulls in both products.

## Addressing the graph skill

Plugin skills are namespaced `plugin:skill`, so this skill reaches the graph as
**`iadc-graph:iadc-graph`** — the skill `iadc-graph` inside the plugin of the same name. The
doubled name is correct, not a typo. It matters because a stale cross-skill reference **fails
silently**: Claude looks for a skill that isn't there, finds nothing, and carries on without the
graph rather than raising an error.
