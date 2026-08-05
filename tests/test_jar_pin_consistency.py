"""IV-394 (family ADR 0011): the pinned jar value must live in exactly one place.
skills/setup/appian-selenium-api.jar.pin is that one place (read by
skills/setup/scripts/check-jar-integrity). SKILL.md's own restatement of it was removed; SKILL.md
now only points at the pin file. build.gradle.template's header comment keeps a deliberate
restatement -- "at the point a Test-repo reader who may never see this skill's prose will actually
find it" -- so it, and the version number baked into SKILL.md's download URL, are the two
deliberate copies this suite guards against drifting from the pin file. A separate test below
searches every tracked file for the digest itself, so a third, undeclared copy doesn't go
unnoticed the way one once did.
"""

from __future__ import annotations

import re
import subprocess

import pytest

from conftest import CHECK_JAR_INTEGRITY, JAR_PIN_FILE, REPO_ROOT, SETUP_SKILL_DIR, read_pin_file

SKILL_MD = SETUP_SKILL_DIR / "SKILL.md"
BUILD_GRADLE_TEMPLATE = SETUP_SKILL_DIR / "build.gradle.template"

BUILD_GRADLE_PIN_RE = re.compile(
    r"Pinned:\s+(?P<version>\S+)\s+--\s+(?P<size>[\d,]+)\s+bytes,\s+sha256\s*\n\s*//\s*(?P<sha256>[0-9a-f]{64})",
)

# The only files allowed to restate the pinned sha256 verbatim -- checked against by
# test_no_untracked_copy_of_the_pinned_sha256 below, which searches every tracked file for the
# digest itself rather than trusting this list alone.
KNOWN_PIN_SHA256_COPY_FILES = {JAR_PIN_FILE, BUILD_GRADLE_TEMPLATE}


@pytest.fixture(scope="module")
def pin() -> dict:
    values = read_pin_file(JAR_PIN_FILE)
    for required in ("VERSION", "SIZE", "SHA256"):
        assert required in values, f"{JAR_PIN_FILE} is missing {required}="
    return values


def test_pin_file_sha256_is_64_lowercase_hex_chars(pin):
    assert re.fullmatch(r"[0-9a-f]{64}", pin["SHA256"]), pin["SHA256"]


def test_pin_file_size_is_a_plain_integer(pin):
    assert pin["SIZE"].isdigit(), pin["SIZE"]


def test_check_jar_integrity_reads_this_exact_pin_file():
    """The path SKILL.md tells the model to invoke names this file, not a copy of it."""
    text = SKILL_MD.read_text(encoding="utf-8")
    assert "skills/setup/appian-selenium-api.jar.pin" in text


def test_download_url_version_matches_pin_file(pin):
    text = SKILL_MD.read_text(encoding="utf-8")
    assert pin["VERSION"] in text, (
        f"SKILL.md's download URL must contain the pinned version {pin['VERSION']!r} -- "
        "mutate the pin file's VERSION= and this test must go red"
    )


def test_build_gradle_template_header_matches_pin_file(pin):
    text = BUILD_GRADLE_TEMPLATE.read_text(encoding="utf-8")
    match = BUILD_GRADLE_PIN_RE.search(text)
    assert match, "build.gradle.template's header no longer states a 'Pinned: ... sha256' block"
    assert match.group("version") == pin["VERSION"]
    assert match.group("size").replace(",", "") == pin["SIZE"]
    assert match.group("sha256") == pin["SHA256"]


def test_build_gradle_template_url_version_matches_pin_file(pin):
    text = BUILD_GRADLE_TEMPLATE.read_text(encoding="utf-8")
    assert pin["VERSION"] in text


