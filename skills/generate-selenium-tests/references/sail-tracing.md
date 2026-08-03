# Tracing SAIL source for field/column values and editability

For every field or column the test plans to assert against or write to, trace
what SAIL expression actually produces its displayed value — don't rely on the
field/component name alone.

## Determining the rendered value

- If a grid column's value is a direct reference to a record field (e.g.,
  `fv!row.field`), the raw stored value is what renders — safe to assert
  against the value you entered/expect.
- If a column or field applies a formatting function, concatenation,
  conditional (`a!match`, `if`, `choose`), or a lookup/mapping against a
  separate choices/labels list (e.g., `index()` into a `choiceLabels` array, a
  lookup dictionary, `a!richTextItem` with conditional styling), the rendered
  text may differ from the raw value or from the dropdown label used to
  select it. Trace the expression to determine the actual rendered string,
  and assert against that.
- The goal is confidence, not suspicion — if the SAIL trace confirms the
  rendered value matches the input label (as happens e.g. with grid columns
  that display the same choice-label text used in a dropdown), assert against
  that value directly. Do not weaken or hedge an assertion once the rendering
  has been verified from the SAIL source.
- Note any component whose displayed value depends on locale/user context
  (dates, numbers) and account for that in the assertion.

## Determining editability

For every field the test plans to write to, trace whether the SAIL source can
render that field as read-only, disabled, or otherwise non-editable under any
condition relevant to this test. Common causes:

- A value pre-supplied by a related action (e.g., a record-related action
  passing in a field value that the interface then renders as read-only).
- A conditional editability expression (`readOnly:`, `disabled:` tied to
  `a!match`/`if` on other field values or record state).
- A field that becomes read-only after initial save (edit vs. create mode).

Note which fields are conditionally or unconditionally non-editable so the
write-guard logic (see field-editability.md) can be applied to them.

## Determining whether a clickable trigger is a button or a link-styled action

This applies to every clickable trigger the test interacts with individually
— not a general awareness to keep in mind. For each one, trace the actual
SAIL component before writing the corresponding fixture call:

- **A genuine button** — `a!buttonWidget`, `a!buttonArrayLayout`, or similar
  — uses `clickOnButton`/`verifyButtonIsPresent`/`verifyButtonIsNotPresent`.
- **A link-styled action** — `a!dynamicLink`, a record type's related
  action, or a quick action — uses `clickOnAction`/`verifyActionIsPresent`
  or `clickOnRecordRelatedAction`, not a button method.

### Do not match on vocabulary — trace actual rendering

The component or function name containing a word that also appears in a
fixture method name (e.g. a SAIL component called `recordActionField` or
`recordActionItem`, versus a fixture method called `clickOnAction`) is not
evidence they correspond to each other. This kind of name overlap is
coincidental, not structural, and reasoning from it is a specific, known
failure mode — not just a general reminder to "be careful." What determines
the correct fixture method is what DOM element the component actually
renders as in the browser, which can differ from what its SAIL name alone
would suggest, and can be changed by parameters on that same component
(most commonly `style`).

**Confirmed instance:** an `a!recordActionField` with `style: "SIDEBAR_PRIMARY"`
renders as a literal button element in the DOM, even though the component's
name and underlying wiring reference a record "action." This specific
combination (`recordActionField` + `style: "SIDEBAR_PRIMARY"`, or any other
style value confirmed to render a button) must be treated as a button —
use `clickOnButton`/`verifyButtonIsPresent`, not `clickOnAction` — regardless
of the "action" vocabulary in the component or rule names.

When tracing a trigger and its SAIL component name shares vocabulary with a
fixture method name, treat that as a prompt to check the rendering more
carefully, not as confirmation. Checking the fixture's own Javadoc for
`clickOnAction`/`clickOnButton` does not resolve this — the Javadoc
describes how each method locates an element, not which SAIL components
render as which DOM element. That mapping has to come from the SAIL
component's actual parameters (like `style`) and, where necessary, from
directly inspecting what element type the interface renders (e.g. via
screenshot/DOM inspection), not from re-reading the same method
documentation repeatedly expecting a different answer.

Do not infer which one applies from the trigger's visible label, wording, or
apparent purpose. An action named "Add Rule," "Submit," "Save," or anything
that sounds like a typical button is not necessarily rendered as a SAIL
button — it may just as easily be a record-related action or a dynamic link
styled to look clickable. Likewise, do not assume every trigger in a given
interface uses the same mechanism just because one of them turned out to be
a button (or an action) — check each one on its own, since a single
interface can mix both kinds of triggers.

Calling a button-fixture method on a link-styled action (or vice versa) will
not find the element, since the underlying DOM/locator strategy differs
between the two — so getting this wrong produces a test that fails to even
locate the trigger, not merely a stylistic mismatch.

Before finalizing any test file, re-check every button/action fixture call
in it against the actual SAIL component it targets. If a call can't be
confirmed against the traced SAIL, don't guess based on the label — go back
and trace it.

## Structural/behavioral properties to check for

Beyond individual field rendering, inspect the SAIL for any structural or
behavioral property of the interface that could change how the test needs to
interact with it or verify results. This list is illustrative, not
exhaustive — look for anything with a similar effect:

- **Pagination/batch-size settings on grids** (e.g., `pageSize`, `batchSize`)
  — affects whether all rows are visible without additional navigation.
- **Conditional visibility** (`a!match`, `showWhen`/`hideWhen`-type logic) on
  fields, buttons, or sections — a field/button may only appear under certain
  conditions, affecting whether a test step needs to trigger that condition
  first.
- **Default sort order** on a grid — affects where a newly created/updated
  row will appear, if a test assumes a particular row position.
- **Client-side vs. server-side filtering/search** on a grid — affects
  whether a value must be searched for vs. scanned for directly.
- **Read-only, disabled, or required-field logic driven by other field
  values** — affects the order fields must be populated in.
- **Asynchronous refresh/reload behavior** (e.g., a grid that only updates
  after a manual refresh action) — affects whether a wait or explicit refresh
  step is needed before verification.

If you find any such property, note what it implies for how the test should
be written (e.g., "must page through the grid," "must sort or search rather
than assume position," "must click refresh before asserting"), and design the
test steps accordingly.

## Explicit existence behaviour

- A requirement stating a field, button, or component should or should
  not be present needs its own explicit existence assertion — this is
  distinct from a requirement that only describes populating or saving a
  value in a field, which does not need a separate existence check.
- When a requirement calls for verifying that no error/validation failure
  occurred, prefer a success-proxy check (e.g., confirming the dialog
  closed, a button is no longer present, or the record appears as
  expected) over a dedicated error-detection method, unless the Javadoc
  confirms that method reliably returns rather than hanging/failing when
  no error is actually present.