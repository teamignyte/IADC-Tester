"""Committed baseline for the skill-prose command ratchet in test_skill_command_ratchet.py.

WHAT IS COUNTED
---------------
COUNTS holds one entry per markdown file sitting directly inside a skill directory --
skills/<skill>/*.md. Every entry is present, including the zeros, because the guard compares this
set against the tree on every run and a discovered file with no entry is a failure rather than a
skip.

The counter, in test_skill_command_ratchet.py, works in four steps:

1. Collect every code span. Three kinds, matching the three ways markdown carries code: one span
   per non-blank line of a fenced block, one per non-blank line of an indented code block, and
   one per backtick-delimited inline span in the prose around them. Backslash-continued lines
   are folded back into the one command they spell, so the argument line of a wrapped invocation
   is not a second command headed by its first argument.
2. Strip a leading "$ " or "> " prompt, then split on &&, ||, | and ; outside quotes, so a
   pipeline counts once per stage and appending one is not free.
3. Keep a segment only if it has two or more whitespace-separated tokens -- a lone word in
   backticks is a name, not an invocation -- and its first token matches one of four recognised
   head shapes: an explicit relative script path (./...); a bare lowercase program name
   ([a-z][a-z0-9+-]*); any token carrying a path separator or an assignment (bin/jira,
   /usr/bin/grep, .venv/bin/python, VAR=value); or a hyphen- or underscore-joined identifier of
   any case (Get-Content, TEST_BROWSER).
4. A relative script path counts on sight. Every other recognised head goes to LEXICON, which
   decides. Nothing recognised is discarded without one or the other happening to it.

The method is deterministic: it reads bytes and nothing else. No PATH lookup, no shell, no clock,
so the same file yields the same number on any machine.

LEXICON classifies every head the counter meets in this tree that is not a ./ path. It is checked
against the tree on every run, and a head with no entry fails the suite. That is what keeps it
from rotting: a verb nobody anticipated cannot be silently counted as zero, it has to be
classified deliberately. True means the token names something a shell executes -- a program, a
builtin, a shell assignment, or a git subcommand written without its "git" prefix. False means it
merely looks like one: a Java keyword from a code sample, a configuration constant, a data-format
sketch, or a fragment of an English sentence someone wrapped in backticks. Entries for tokens no
longer on disk are harmless; the printer drops them.

A slash-command skill invocation such as `/iadc-graph:setup` is not a shell command, and
delegating to a skill is the move family ADR 0011 asks for rather than the one it discourages, so
where one appears with arguments it is classified False -- counting it would put a cost on the
right answer.

WHAT IS OUT OF SCOPE, ALL OF IT DELIBERATE
------------------------------------------
Four boundaries. Each is a place command prose could be put without moving a number, and each is
named here rather than left to be discovered:

- **Subdirectories.** skills/generate-selenium-tests/references/ holds bundled reference
  material, and skills/setup/scripts/ holds the executables that prose here is meant to become.
- **Files that are not .md.** A skill directory also holds build templates and the jar pin
  (build.gradle.template, settings.gradle.template, appian-selenium-api.jar.pin). Those are data,
  not prose a model reads as instructions, so they are not counted -- but a .txt full of commands
  beside a SKILL.md would not be seen either.
- **Commands written as running prose.** The counter reads code spans. A command in an ordinary
  sentence with no backticks around it has never been counted, at any indentation. This includes
  a line indented under a list item, which CommonMark renders as continuation text rather than as
  a code block; only a line indented four columns past its list item's own content column is code.
- **Head shapes outside the four above.** A head led by punctuation (`#`, `--flag`, `<x>`) or a
  plain capitalised word with no separator in it (`Test site URL`) is not read as an invocation at
  all. Neither form appears as a real command anywhere in this tree today, and admitting them
  would pull in table cells and placeholder text that are not commands.

WHAT THE NUMBER MEANS, AND WHAT IT DOES NOT
-------------------------------------------
It is a proxy, and it should be read as one. It counts commands, not judgment, so it is wrong in
both directions. Prose walking a model through a decision no subprocess can make -- asking a
person for consent, reading an answer back -- counts exactly the same as prose reimplementing a
script that already exists, and family ADR 0011 says those two are not alike at all. A file can
also carry a great deal of untestable procedural prose and score zero, because none of it is
written as a command. A count that rises is a reason to read the diff, not a verdict on it; a
count that stays flat is not a certificate.

What the ratchet does buy is that the number cannot move without someone editing this file, in the
same commit, in view of a reviewer.

ONE AXIS, DELIBERATELY
----------------------
Command density is the only thing counted here. A second axis was weighed and left out: counting
whole-file substring assertions in the test suite -- `literal in path.read_text()` -- which stay
green while the specific rule they name is broken, because some other line in the file satisfies
the substring. Such assertions are countable; an AST walk finds them. What disqualifies them is
direction, and direction is the whole of what a ratchet reads.

Command density moves with the thing being guarded: command prose grows, the number grows. A
substring-assertion count would move with unrelated test growth and unrelated test deletion, so a
rise could mean the suite got weaker or that somebody added forty sound assertions, and a fall
could mean the assertions were repaired or that a module was deleted. The sound form and the
defective form are also syntactically identical -- `token in text` is right when the token occurs
once and the assertion is anchored to that occurrence, and empty when four other occurrences
satisfy it -- so no threshold separates them either. A ratchet over such a number would report a
bar that is not being held, which is worse than no number, because it reads like one.

What finds such an assertion is breaking the rule it names and watching whether it notices. That
is not a count and does not belong in a ratchet.

UPDATING
--------
`python3 tests/test_skill_command_ratchet.py` prints COUNTS as the working tree yields it, in the
form below, and names any token still needing a LEXICON entry and any entry that has gone stale.
A count that moved in either direction fails:

- Up: command prose grew. Invoke a script instead. If the prose really is irreducible under family
  ADR 0011's five conditions, raise the number here in the same commit and say in the message which
  condition it fails.
- Down: a conversion landed. Lower the number here in the same commit, so the bar stays where the
  conversion put it instead of leaving headroom for the prose to come back.
"""
from __future__ import annotations

COUNTS: dict[str, int] = {
    "skills/generate-selenium-tests/SKILL.md": 0,
    "skills/setup/SKILL.md": 11,
    "skills/setup/tester-config-template.md": 0,
    "skills/setup/tester-local-config-template.md": 0,
}

LEXICON: dict[str, bool] = {
    "TEST_BROWSER": False,  # a fixed test-harness constant, named in prose
    "TEST_SITE_LOCALE": False,  # a fixed test-harness constant, named in prose
    "TEST_TIMEOUT": False,  # a fixed test-harness constant, named in prose
    "base64": True,
    "bash": True,
    "blob": False,  # `blob <len>\\0<bytes>`, a sketch of git's object header
    "curl": True,
    "git": True,
    "gradle": True,
    "package": False,  # Java keyword, from a generated-source sample
    "private": False,  # Java keyword, from a generated-source sample
}
