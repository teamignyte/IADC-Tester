# IADC-Tester

The **`iadc-tester`** Claude Code plugin — part of the [IADC](https://github.com/teamignyte/IADC)
family.

It syncs an Appian application's Selenium test suite with a Jira ticket's requirements: updating
existing test files where a feature already has one, and creating new JUnit files where it doesn't.
You give it a ticket key; it works out the rest.

```
/generate-selenium-tests IV-201
```

The Appian application under test is resolved from the ticket's Jira project — you don't name it.
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

## Not installable yet

`IADC-Marketplace` does not exist, so nothing lists this plugin and `iadc-graph` is not yet
published as one. Until both land, the `dependencies` entry cannot resolve and this repo is a
plugin in shape only.

One open item for that work: plugin skills are namespaced `plugin:skill`, so the address the
`generate-selenium-tests` skill uses to reach the graph skill changes once `iadc-graph` ships as a
plugin. A stale reference fails **silently** rather than erroring, so the address should be
confirmed against a real install rather than assumed — which is why the skill's prose is left
untouched here.
