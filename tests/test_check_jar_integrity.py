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

from conftest import CHECK_JAR_INTEGRITY, JAR_PIN_FILE, read_pin_file

# Read live from the shipped pin file rather than typed in by hand -- otherwise this is a fourth
# place the pinned digest could go stale unnoticed, on top of the two build.gradle.template /
# SKILL.md restatements test_jar_pin_consistency.py already guards. Used below only as a realistic
# 64-hex string; nothing here runs the script against the real pin file itself.
PRODUCTION_DIGEST = read_pin_file(JAR_PIN_FILE)["SHA256"]


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


def _minimal_path_with(tmp_path: Path, extra_tool_dirs: list[Path] | None = None) -> str:
    """Build a PATH containing only the coreutils this script itself needs (bash, grep, cut, wc,
    tr, head) plus whatever tool directories are listed first, so `command -v <tool>` genuinely
    fails for anything not explicitly provided rather than the branch merely going untested."""
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
    dirs = [str(d) for d in (extra_tool_dirs or [])]
    dirs.append(str(bin_dir))
    return ":".join(dirs)


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


class TestMismatchIsDetected:
    """A deliberately wrong fixture must be rejected, and each test spells out exactly what's
    wrong with it so a failure here is traceable to a specific, named change rather than an
    unspecified difference."""

    def test_one_byte_altered_fixture_is_rejected(self, good_jar, good_digest, tmp_path):
        """Flip one bit of good_jar's first byte, leaving every other byte and the file's length
        untouched. Before flipping it, assert the byte about to change is what's expected, so a
        change that silently fails to apply can't leave this test passing against an unaltered
        fixture."""
        original = bytearray(good_jar.read_bytes())
        assert original[0] == 0x00, "fixture's first byte drifted; the flip below assumes 0x00"
        original[0] ^= 0xFF
        mutated_path = good_jar.parent / "mutated.jar"
        mutated_path.write_bytes(bytes(original))
        assert mutated_path.read_bytes() != good_jar.read_bytes(), "the byte flip did not apply"

        pin_path = write_pin(tmp_path, good_digest)  # pinned to the ORIGINAL (unflipped) digest
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
        assert result.returncode == 2, result.stdout + result.stderr
        assert "not found" in result.stdout.lower()


