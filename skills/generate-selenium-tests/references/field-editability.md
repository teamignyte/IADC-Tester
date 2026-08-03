# Guarding writes to potentially-read-only fields

Before writing to any field, check whether it is currently editable.

## This applies to every populated field individually — no exceptions

This is not a general guideline to keep in mind — it is a per-field
requirement. Every single `populateFieldWith` (or equivalent) call, for
every field, must individually go through the click-first and
editability-guard logic below. Do not write one shared helper (e.g. a
`populateXForm(...)` method) that calls `populateFieldWith` on a list of
fields uniformly, with the guard applied to only some of them, applied only
"where it seemed necessary," or omitted because most fields in that
particular form are expected to be freely editable. A field that is
expected to be editable is not exempt — the guard exists precisely because
that expectation can be wrong (e.g. a field pre-supplied by a related
action, which looks like any other field in the form but is actually
read-only). Treat every populate call as requiring this guard until proven
otherwise for that specific field, not until proven otherwise for the form
as a whole.

Before finalizing any generated test file, re-check every `populateFieldWith`
(or equivalent) call in it against this file. If any call lacks the
click-first step and an editability guard (fixture check, or the
try/catch-and-skip fallback), that is incomplete generation — add the
guard, do not leave it out because the field is assumed safe.

## Always click the field before populating it

Regardless of any other check in this file, every populate action on a text
field or dropdown must first click on that field, before attempting to call
the populate method on it. Some fields (particularly ones prefilled by a
related action) render in a static/read-only display state until clicked,
and only switch into their real interactive input after that click. A
field's read-only appearance or classification at the moment the test
reaches it is not reliable evidence that it is actually locked — clicking it
first is required to find out. Only treat a field as genuinely non-editable
if it is still read-only/disabled *after* this click, using the checks
below.

## Preferred: use a fixture-provided check

Confirm in the Javadoc (step 5 of SKILL.md) whether the fixture exposes a
method to check a field's editable/read-only state before writing to it
(e.g., an `isFieldEditable`/`isReadOnly`-style check, or a way to read a
field's current value without attempting to populate it). If such a method
exists, use it: check editability first, and only call the populate method if
the field is confirmed editable.

## Fallback: no editability check exists in the fixture

If the fixture has no such check method, verify editability implicitly
instead, using one of:

- Read the field's current value first and compare it to the intended value
  (if it's already correct — e.g., pre-filled by a related action — there may
  be nothing to write).
- Wrap the write in a try/catch for the specific read-only exception the
  fixture throws (e.g., `IllegalArgumentException` from a
  `TempoReadOnlyField`-style class) and treat that exception as "this field
  is not editable" rather than a test failure.

## Skip logic

If a field is confirmed (or inferred via the fallback) to be non-editable,
skip the write for that field rather than letting the test fail outright on
it. Log which fields were skipped and why — a skipped write may itself be
worth surfacing rather than silently ignoring.

## Exception: required-editable fields

Do not skip a write silently if the field being editable is itself required
by an acceptance criterion. In that case the test should still fail, just
with a clear message identifying that the required field was unexpectedly
non-editable, rather than an unrelated fixture exception bubbling up
uninterpreted.

## JUnit-specific note

Since generated tests are JUnit 5 test classes, a skipped-but-not-required
write should not itself cause the `@Test` method to fail — just log it and
continue populating the remaining fields. Only turn a skip into a failure
(via `fail(...)` or an unhandled exception) when it corresponds to the
required-editable-field exception case above.
