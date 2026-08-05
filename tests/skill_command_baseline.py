"""Committed baseline for the skill-prose command ratchet in test_skill_command_ratchet.py.

WHAT IS COUNTED
---------------
COUNTS holds one entry per markdown file sitting directly inside a skill directory --
skills/<skill>/*.md. Every entry is present, including the zeros, because the guard compares this
set against the tree on every run and a discovered file with no entry is a failure rather than a
skip.

Subdirectories are out of scope: skills/generate-selenium-tests/references/ holds bundled
reference material, and skills/setup/scripts/ holds the executables that prose in this repo is
meant to be converted into. That leaves a subdirectory as an unguarded place to put command
prose. It is a known limit of the scope, not an oversight.

The counter, in test_skill_command_ratchet.py, works in four steps:

1. Collect every code span: each non-blank line inside a fenced code block, plus each
   backtick-delimited inline span in the prose around them.
2. Strip a leading "$ " or "> " prompt, then split on &&, ||, | and ; outside quotes, so a
   pipeline counts once per stage and appending one is not free.
3. Keep a segment only if it has two or more whitespace-separated tokens -- a lone word in
   backticks is a name, not an invocation -- and its first token is either a bare lowercase
   program name ([a-z][a-z0-9+-]*) or an explicit relative script path (./...).
4. A relative script path always counts. A bare name counts when LEXICON below marks it True.

The method is deterministic: it reads bytes and nothing else. No PATH lookup, no shell, no clock,
so the same file yields the same number on any machine.

LEXICON classifies every bare leading token the counter meets in this tree. It is checked against
the tree on every run too, and a token with no entry fails the suite. That is what keeps it from
rotting: a verb nobody anticipated cannot be silently counted as zero, it has to be classified
deliberately. True means the token names something a shell executes -- a program or a builtin, or
a git subcommand written without its "git" prefix. False means it merely looks like one: a Java
keyword from a code sample, a data-format sketch, or a fragment of an English sentence someone
wrapped in backticks. Entries for tokens no longer on disk are harmless; the printer drops them.

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
the substring. Such assertions are countable; an AST walk finds them. But the count is not
diagnostic, and that is the disqualifier. The sound form and the defective form are syntactically
identical: `token in text` is right when the token occurs once and the assertion is anchored to
that occurrence, and empty when four other occurrences satisfy it. A ratchet over a number that
cannot separate those would report a bar that is not being held -- worse than no number, because
it reads like one. What finds such an assertion is breaking the rule it names and watching whether
it notices, which is not a count and does not belong in a ratchet.

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
    "base64": True,
    "bash": True,
    "blob": False,  # `blob <len>\\0<bytes>`, a sketch of git's object header
    "curl": True,
    "git": True,
    "gradle": True,
    "package": False,  # Java keyword, from a generated-source sample
    "private": False,  # Java keyword, from a generated-source sample
}
