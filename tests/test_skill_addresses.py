"""Invocation-address integrity: each skill directory's SKILL.md frontmatter `name` must agree
with its own directory name (IV-402).

Anything outside this repo addresses a skill as `iadc-tester:<directory-name>`. Claude Code
resolves the skill half of that address from the directory name it discovers under skills/; if
the frontmatter `name` drifts from it, the address a caller uses silently stops resolving to the
skill a maintainer thinks they renamed. The check below is parametrized over the skill
directories discovered on disk at collection time, so a skill added later is covered without
anyone remembering to add a test for it.
"""

import pytest

from conftest import SKILLS_DIR, read_frontmatter

SKILL_DIRS = sorted((p for p in SKILLS_DIR.iterdir() if p.is_dir()), key=lambda p: p.name)


@pytest.mark.parametrize("skill_dir", SKILL_DIRS, ids=lambda p: p.name)
def test_skill_directory_and_frontmatter_name_agree(skill_dir):
    skill_md = skill_dir / "SKILL.md"
    assert skill_md.is_file(), (
        f"skills/{skill_dir.name}/SKILL.md must exist for iadc-tester:{skill_dir.name} to resolve"
    )
    fields = read_frontmatter(skill_md)
    assert fields.get("name") == skill_dir.name


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
