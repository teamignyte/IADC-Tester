"""The plugin manifest: valid JSON, required fields, and the documented duplicate-registration
trap (IV-402).

README.md's own "Layout" section records the bug: declaring `skills` or `hooks` in plugin.json
when they're already auto-discovered from the `skills/` directory makes the plugin "install
successfully but load nothing" — silently, and `claude plugin validate` does not catch it. Nothing
else in this repo catches that at install time, which is why it belongs in this suite.
"""

import json

from conftest import PLUGIN_JSON


def test_plugin_json_is_valid_json_with_required_fields(plugin_manifest):
    for field in ("name", "version", "description", "author"):
        assert field in plugin_manifest, f"plugin.json is missing required field {field!r}"
    assert isinstance(plugin_manifest["author"], dict) and plugin_manifest["author"].get("name")


def test_plugin_name_is_iadc_tester(plugin_manifest):
    """The plugin-name half of every `iadc-tester:<skill>` invocation address derives from here."""
    assert plugin_manifest["name"] == "iadc-tester", (
        "renaming plugin.json's name breaks every iadc-tester:generate-selenium-tests and "
        "iadc-tester:setup call outside this repo"
    )


def test_plugin_json_does_not_declare_skills_or_hooks():
    raw = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
    assert "skills" not in raw, "skills/ is auto-discovered — declaring it too breaks loading silently"
    assert "hooks" not in raw, "hooks/ is auto-discovered — declaring it too breaks loading silently"
