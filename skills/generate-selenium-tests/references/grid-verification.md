# Verifying grid/list results without assuming an empty or known starting state

Never assume any list, grid, or other collection the test interacts with
starts empty or at a known count, even if this appears true at the time of
writing. Treat every such collection as potentially already populated by
real or prior test data (including leftover rows from earlier failed test
runs).

## Do not verify by count

Do not verify that a create/update action worked by checking that a grid or
list's row/item count changed. Counts are not a reliable signal of
existence, since:

- The collection may already contain an unknown and changing number of items
  from real or prior test data.
- Many Appian grids are paginated — the rendered row count reflects only the
  current page size (e.g., 10 rows shown out of 90+ total records), not the
  total dataset. A rendered-row-count check is not a reliable stand-in for a
  total-record-count check unless the fixture is confirmed via Javadoc to
  page through all data internally.

## Instead, locate the exact record

Locate the specific created/updated record directly, by searching,
filtering, or scanning for the exact value(s) that uniquely identify it
(e.g., the exact name or other distinguishing field value used when creating
it), and verify that record's fields match what's expected.

Account for pagination when doing so:

- If the fixture exposes a search or filter method, prefer that over
  scanning pages manually.
- If no search/filter method exists, page through results (using whatever
  "next page" method the fixture provides) until the record is found, or
  until all pages have been checked.
- Do not assume the record appears on the currently-rendered page, the first
  page, or the last page, unless the interface's SAIL trace confirms a sort
  order that guarantees this (see sail-tracing.md's "default sort order"
  point).

## Always navigate/refresh fresh before scanning a grid

Grids reset to page 1 on a fresh page load. So before scanning any grid for
a record, re-navigate to that page fresh (the same navigation steps used to
reach it originally — e.g. site navigation, record click, etc.) rather than
scanning whatever page a grid happens to already be on. This guarantees the
scan starts from page 1 without needing any "reset to first page" logic —
do not write reset loops (repeated "previous" or "first" clicks) at all.

## Page-through-scanning loops need a hard iteration cap

Any loop that pages forward through a grid (via repeated "next" calls)
while searching for a record must have an explicit, hard-coded maximum
iteration count (e.g., a named constant such as `MAX_PAGES_TO_SCAN`), not
just an exception-based exit condition. If the loop reaches its cap without
finding the record, fail with a clear message (e.g., "Did not find a
matching row after scanning N pages") rather than silently stopping. Pick
the cap generously enough for realistic data volumes, but always finite.

## JUnit-specific note

Since a search/page-through loop may take multiple iterations, keep this
logic inside the `@Test` method itself (not spread across multiple test
methods) so the whole find-and-verify sequence is one atomic, independently
re-runnable test case.
