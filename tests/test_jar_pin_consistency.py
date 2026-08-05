"""IV-394 / family ADR 0011, Ruling 2: AC 3 requires the pinned jar value to live in exactly one
place. skills/setup/appian-selenium-api.jar.pin is that one place (read by
skills/setup/scripts/check-jar-integrity). SKILL.md's own deliberate restatement was removed by
IV-394 (it now only points at the pin file); build.gradle.template's header comment is kept
deliberately -- "at the point a Test-repo reader who may never see this skill's prose will actually
find it" -- so it, and the version number baked into SKILL.md's download URL, are the two remaining
copies this suite guards against drifting from the pin file.
"""

from __future__ import annotations

import re

import pytest

from conftest import JAR_PIN_FILE, SETUP_SKILL_DIR, read_pin_file

SKILL_MD = SETUP_SKILL_DIR / "SKILL.md"
BUILD_GRADLE_TEMPLATE = SETUP_SKILL_DIR / "build.gradle.template"

BUILD_GRADLE_PIN_RE = re.compile(
    r"Pinned:\s+(?P<version>\S+)\s+--\s+(?P<size>[\d,]+)\s+bytes,\s+sha256\s*\n\s*//\s*(?P<sha256>[0-9a-f]{64})",
)


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


class TestSkillProseNoLongerNamesAHashCommandOrFormat:
    """AC 2: the skill's prose no longer names any hash command or output format."""

    @pytest.fixture(scope="class")
    def skill_text(self) -> str:
        return SKILL_MD.read_text(encoding="utf-8")

    @pytest.mark.parametrize(
        "forbidden",
        ["sha256sum", "shasum", "certutil", "-hashfile"],
    )
    def test_no_hash_command_named(self, skill_text, forbidden):
        assert forbidden not in skill_text, (
            f"SKILL.md still names {forbidden!r} -- AC 2 requires the script to absorb this, not "
            "the prose to teach it"
        )

    def test_no_bare_pinned_sha256_literal_in_prose(self, skill_text, pin):
        """The raw hex digest itself is no longer restated in SKILL.md prose -- only the pin
        file's path is. (build.gradle.template's header comment is the one deliberate exception,
        per Ruling 2, and that file is covered by a separate test above.)"""
        assert pin["SHA256"] not in skill_text


class TestHardStopScopeCoversTheJavaSweep:
    """The deferred Minor from IV-387: the root-level .java sweep sits textually after the jar
    check inside step 4, and used to open with 'regardless of whether either check above found
    anything to do' -- which a model reading the hard-stop's own enumerated stop-list ('the build
    file below and steps 5-9') could read as still in scope after a hard stop, since the sweep is
    neither 'the build file' nor 'step 5-9'. IV-394 folds this in (ticket's agent notes: fix it in
    this round, prove the stop is total)."""

    @pytest.fixture(scope="class")
    def skill_text(self) -> str:
        return SKILL_MD.read_text(encoding="utf-8")

    def test_ambiguous_regardless_phrase_is_gone(self, skill_text):
        assert "regardless of whether either check above found anything to do" not in skill_text

    def test_java_sweep_opener_is_explicitly_gated_on_not_having_stopped(self, skill_text):
        assert "did not stop the run" in skill_text

    def test_pre_push_hard_stop_names_the_java_sweep(self, skill_text):
        pre_push_stop = skill_text.split("**On a nonzero exit, stop here", 1)[1].split("\n\n", 1)[0]
        assert ".java` sweep" in pre_push_stop

    def test_post_push_hard_stop_also_names_downstream_steps(self, skill_text):
        post_push_stop = skill_text.split("the push already happened but produced bad content", 1)[1]
        post_push_stop = post_push_stop.split("\n\n", 1)[0]
        assert ".java` sweep" in post_push_stop
        assert "steps 5-9" in post_push_stop
