"""Ratchet guard: the executable commands written into skill prose may not grow (IV-401).

Family ADR 0011 (docs/adr/0011-scripts-replace-prose-once-a-check-clears-a-viability-test.md in
the umbrella repo) says a deterministic check ships as a script the skill invokes, not as prose
the model follows. Nothing mechanical held that. Command prose accumulates one sentence at a
time, each addition looks small next to the file it lands in, and no test notices. This module
counts the commands in each skill file and fails when a count leaves the committed baseline in
skill_command_baseline.py, in either direction.

The counting method is code and lives here. What the number means, what it deliberately does not
measure, and how to move it are documented in skill_command_baseline.py, beside the numbers.

**This is a mirror.** The authored copy is IADC-Advisor's tests/test_skill_command_ratchet.py.
The two copies differ in exactly three places -- SKILLS_ROOT, this paragraph, and the file named
in the go-red recipe below -- and each carries its own baseline. Fix the authored copy first,
then bring the change here.

To watch the ratchet go red: add the text `git status --short`, backticks included, anywhere in
skills/generate-selenium-tests/SKILL.md and run `python3 -m pytest tests -v`. The failure names
the file, the baseline and the new count. Remove it and the suite is green again.

Run `python3 tests/test_skill_command_ratchet.py` to print the counts and lexicon the working
tree yields, in the form the baseline stores them.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from skill_command_baseline import COUNTS, LEXICON

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = REPO_ROOT / "skills"

# A fence opens on three or more backticks or tildes and closes on a run of the same character
# at least as long, per CommonMark -- so a ``` block may quote a ~~~ line without ending.
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
# An inline span is a run of N backticks, content, then a run of exactly N backticks.
_INLINE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.DOTALL)
# A list marker, and how far its content is indented -- an indented code block nested in a list
# item is measured from the item's content column, not from column zero.
_LIST_ITEM = re.compile(r"^ *(?:[-*+]|\d+[.)]) +")
_PROMPT = re.compile(r"^[$>]\s+")
_SEPARATORS = ("&&", "||", "|", ";")

# --- The four head shapes the counter recognises. Anything else is not read as an invocation;
# --- skill_command_baseline.py's WHAT IS COUNTED states that boundary and what falls outside it.
#
# An explicit relative path to a script is an invocation whatever it is named, so it counts on
# sight. The other three go to the lexicon to be classified.
_SCRIPT_PATH = re.compile(r"^\./[A-Za-z0-9_./+-]+$")
# A bare program name: lowercase, no dots, no slashes, no underscores.
_NAME = re.compile(r"^[a-z][a-z0-9+-]*$")
# Any head carrying a path separator or an assignment: bin/jira, /usr/bin/grep, .venv/bin/python,
# scripts/audit-skill, VAR=value. These are house style in this family, not exotic forms.
_PATH_OR_ASSIGNMENT = re.compile(r"^\S*[/=]\S*$")
# A hyphen- or underscore-joined identifier, whatever its case: Get-Content, TEST_BROWSER.
_JOINED = re.compile(r"^[A-Za-z][A-Za-z0-9]*[-_][A-Za-z0-9_-]*$")


def join_continuations(lines: list[str]) -> list[str]:
    """Fold a block's backslash-continued lines into the single command they spell.

    Without this, `bash script.sh \\` and its argument line are two segments, the second headed
    by whatever the first argument happens to be -- one command counted twice, the second time
    under a head that means nothing.
    """
    spans: list[str] = []
    buffer = ""
    for line in lines:
        buffer = f"{buffer} {line}" if buffer else line
        if buffer.endswith("\\"):
            buffer = buffer[:-1].rstrip()
            continue
        spans.append(buffer)
        buffer = ""
    if buffer:
        spans.append(buffer)
    return spans


def code_spans(text: str) -> list[str]:
    """Every code span in `text`.

    Three kinds, matching the three ways markdown carries code: one span per non-blank line of a
    fenced block, one per non-blank line of an indented code block, and one per inline backtick
    span in the prose around them -- with backslash-continued lines folded back together. Text
    markdown renders as an ordinary paragraph is prose and is not read here, whatever it says --
    including a line indented under a list item, which CommonMark makes paragraph continuation
    rather than code.
    """
    spans: list[str] = []
    prose: list[str] = []
    block: list[str] = []
    open_fence: str | None = None
    list_content_indent = 0
    after_blank = True
    in_indented_block = False

    def close_block() -> None:
        if block:
            spans.extend(join_continuations(block))
            block.clear()

    for line in text.splitlines():
        fence = _FENCE.match(line)
        if open_fence is not None:
            if fence and fence.group(1)[0] == open_fence[0] and len(fence.group(1)) >= len(open_fence):
                open_fence = None
                close_block()
            elif line.strip():
                block.append(line.strip())
            else:
                close_block()
            continue
        if fence:
            close_block()
            open_fence = fence.group(1)
            after_blank = in_indented_block = False
            continue
        if not line.strip():
            close_block()
            prose.append(line)
            after_blank = True
            in_indented_block = False
            continue
        indent = len(line) - len(line.lstrip(" "))
        marker = _LIST_ITEM.match(line)
        if marker:
            list_content_indent = len(marker.group(0))
            in_indented_block = False
        elif indent == 0:
            list_content_indent = 0
            in_indented_block = False
        elif indent >= list_content_indent + 4 and (after_blank or in_indented_block):
            block.append(line.strip())
            after_blank = False
            in_indented_block = True
            continue
        else:
            in_indented_block = False
        close_block()
        prose.append(line)
        after_blank = False
    close_block()
    for _, span in _INLINE.findall("\n".join(prose)):
        if span.strip():
            spans.append(span.strip())
    return spans


def segments(span: str) -> list[str]:
    """Split one code span into command segments on &&, ||, | and ; outside quotes.

    A pipeline is more than one command, and counting it as one would let a stage be appended
    for free.
    """
    span = _PROMPT.sub("", span)
    parts: list[str] = []
    buffer = ""
    quote: str | None = None
    index = 0
    while index < len(span):
        char = span[index]
        if quote is not None:
            buffer += char
            if char == quote:
                quote = None
            index += 1
            continue
        if char in "'\"":
            quote = char
            buffer += char
            index += 1
            continue
        separator = next((s for s in _SEPARATORS if span.startswith(s, index)), None)
        if separator is not None:
            parts.append(buffer)
            buffer = ""
            index += len(separator)
            continue
        buffer += char
        index += 1
    parts.append(buffer)
    return [part.strip() for part in parts if part.strip()]


def invocations(text: str) -> list[tuple[str, bool]]:
    """Every invocation-shaped segment in `text`, as (leading token, counts without classifying).

    Invocation-shaped means: at least two whitespace-separated tokens -- a lone word in
    backticks is a name, not an invocation -- and a leading token matching one of the four
    recognised head shapes above. A ./ script path counts on sight; every other recognised head
    is handed to the lexicon, so it is classified rather than dropped. Whether it is a command
    is the lexicon's call, not this function's.
    """
    found: list[tuple[str, bool]] = []
    for span in code_spans(text):
        for segment in segments(span):
            tokens = segment.split()
            if len(tokens) < 2:
                continue
            head = tokens[0]
            if _SCRIPT_PATH.match(head):
                found.append((head, True))
            elif _NAME.match(head) or _PATH_OR_ASSIGNMENT.match(head) or _JOINED.match(head):
                found.append((head, False))
    return found


def unclassified_tokens(text: str, lexicon: dict[str, bool]) -> set[str]:
    """Leading tokens in `text` that the lexicon does not classify either way."""
    return {head for head, is_path in invocations(text) if not is_path and head not in lexicon}


def count_commands(text: str, lexicon: dict[str, bool]) -> int:
    """How many executable commands `text` writes out. Every token must be classified first."""
    missing = unclassified_tokens(text, lexicon)
    if missing:
        raise KeyError(f"unclassified leading tokens: {sorted(missing)}")
    return sum(1 for head, is_path in invocations(text) if is_path or lexicon[head])


def discover_skill_files(skills_root: Path, base: Path) -> list[str]:
    """Every markdown file directly inside a skill directory, as a sorted path relative to `base`.

    Derived from disk on every run, never enumerated, so a skill added tomorrow is discovered
    rather than exempt.
    """
    found = [
        path
        for skill_dir in skills_root.iterdir()
        if skill_dir.is_dir()
        for path in skill_dir.glob("*.md")
        if path.is_file()
    ]
    return sorted(p.relative_to(base).as_posix() for p in found)


def _skill_files() -> list[str]:
    return discover_skill_files(SKILLS_ROOT, REPO_ROOT)


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


# --- The guard, against the real tree ----------------------------------------------------


def test_baseline_covers_exactly_the_skill_files_on_disk() -> None:
    """A new skill file is a failure until it is baselined, never a silent skip."""
    on_disk = set(_skill_files())
    baselined = set(COUNTS)
    assert on_disk, (
        f"discovery found no skill files under {SKILLS_ROOT}. A guard that reads nothing reads "
        "green: SKILLS_ROOT is wrong, or the skills tree moved. Repoint it -- do not empty the "
        "baseline to match."
    )
    assert on_disk - baselined == set(), (
        "skill files with no baseline entry: "
        f"{sorted(on_disk - baselined)}. Add each with its current count "
        "(python3 tests/test_skill_command_ratchet.py prints them)."
    )
    assert baselined - on_disk == set(), (
        "baseline entries with no file on disk: "
        f"{sorted(baselined - on_disk)}. If the skill really was deleted, drop its entry in that "
        "same commit; if it moved, fix the path here rather than removing the entry, so the file "
        "keeps its history instead of re-entering at whatever count it has drifted to."
    )


def test_every_leading_token_on_disk_is_classified() -> None:
    """An unknown verb stops the suite instead of being counted as zero."""
    unknown: dict[str, str] = {}
    for relative_path in _skill_files():
        for token in sorted(unclassified_tokens(_read(relative_path), LEXICON)):
            unknown.setdefault(token, relative_path)
    assert unknown == {}, (
        "leading tokens with no LEXICON entry: "
        f"{sorted(f'{t} (first in {f})' for t, f in unknown.items())}. "
        "Classify each as True (an executable command) or False (a word that merely looks like "
        "one) in skill_command_baseline.py."
    )


@pytest.mark.parametrize("relative_path", sorted(COUNTS))
def test_command_count_matches_baseline(relative_path: str) -> None:
    """Exact equality, both directions: growth is the thing guarded, and a drop that does not
    lower the baseline would leave headroom for the growth to come back."""
    actual = count_commands(_read(relative_path), LEXICON)
    baseline = COUNTS[relative_path]
    if actual > baseline:
        pytest.fail(
            f"{relative_path} writes out {actual} commands, up from the baseline {baseline}. "
            "Invoke a script instead, or -- if the prose is genuinely irreducible -- raise the "
            "baseline in this commit and say in the message why the command cannot be a script."
        )
    if actual < baseline:
        pytest.fail(
            f"{relative_path} writes out {actual} commands, down from the baseline {baseline}. "
            "Lower the baseline to "
            f"{actual} in this same commit so the bar stays where the conversion put it."
        )


# --- The counter itself, against fixtures ------------------------------------------------
#
# Each of these builds text that violates or exercises exactly one rule of the method, so the
# rule is pinned rather than assumed from the real tree's current numbers.


def test_a_lone_word_in_backticks_is_not_an_invocation() -> None:
    assert invocations("Set it to `appian` or `none`.") == []
    assert count_commands("Set it to `appian` or `none`.", {}) == 0


def test_a_command_with_an_argument_is_an_invocation() -> None:
    assert invocations("Run `git status --short` first.") == [("git", False)]


def test_a_pipeline_counts_once_per_stage() -> None:
    text = "Run `git ls-files -v .gitignore 2>/dev/null | grep -q '^H '`."
    assert [head for head, _ in invocations(text)] == ["git", "grep"]
    assert count_commands(text, {"git": True, "grep": True}) == 2


def test_a_separator_inside_quotes_does_not_split() -> None:
    assert [head for head, _ in invocations("Run `grep -E 'a|b' file`.")] == ["grep"]


def test_fenced_block_lines_each_count() -> None:
    text = "Run this:\n\n```bash\ngit add -A\ngit commit -m x\n\n```\n"
    assert [head for head, _ in invocations(text)] == ["git", "git"]


def test_a_longer_fence_does_not_close_on_a_quoted_shorter_one() -> None:
    text = "````\ngit add -A\n```\ngit commit -m x\n````\n"
    assert [head for head, _ in invocations(text)] == ["git", "git"]


def test_a_shell_prompt_is_stripped_before_the_leading_token() -> None:
    assert [head for head, _ in invocations("`$ git add -A`")] == ["git"]


def test_a_relative_script_path_counts_without_a_lexicon_entry() -> None:
    text = "Run `./skills/setup/scripts/check-jar-integrity lib/appian/x.jar`."
    assert invocations(text) == [("./skills/setup/scripts/check-jar-integrity", True)]
    assert count_commands(text, {}) == 1


def test_a_head_carrying_a_path_reaches_the_lexicon_rather_than_being_dropped() -> None:
    """The four path forms this family actually writes. None may be discarded unseen."""
    for span, head in (
        ("bin/jira view IV-401", "bin/jira"),
        ("/usr/bin/grep -n 'x' file", "/usr/bin/grep"),
        (".venv/bin/python -m tools.audit --all", ".venv/bin/python"),
        ("scripts/audit-skill --all", "scripts/audit-skill"),
    ):
        text = f"Run `{span}` next."
        assert invocations(text) == [(head, False)], span
        assert unclassified_tokens(text, {}) == {head}, span
        assert count_commands(text, {head: True}) == 1, span


def test_an_assignment_head_reaches_the_lexicon_rather_than_being_dropped() -> None:
    text = "Set `DOC_PATH=$(jq -r '.x' /tmp/f.json)` first."
    assert invocations(text) == [("DOC_PATH=$(jq", False)]
    assert unclassified_tokens(text, {}) == {"DOC_PATH=$(jq"}


def test_a_hyphen_joined_head_reaches_the_lexicon_rather_than_being_dropped() -> None:
    text = "Run `Get-Content x.txt` on Windows."
    assert invocations(text) == [("Get-Content", False)]
    assert unclassified_tokens(text, {}) == {"Get-Content"}


def test_a_punctuation_led_or_plain_capitalised_head_is_not_an_invocation() -> None:
    """The boundary the baseline documents: these shapes are not read as commands at all."""
    for span in ("# a comment", "-- flag fragment", "<placeholder> value", "Test site URL"):
        assert invocations(f"See `{span}` above.") == [], span


def test_a_backslash_continued_command_counts_once_not_once_per_line() -> None:
    text = '```\nbash check.sh \\\n  /tmp/x.jar "${ROOT}/x.pin"\n```\n'
    assert code_spans(text) == ['bash check.sh /tmp/x.jar "${ROOT}/x.pin"']
    assert [head for head, _ in invocations(text)] == ["bash"]


def test_an_indented_code_block_counts() -> None:
    text = "Run this:\n\n    git add -A\n    git commit -m x\n"
    assert [head for head, _ in invocations(text)] == ["git", "git"]


def test_an_indented_block_inside_a_list_item_counts_from_the_item_s_own_column() -> None:
    text = "- Do the thing:\n\n      git add -A\n"
    assert [head for head, _ in invocations(text)] == ["git"]


def test_a_line_indented_under_a_list_item_is_paragraph_text_not_code() -> None:
    """CommonMark makes this a continuation paragraph, not a code block, and so does the counter.

    Verified against markdown-it's commonmark preset: the four-space form below renders as
    <p>, the six-space form above as <pre><code>. A command written as running prose has never
    been counted, at any indentation; the baseline records that boundary.
    """
    text = "- Do the thing.\n\n    git add -A\n"
    assert invocations(text) == []


def test_a_word_classified_false_is_not_counted() -> None:
    text = "Declare `package autogen;` at the top."
    assert count_commands(text, {"package": False}) == 0


def test_an_unclassified_token_is_reported_rather_than_counted_as_zero() -> None:
    text = "Run `docker compose up -d`."
    assert unclassified_tokens(text, {"git": True}) == {"docker"}
    with pytest.raises(KeyError):
        count_commands(text, {"git": True})


def test_discovery_reads_the_tree_and_skips_subdirectories(tmp_path: Path) -> None:
    skills = tmp_path / "plugin" / "skills"
    (skills / "one" / "references").mkdir(parents=True)
    (skills / "one" / "SKILL.md").write_text("x", encoding="utf-8")
    (skills / "one" / "companion.md").write_text("x", encoding="utf-8")
    (skills / "one" / "references" / "bundled.md").write_text("x", encoding="utf-8")
    (skills / "one" / "notes.txt").write_text("x", encoding="utf-8")
    (skills / "two").mkdir()
    (skills / "two" / "SKILL.md").write_text("x", encoding="utf-8")
    assert discover_skill_files(skills, tmp_path) == [
        "plugin/skills/one/SKILL.md",
        "plugin/skills/one/companion.md",
        "plugin/skills/two/SKILL.md",
    ]


if __name__ == "__main__":  # pragma: no cover - a maintainer's printer, not part of the suite
    files = _skill_files()
    unknown = sorted({t for p in files for t in unclassified_tokens(_read(p), LEXICON)})
    if unknown:
        print("# Classify these in LEXICON first -- the counts below treat them as not-commands:")
        for token in unknown:
            print(f'#     "{token}": ...,')
    print("COUNTS = {")
    for path in files:
        counted = [h for h, is_path in invocations(_read(path)) if is_path or LEXICON.get(h)]
        print(f'    "{path}": {len(counted)},')
    print("}")
    stale = sorted(set(LEXICON) - {h for p in files for h, _ in invocations(_read(p))})
    if stale:
        print(f"# LEXICON entries no longer present in the tree, safe to drop: {stale}")
