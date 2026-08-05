"""Invocation-address integrity: each skill directory's SKILL.md frontmatter `name` must agree
with its own directory name (IV-402).

`iadc-tester:generate-selenium-tests` and `iadc-tester:setup` are the two addresses anything
outside this repo calls. Claude Code resolves the skill half of that address from the directory
name it discovers under skills/; if the frontmatter `name` drifts from it, the address a caller
uses silently stops resolving to the skill a maintainer thinks they renamed.
"""

from conftest import SKILLS_DIR, read_frontmatter


def test_generate_selenium_tests_skill_directory_and_frontmatter_name():
    skill_md = SKILLS_DIR / "generate-selenium-tests" / "SKILL.md"
    assert skill_md.is_file(), (
        "skills/generate-selenium-tests/SKILL.md must exist for "
        "iadc-tester:generate-selenium-tests to resolve"
    )
    fields = read_frontmatter(skill_md)
    assert fields.get("name") == "generate-selenium-tests"


def test_setup_skill_directory_and_frontmatter_name():
    skill_md = SKILLS_DIR / "setup" / "SKILL.md"
    assert skill_md.is_file(), "skills/setup/SKILL.md must exist for iadc-tester:setup to resolve"
    fields = read_frontmatter(skill_md)
    assert fields.get("name") == "setup"


def test_setup_skill_is_not_model_invoked():
    """`setup` writes per-project config, a Gradle build and a committed jar — it must only run
    when the user asks for it, never because the model decided setup looked relevant.
    `disable-model-invocation: true` is what enforces that."""
    fields = read_frontmatter(SKILLS_DIR / "setup" / "SKILL.md")
    assert fields.get("disable-model-invocation") == "true"


def test_no_other_skill_directories_exist():
    """The plugin ships exactly two skills — an extra directory would be a silent third address."""
    names = sorted(p.name for p in SKILLS_DIR.iterdir() if p.is_dir())
    assert names == ["generate-selenium-tests", "setup"]
