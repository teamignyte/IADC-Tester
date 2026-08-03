# Verifying site navigation structure before generating navigation steps

Before generating any step that navigates within the target Appian site
(clicking a site page/tab, a top-level Tempo menu item, or any other
navigation entry point), confirm that entry point actually exists for this
specific site — do not default to a commonly-seen Appian navigation pattern
just because it's typical of Appian sites in general.

## The problem this guards against

Appian sites vary in which navigation surfaces they expose. A given site may
have Tempo-style top-level menu tabs (e.g. "News," "Records," "Tasks"),
site-specific page tabs configured for that site (e.g. "Settings,"
"Summary," a custom-named tab), or some mix of both — and which ones exist,
and what they're named, is specific to how that site was configured, not a
fixed set every Appian site has. Generating a navigation step for a tab like
"Records" because it's a common Tempo tab, without confirming this
particular site actually has it, produces a step that fails outright: the
fixture will wait the full configured timeout for an element that will
never appear, then throw a timeout/no-such-element exception — not a fast
failure, and not something that "mostly works."

## What to check before generating a navigation step

- Identify which navigation mechanism is actually appropriate: a site page
  tab (used via a site-page-click method) versus a top-level Tempo menu
  item (used via a menu-click method) are different mechanisms in the
  fixture, tied to different UI surfaces. Confirm which one applies to the
  target destination rather than assuming.
- Confirm the exact name of the page/tab/menu item as configured for this
  site, rather than a generic or guessed name. If the acceptance criteria,
  prior test files for the same application, or any tool output (e.g. site
  metadata) gives the actual configured name, use that name exactly.
- If a prior, working version of a test already navigates to the same
  destination successfully, treat that as strong evidence of the correct
  navigation mechanism and name for this site, and do not replace it with a
  different mechanism or name without a specific reason tied to a changed
  requirement. Reusing a previously-confirmed-working navigation step is
  preferable to regenerating one from a general assumption about typical
  Appian sites.
- If it's genuinely unclear which navigation mechanism or name applies (no
  prior working test, no confirming source), do not guess a common
  Appian default (e.g. "Records," "News," "Tasks") — surface the
  uncertainty rather than generating a step likely to fail outright.

## JUnit-specific note

Since a wrong navigation step fails at the very first interaction in a test
method (before any of the method's actual logic runs), an incorrect
navigation assumption here silently invalidates every assertion later in
that method — the method fails at setup, not at the behavior it's meant to
verify. Treat getting this step right as a prerequisite for the rest of the
test being meaningful, not a minor detail to fix later.
