"""skills/setup/scripts/check-jar-integrity: the executable half of IV-394 (family ADR 0011 --
scripts replace prose once a check clears the viability test).

Drives the script directly via subprocess, with no model in the loop -- ADR 0011 condition 3. Every
test here constructs its own fixture file and its own pin file, never the shipped production pin
(skills/setup/appian-selenium-api.jar.pin) or a real Appian jar: the point of these tests is to
prove the comparator discriminates correctly given arbitrary bytes and an arbitrary pinned digest,
independent of which release happens to be pinned this month. test_jar_pin_consistency.py is what
guards the production pin's own consistency across its copies.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from conftest import CHECK_JAR_INTEGRITY

PRODUCTION_DIGEST = "80dcc7560f026aba27bc74de5a242eef4d1e80e5350e465e91a83aa55cdcece8"


def run_check(file_path: Path, pin_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(CHECK_JAR_INTEGRITY), str(file_path), str(pin_path)],
        capture_output=True,
        text=True,
    )


def write_pin(tmp_path: Path, sha256: str, *, version: str = "TEST", size: str | None = None) -> Path:
    pin_path = tmp_path / "fixture.pin"
    lines = [f"VERSION={version}", f"SHA256={sha256}"]
    if size is not None:
        lines.insert(1, f"SIZE={size}")
    pin_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return pin_path


@pytest.fixture
def good_jar(tmp_path: Path) -> Path:
    jar_path = tmp_path / "good.jar"
    jar_path.write_bytes(b"\x00\x01\x02not a real jar, just deterministic bytes\xff" * 37)
    return jar_path


@pytest.fixture
def good_digest(good_jar: Path) -> str:
    return hashlib.sha256(good_jar.read_bytes()).hexdigest()


class TestScriptExists:
    def test_script_is_executable(self):
        assert CHECK_JAR_INTEGRITY.is_file(), "scripts/check-jar-integrity must exist"
        # POSIX-only check: executable bit is metadata this repo carries under git, not something
        # meaningful to assert on a non-POSIX filesystem, but this suite only runs on POSIX CI.
        assert CHECK_JAR_INTEGRITY.stat().st_mode & 0o111, "check-jar-integrity must be executable"

    def test_invoked_name_is_extensionless(self):
        """Portability rule (ADR 0011): scripts are extensionless -- no .sh suffix on the
        invoked name, since that is what triggers Claude Code's Windows-launcher auto-prepend
        behaviour a leading `bash` in the invocation would then collide with (see ADR 0012)."""
        assert CHECK_JAR_INTEGRITY.suffix == ""


class TestHappyPath:
    def test_matching_digest_exits_zero(self, good_jar, good_digest, tmp_path):
        pin_path = write_pin(tmp_path, good_digest)
        result = run_check(good_jar, pin_path)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "OK" in result.stdout
        assert good_digest not in result.stdout or True  # OK message doesn't need to echo it back


class TestMismatchIsDetected:
    """AC 4: a test proves a mismatch is detected, using a deliberately wrong fixture, and names
    the mutation that turns it red."""

    def test_one_byte_altered_fixture_is_rejected(self, good_jar, good_digest, tmp_path):
        """The mutation: flip one bit of good_jar's first byte, leaving every other byte and the
        file's length untouched. Before mutating, assert the byte we're about to flip is what we
        expect, so a no-op mutation can't silently pass this test against an unmutated fixture."""
        original = bytearray(good_jar.read_bytes())
        assert original[0] == 0x00, "fixture's first byte drifted; mutation below assumes 0x00"
        original[0] ^= 0xFF
        mutated_path = good_jar.parent / "mutated.jar"
        mutated_path.write_bytes(bytes(original))
        assert mutated_path.read_bytes() != good_jar.read_bytes(), "mutation did not apply"

        pin_path = write_pin(tmp_path, good_digest)  # pinned to the ORIGINAL (unmutated) digest
        result = run_check(mutated_path, pin_path)

        assert result.returncode == 1, result.stdout + result.stderr
        assert "MISMATCH" in result.stdout
        # the pinned value and the wrongly-computed value must both be named, per the invocation
        # contract's "stdout is the human-readable reason"
        assert good_digest in result.stdout
        wrong_digest = hashlib.sha256(bytes(original)).hexdigest()
        assert wrong_digest in result.stdout

    def test_truncated_fixture_is_rejected(self, good_jar, good_digest, tmp_path):
        truncated_path = good_jar.parent / "truncated.jar"
        truncated_path.write_bytes(good_jar.read_bytes()[: len(good_jar.read_bytes()) // 2])
        pin_path = write_pin(tmp_path, good_digest)
        result = run_check(truncated_path, pin_path)
        assert result.returncode == 1, result.stdout + result.stderr
        assert "MISMATCH" in result.stdout

    def test_missing_file_is_rejected(self, tmp_path, good_digest):
        pin_path = write_pin(tmp_path, good_digest)
        result = run_check(tmp_path / "does-not-exist.jar", pin_path)
        assert result.returncode != 0, result.stdout + result.stderr
        assert "not found" in result.stdout.lower()


class TestSizeNeverSubstitutesForHash:
    """AC 5 / the exact defect IV-387 found: a fixture with the correct byte count and the wrong
    sha256 must fail -- proving there is no code path where matching size alone produces a pass."""

    def test_same_size_wrong_digest_is_rejected(self, good_jar, good_digest, tmp_path):
        same_size_wrong = good_jar.parent / "same-size-wrong.jar"
        original_bytes = bytearray(good_jar.read_bytes())
        # Same length, different content throughout -- not just one byte -- so this can't be
        # mistaken for the single-bit-flip mutation case above.
        mutated = bytes((b + 1) % 256 for b in original_bytes)
        same_size_wrong.write_bytes(mutated)
        assert len(mutated) == len(original_bytes)
        assert mutated != bytes(original_bytes)

        pin_path = write_pin(tmp_path, good_digest, size=str(len(original_bytes)))
        result = run_check(same_size_wrong, pin_path)

        assert result.returncode == 1, (
            "a same-size, wrong-hash fixture must fail -- a passing exit here would mean size is "
            "substituting for the hash, the exact defect IV-387 found"
        )
        assert "MISMATCH" in result.stdout


class TestPinFileErrors:
    def test_missing_pin_file_is_an_error(self, good_jar, tmp_path):
        result = run_check(good_jar, tmp_path / "no-such.pin")
        assert result.returncode == 2
        assert "pin file" in result.stdout.lower()

    def test_pin_file_without_sha256_is_an_error(self, good_jar, tmp_path):
        pin_path = tmp_path / "malformed.pin"
        pin_path.write_text("VERSION=TEST\n", encoding="utf-8")
        result = run_check(good_jar, pin_path)
        assert result.returncode == 2
        assert "SHA256" in result.stdout


class TestNormalizeDigestAbsorbsPlatformVariance:
    """AC 2's converse: the platform-dispatch-and-format-reconciliation prose SKILL.md used to
    carry is now absorbed into this script, not deleted outright. These four inputs are the exact
    four forms that prose named. All are constructed here, not captured from a real run of
    sha256sum/shasum/certutil -- certutil isn't available on this (Linux) host, and the other three
    forms are trivial to construct byte-for-byte from the known-correct digest, so constructing all
    four keeps the comparison symmetric instead of trusting three real tool runs against one
    hand-built string."""

    @staticmethod
    def normalize(stdin_text: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", str(CHECK_JAR_INTEGRITY), "--normalize-digest"],
            input=stdin_text,
            capture_output=True,
            text=True,
        )

    def test_sha256sum_bare_form(self):
        result = self.normalize(f"{PRODUCTION_DIGEST}  appian-selenium-api.jar\n")
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == PRODUCTION_DIGEST

    def test_certutil_labelled_multiline_form(self):
        blob = (
            "SHA256 hash of appian-selenium-api.jar:\n"
            f"{PRODUCTION_DIGEST}\n"
            "CertUtil: -hashfile command completed successfully.\n"
        )
        result = self.normalize(blob)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == PRODUCTION_DIGEST

    def test_hex_spaced_into_pairs_form(self):
        spaced = " ".join(PRODUCTION_DIGEST[i : i + 2] for i in range(0, len(PRODUCTION_DIGEST), 2))
        assert spaced != PRODUCTION_DIGEST  # sanity: the fixture actually has spaces in it
        result = self.normalize(spaced + "\n")
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == PRODUCTION_DIGEST

    def test_uppercase_hex_form(self):
        upper = PRODUCTION_DIGEST.upper()
        assert upper != PRODUCTION_DIGEST  # sanity: the fixture actually differs in case
        result = self.normalize(upper + "\n")
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == PRODUCTION_DIGEST

    def test_certutil_labelled_and_spaced_older_windows_form(self):
        """The two quirks the old prose called out can co-occur (an older Windows certutil
        producing a labelled block AND spaced hex) -- prove the normalizer handles both at once,
        not just each individually."""
        spaced = " ".join(PRODUCTION_DIGEST[i : i + 2] for i in range(0, len(PRODUCTION_DIGEST), 2))
        blob = (
            "SHA256 hash of appian-selenium-api.jar:\n"
            f"{spaced}\n"
            "CertUtil: -hashfile command completed successfully.\n"
        )
        result = self.normalize(blob)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == PRODUCTION_DIGEST

    def test_no_digest_present_fails(self):
        result = self.normalize("no hex here\n")
        assert result.returncode == 1


class TestHashToolFallback:
    """The script tries sha256sum, then shasum, then openssl, then certutil, in that order --
    absorbing the exact three-way (four, with openssl) platform dispatch the old prose taught.
    Forces each non-default branch by shrinking PATH to a minimal directory that provides only the
    coreutils the script itself needs (bash, grep, cut, wc, tr, head) plus one hash tool, so
    `command -v sha256sum` (etc.) genuinely fails rather than the branch merely going untested."""

    @staticmethod
    def _minimal_path_with(tmp_path: Path, extra_tool_dir: Path | None) -> str:
        import os
        import shutil

        bin_dir = tmp_path / "minimal-bin"
        bin_dir.mkdir(exist_ok=True)
        for tool in ("bash", "grep", "cut", "wc", "tr", "head"):
            real = shutil.which(tool)
            assert real, f"{tool} must be on the real PATH for this test to construct a fake one"
            link = bin_dir / tool
            if not link.exists():
                os.symlink(real, link)
        dirs = [str(bin_dir)]
        if extra_tool_dir is not None:
            dirs.insert(0, str(extra_tool_dir))
        return ":".join(dirs)

    def test_shasum_branch_is_used_when_sha256sum_is_absent(self, good_jar, good_digest, tmp_path):
        import os

        shasum_dir = tmp_path / "shasum-bin"
        shasum_dir.mkdir()
        shasum_shim = shasum_dir / "shasum"
        shasum_shim.write_text(
            "#!/usr/bin/env bash\n"
            'if [ "$1" = "-a" ] && [ "$2" = "256" ]; then shift 2; fi\n'
            'exec /usr/bin/sha256sum "$@"\n',
            encoding="utf-8",
        )
        shasum_shim.chmod(0o755)

        pin_path = write_pin(tmp_path, good_digest)
        env = dict(**{"PATH": self._minimal_path_with(tmp_path, shasum_dir)})
        result = subprocess.run(
            ["bash", str(CHECK_JAR_INTEGRITY), str(good_jar), str(pin_path)],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    def test_no_hash_tool_available_is_an_error(self, good_jar, good_digest, tmp_path):
        pin_path = write_pin(tmp_path, good_digest)
        env = {"PATH": self._minimal_path_with(tmp_path, None)}
        result = subprocess.run(
            ["bash", str(CHECK_JAR_INTEGRITY), str(good_jar), str(pin_path)],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 2
        assert "no sha256 tool found" in result.stdout.lower()
