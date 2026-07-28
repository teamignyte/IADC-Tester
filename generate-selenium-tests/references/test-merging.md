# Reconciling ticket requirements against an existing test file

When a feature's target is an existing file (per SKILL.md step 3), every
requirement from the ticket falls into exactly one of three categories.
Decide the category for each requirement individually — do not judge the
file as a whole as "needs updating" or "fine as is."

## Category 1: Already covered

The requirement is already verified by an existing assertion, field
population, or interaction step in the file, and nothing about it has
changed. Leave the corresponding code exactly as it is. Do not "clean up,"
rephrase, or restructure code that already correctly covers a requirement —
touching it introduces risk with no benefit.

## Category 2: New and non-conflicting

The requirement is not currently covered, and adding it does not require
removing or changing anything that's already there. Two ways to add it,
choose whichever fits:

- **Extend an existing `@Test` method** if the new requirement verifies the
  same underlying save/output that method already checks (e.g., the method
  already submits a form and checks several fields on the saved record, and
  the new requirement is one more field on that same record).
- **Add a new `@Test` method** if the new requirement verifies a genuinely
  distinct behavior or outcome — a different action, a different record, or
  a different save/output boundary than what any existing method covers.

When extending an existing method, add the new population/assertion lines
in the position consistent with the method's existing field order (e.g.,
alongside other field assertions, not appended awkwardly after cleanup
code).

## Category 3: Contradicting

The requirement conflicts with something the file currently asserts or
does — for example, a changed expected value, a field that's no longer
required, a renamed dropdown option, or a changed workflow step. Before
concluding something is a contradiction, confirm it actually conflicts
rather than merely being unrelated or additive; when genuinely uncertain
whether two things conflict, treat it as Category 2 (additive) rather than
replacing something on a guess.

Once confirmed as a real contradiction:

- Identify the smallest unit of code that embodies the outdated
  requirement — typically a single assertion, a single populate call, or a
  single expected-value constant. Do not replace the entire `@Test` method
  or the whole file.
- Replace only that unit with the version matching the new requirement.
  Everything else in the method and file — setup, unrelated assertions,
  other fields, cleanup — stays exactly as it was.
- If a changed value is used in multiple places (e.g., a constant used in
  both a populate call and a later assertion), update the single constant
  rather than hunting down and editing every usage site separately.

## After reconciling

Once every requirement has been placed into one of the three categories and
handled accordingly, re-read the whole file once more (per SKILL.md step 7)
to confirm the result is internally consistent — e.g., a replaced expected
value in a constant is not still referenced by its old literal value
somewhere else in the file, and no partially-applied edit was left behind.