def _tracked_files() -> list:
    result = subprocess.run(
        ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    files = [REPO_ROOT / line for line in result.stdout.splitlines() if line]
    assert files, (
        f"git ls-files returned nothing under {REPO_ROOT} -- an empty result would otherwise make "
        "the digest scan below examine zero files and silently pass"
    )
    return files


def test_no_untracked_copy_of_the_pinned_sha256(pin):
    """Searches every tracked file for the pinned digest, rather than trusting that only the two
    files in KNOWN_PIN_SHA256_COPY_FILES ever restate it -- a new file added later that happens to
    quote the digest (documentation, a stray fixture, anything) is caught here instead of being
    silently exempt because nobody remembered to extend a hand-typed list of files to check."""
    digest = pin["SHA256"]
    known = {path.resolve() for path in KNOWN_PIN_SHA256_COPY_FILES}
    offenders = []
    for path in _tracked_files():
        if not path.is_file() or path.resolve() in known:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if digest in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, (
        f"pinned sha256 found outside the known copies: {offenders} -- add it to "
        "KNOWN_PIN_SHA256_COPY_FILES if it's meant to be a deliberate copy, otherwise it's drift"
    )


def _hash_tool_dispatch_tokens() -> list:
    """The identifiers SKILL.md's prose must not name, read from check-jar-integrity's own
    dispatch table rather than typed by hand here -- a tool added to the script's HASH_TOOLS array
    is automatically forbidden in prose too, instead of being silently exempt until someone
    remembers to extend a second, separately maintained list."""
    text = CHECK_JAR_INTEGRITY.read_text(encoding="utf-8")
    tools_match = re.search(r"^HASH_TOOLS=\(([^)]*)\)", text, re.MULTILINE)
    assert tools_match, f"{CHECK_JAR_INTEGRITY} has no HASH_TOOLS=(...) array to read"
    tokens = tools_match.group(1).split()
    assert tokens, f"{CHECK_JAR_INTEGRITY}'s HASH_TOOLS array is empty"
    # certutil's flag is specific enough to give the mechanism away even without naming the tool
    # itself, so it's forbidden alongside the tool names -- also read from the script, not typed.
    flags = re.findall(r"certutil\s+(-\w+)", text)
    return tokens + flags


class TestSkillProseNoLongerNamesAHashCommandOrFormat:
    """The skill's prose no longer names any hash command or output format -- the script absorbs
    that, so a model reading SKILL.md never has to choose among them or reconcile their output."""

    @pytest.fixture(scope="class")
    def skill_text(self) -> str:
        return SKILL_MD.read_text(encoding="utf-8")

    @pytest.mark.parametrize("forbidden", _hash_tool_dispatch_tokens())
    def test_no_hash_command_named(self, skill_text, forbidden):
        assert forbidden not in skill_text, (
            f"SKILL.md still names {forbidden!r} -- the script absorbs this now, the prose "
            "shouldn't teach it"
        )

    def test_no_bare_pinned_sha256_literal_in_prose(self, skill_text, pin):
        """The raw hex digest itself is no longer restated in SKILL.md prose -- only the pin
        file's path is. (build.gradle.template's header comment is the one deliberate exception,
        and that file is covered by a separate test above.)"""
        assert pin["SHA256"] not in skill_text


class TestHardStopScopeCoversTheJavaSweep:
    """The root-level .java sweep sits textually after the jar check inside step 4, and used to
    open with 'regardless of whether either check above found anything to do' -- which a model
    reading the hard-stop's own enumerated stop-list ('the build file below and steps 5-9') could
    read as still in scope after a hard stop, since the sweep is neither 'the build file' nor 'step
    5-9'. These tests prove the stop is total: the ambiguous phrase is gone, and the sweep opener
    is explicitly gated on the run not having already stopped."""

    @pytest.fixture(scope="class")
    def skill_text(self) -> str:
        return SKILL_MD.read_text(encoding="utf-8")

    def test_ambiguous_regardless_phrase_is_gone(self, skill_text):
        assert "regardless of whether either check above found anything to do" not in skill_text

    def test_java_sweep_opener_is_explicitly_gated_on_not_having_stopped(self, skill_text):
        """Anchored to the block that opens the .java sweep discussion (from the end of the
        build-file bullet to the next blank line), not the whole file -- this phrase surviving
        somewhere else in the file while the opener itself regresses to the old, unscoped wording
        must fail this test, not pass it."""
        after_build_file_bullet = skill_text.split(
            "guessed; changing them here would silently drop that guarantee.", 1
        )[1]
        sweep_section = after_build_file_bullet.split("\n\n", 2)[1]
        assert "did not stop the run" in sweep_section
        assert "regardless of whether either check above found anything to do" not in sweep_section

    def test_pre_push_hard_stop_names_the_java_sweep(self, skill_text):
        pre_push_stop = skill_text.split("**On a nonzero exit, stop here", 1)[1].split("\n\n", 1)[0]
        assert ".java` sweep" in pre_push_stop

    def test_post_push_hard_stop_also_names_downstream_steps(self, skill_text):
        post_push_stop = skill_text.split("the push already happened but produced bad content", 1)[1]
        post_push_stop = post_push_stop.split("\n\n", 1)[0]
        assert ".java` sweep" in post_push_stop
        assert "steps 5-9" in post_push_stop
