Edit these values in place (or re-run `/iadc-tester:setup`); this file is committed and shared with
the team. The one value that differs per machine — Harness path — lives separately, in
`docs/agents/tester.local.md` (gitignored).

**How to fill these in.** The data lines below carry **bare values** — every rule for choosing one
is stated here, above the data, and never as a trailing note on the line itself. None of these
fields has a deliberate "doesn't apply" answer — every one applies to every project this plugin
runs against, so a field with no real answer yet stays a placeholder rather than taking a stand-in
word like `none`.

- **Application UUID:** `<the Appian application these tests cover — the iadc graph seed target>`
- **Test repo:** `<the git repository holding the generated test files, e.g. your-org/your-repo>`
  - **Branch:** `<the branch in Test repo that generated files are pushed to>`
- **Test site URL:** `<the full URL used to sign in, e.g. https://your-tenant.appiancloud.com/suite>`
- **Site web address:** `<the site's internal web address, used for navigateToSite once signed in>`
- **Test username:** `<the Appian username these tests sign in as — must have a matching entry in users.properties>`
- **Site version:** `<the Appian site version under test>`
