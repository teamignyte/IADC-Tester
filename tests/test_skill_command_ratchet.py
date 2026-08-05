"""Ratchet guard: the executable commands written into skill prose may not grow (IV-401).

Family ADR 0011 (docs/adr/0011-scripts-replace-prose-once-a-check-clears-a-viability-test.md in
the umbrella repo) says a deterministic check ships as a script the skill invokes, not as prose
the model follows. Nothing mechanical held that. Command prose accumulates one sentence at a
time, each addition looks small next to the file it lands in, and no test notices. This module
counts the commands in each skill file and fails when a count leaves the committed baseline in
skill_command_baseline.py, in either direction.

The counting method is code and lives here. What the number means, what it deliberately does not
measure, and how to move it are documented in skill_command_baseline.py, beside the numbers.

**This is a mirror.** The authored copy is IADC-Advisor's tests/test_skill_command_ratchet.py;
this one is identical but for SKILLS_ROOT and this paragraph, and carries its own baseline. Fix
the authored copy first, then bring the change here.

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
_PROMPT = re.compile(r"^[$>]\s+")
# A bare program name: lowercase, no dots, no slashes, no underscores.
_NAME = re.compile(r"^[a-z][a-z0-9+-]*$")
# An explicit relative path to a script, which is an invocation whatever it is named.
_SCRIPT_PATH = re.compile(r"^\./[A-Za-z0-9_./+-]+$")
_SEPARATORS = ("&&", "||", "|", ";")


def code_spans(text: str) -> list[str]:
    """Every code span in `text`: one per fenced-block line, plus each inline backtick span."""
    spans: list[str] = []
    prose: list[str] = []
    open_fence: str | None = None
    for line in text.splitlines():
        match = _FENCE.match(line)
        if open_fence is None:
            if match:
                open_fence = match.group(1)
                continue
            prose.append(line)
            continue
        if match and match.group(1)[0] == open_fence[0] and len(match.group(1)) >= len(open_fence):
            open_fence = None
            continue
        if line.strip():
            spans.append(line.strip())
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
    """Every invocation-shaped segment in `text`, as (leading token, is an explicit script path).

    Invocation-shaped means: at least two whitespace-separated tokens -- a lone word in
    backticks is a name, not an invocation -- and a leading token that is either a bare
    lowercase program name or a ./ path. Whether a bare name is a command is the lexicon's
    call, not this function's.
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
            elif _NAME.match(head):
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
    assert on_disk - baselined == set(), (
        "skill files with no baseline entry: "
        f"{sorted(on_disk - baselined)}. Add each with its current count "
        "(python3 tests/test_skill_command_ratchet.py prints them)."
    )
    assert baselined - on_disk == set(), (
        "baseline entries for files no longer on disk: "
        f"{sorted(baselined - on_disk)}. Drop them in the commit that removed the files."
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