class TestFilenameCannotSubstituteForTheHash:
    """openssl and certutil both print the target file's own name or path before the digest in
    their output -- unlike sha256sum/shasum, which print the digest first. Taking the first
    64-hex-character run found anywhere in that output used to mean a path that itself contains a
    64-hex segment (a content-addressed cache directory keyed by digest, for instance) could be
    compared against that segment instead of the file's real hash. sha256sum, shasum and openssl
    are now all fed the file on stdin, so none of their output carries a filename at all; certutil
    has no stdin mode, so its branch takes the last hex run in its output instead of the first --
    the real digest always follows the label line that may embed the path."""

    def test_openssl_branch_rejects_a_digest_named_path_with_the_wrong_bytes(
        self, good_digest, tmp_path
    ):
        # A directory literally named for the PINNED digest, holding a file whose actual bytes
        # are something else entirely -- the shape a content-addressed checkout produces, and
        # exactly the shape the old first-run extraction accepted as a pass.
        evil_dir = tmp_path / good_digest
        evil_dir.mkdir()
        evil_file = evil_dir / "appian-selenium-api.jar"
        evil_file.write_bytes(b"not the pinned bytes -- only the containing path claims to be")
        assert hashlib.sha256(evil_file.read_bytes()).hexdigest() != good_digest

        pin_path = write_pin(tmp_path, good_digest)
        env = {"PATH": _minimal_path_with(tmp_path, [_openssl_only_dir(tmp_path)])}
        result = subprocess.run(
            ["bash", str(CHECK_JAR_INTEGRITY), str(evil_file), str(pin_path)],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 1, result.stdout + result.stderr
        assert "MISMATCH" in result.stdout

    def test_openssl_branch_still_accepts_the_correct_bytes_at_a_digest_named_path(
        self, good_jar, good_digest, tmp_path
    ):
        """Positive control for the test above: the same digest-named-directory shape must still
        pass when the bytes really are correct, proving the fix didn't just make this path always
        fail."""
        good_dir = tmp_path / good_digest
        good_dir.mkdir()
        same_named_good_file = good_dir / "appian-selenium-api.jar"
        same_named_good_file.write_bytes(good_jar.read_bytes())

        pin_path = write_pin(tmp_path, good_digest)
        env = {"PATH": _minimal_path_with(tmp_path, [_openssl_only_dir(tmp_path)])}
        result = subprocess.run(
            ["bash", str(CHECK_JAR_INTEGRITY), str(same_named_good_file), str(pin_path)],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "OK" in result.stdout


def _openssl_only_dir(tmp_path: Path) -> Path:
    import shutil

    real_openssl = shutil.which("openssl")
    assert real_openssl, "openssl must be on the real PATH for this test to construct a fake one"
    tool_dir = tmp_path / "openssl-only-bin"
    tool_dir.mkdir(exist_ok=True)
    link = tool_dir / "openssl"
    if not link.exists():
        import os

        os.symlink(real_openssl, link)
    return tool_dir


class TestSizeNeverSubstitutesForHash:
    """A fixture with the correct byte count and the wrong sha256 must fail -- proving there is no
    code path where matching size alone produces a pass."""

    def test_same_size_wrong_digest_is_rejected(self, good_jar, good_digest, tmp_path):
        same_size_wrong = good_jar.parent / "same-size-wrong.jar"
        original_bytes = bytearray(good_jar.read_bytes())
        # Same length, different content throughout -- not just one byte -- so this can't be
        # mistaken for the single-bit-flip case above.
        mutated = bytes((b + 1) % 256 for b in original_bytes)
        same_size_wrong.write_bytes(mutated)
        assert len(mutated) == len(original_bytes)
        assert mutated != bytes(original_bytes)

        pin_path = write_pin(tmp_path, good_digest, size=str(len(original_bytes)))
        result = run_check(same_size_wrong, pin_path)

        assert result.returncode == 1, (
            "a same-size, wrong-hash fixture must fail -- a passing exit here would mean size is "
            "substituting for the hash, which this script must never allow"
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

    def test_overlong_pin_value_is_rejected(self, good_jar, good_digest, tmp_path):
        """A pin value longer than 64 hex characters used to be silently truncated to its first
        64 characters and accepted. The pin's own value must be exactly 64 hex characters, not a
        longer run with the extra characters discarded."""
        pin_path = write_pin(tmp_path, good_digest + "a")
        result = run_check(good_jar, pin_path)
        assert result.returncode == 2, result.stdout + result.stderr
        assert "not a recognizable sha256 digest" in result.stdout


class TestNormalizeDigestAbsorbsPlatformVariance:
    """The platform-dispatch-and-format-reconciliation prose SKILL.md used to carry is now
    absorbed into this script, not deleted outright. These four inputs are the exact four forms
    that prose named. All are constructed here, not captured from a real run of
    sha256sum/shasum/certutil -- certutil isn't available on this (Linux) host, and the other three
    forms are trivial to construct byte-for-byte from the known-correct digest, so constructing all
    four keeps the comparison symmetric instead of trusting three real tool runs against one
    hand-built string."""

    @staticmethod
    def normalize(stdin_text: str, mode: str | None = None) -> subprocess.CompletedProcess:
        args = ["bash", str(CHECK_JAR_INTEGRITY), "--normalize-digest"]
        if mode is not None:
            args.append(mode)
        return subprocess.run(args, input=stdin_text, capture_output=True, text=True)

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
        result = self.normalize(blob, mode="last")
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
        result = self.normalize(blob, mode="last")
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == PRODUCTION_DIGEST

    def test_no_digest_present_fails(self):
        result = self.normalize("no hex here\n")
        assert result.returncode == 1

    def test_certutil_last_mode_prefers_the_real_digest_over_a_path_embedded_one(self):
        """The certutil branch's label line names the file it hashed -- if that path itself
        contains a 64-hex-character segment (a digest-named cache directory, say), the first hex
        run in the blob is that path segment, not the real digest, which always follows it. Mode
        "last" is what the main dispatch uses for this branch; the default ("first") on this same
        blob would find the path-embedded run instead, which is exactly the false pass this fixes."""
        path_embedded_digest = "0" * 64
        blob = (
            f"SHA256 hash of /cache/{path_embedded_digest}/appian-selenium-api.jar:\n"
            f"{PRODUCTION_DIGEST}\n"
            "CertUtil: -hashfile command completed successfully.\n"
        )
        last_result = self.normalize(blob, mode="last")
        assert last_result.returncode == 0, last_result.stderr
        assert last_result.stdout.strip() == PRODUCTION_DIGEST

        first_result = self.normalize(blob, mode="first")
        assert first_result.returncode == 0, first_result.stderr
        assert first_result.stdout.strip() == path_embedded_digest, (
            "this documents the vulnerable behaviour mode 'last' exists to avoid -- if this "
            "assertion starts failing, the default extraction direction changed and the dispatch "
            "table's mode selection for certutil should be re-checked"
        )


class TestHashToolFallback:
    """The script tries sha256sum, then shasum, then openssl, then certutil, in that order --
    absorbing the exact platform dispatch the old prose taught. Forces each non-default branch by
    shrinking PATH to a minimal directory that provides only the coreutils the script itself needs
    (bash, grep, cut, wc, tr, head) plus whichever hash tool(s) each test wants present, so
    `command -v sha256sum` (etc.) genuinely fails rather than the branch merely going untested."""

    def test_shasum_branch_is_used_when_sha256sum_is_absent(self, good_jar, good_digest, tmp_path):
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
        env = {"PATH": _minimal_path_with(tmp_path, [shasum_dir])}
        result = subprocess.run(
            ["bash", str(CHECK_JAR_INTEGRITY), str(good_jar), str(pin_path)],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    def test_no_hash_tool_available_is_an_error(self, good_jar, good_digest, tmp_path):
        pin_path = write_pin(tmp_path, good_digest)
        env = {"PATH": _minimal_path_with(tmp_path, None)}
        result = subprocess.run(
            ["bash", str(CHECK_JAR_INTEGRITY), str(good_jar), str(pin_path)],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 2
        assert "no sha256 tool found" in result.stdout.lower()

    def test_falls_through_to_the_next_tool_when_a_present_one_fails(
        self, good_jar, good_digest, tmp_path
    ):
        """A tool that's on PATH but fails (a broken shim, a permissions problem) isn't trusted
        just because `command -v` found it -- the dispatch loop falls through to the next
        candidate on empty output, not on presence alone."""
        broken_dir = tmp_path / "broken-sha256sum-bin"
        broken_dir.mkdir()
        broken_shim = broken_dir / "sha256sum"
        broken_shim.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
        broken_shim.chmod(0o755)

        shasum_dir = tmp_path / "working-shasum-bin"
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
        env = {"PATH": _minimal_path_with(tmp_path, [broken_dir, shasum_dir])}
        result = subprocess.run(
            ["bash", str(CHECK_JAR_INTEGRITY), str(good_jar), str(pin_path)],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0, result.stdout + result.stderr
