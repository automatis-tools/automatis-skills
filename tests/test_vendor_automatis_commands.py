from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "vendor-automatis-commands"


def load_vendor():
    # Extensionless script: bare spec_from_file_location returns None on Python 3.14+.
    # Register in sys.modules before exec so @dataclass can resolve the module.
    loader = importlib.machinery.SourceFileLoader(
        "vendor_automatis_commands", str(SCRIPT)
    )
    spec = importlib.util.spec_from_file_location(
        "vendor_automatis_commands", SCRIPT, loader=loader
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    loader.exec_module(mod)
    return mod


def write_skill(root: Path, name: str, text: str) -> Path:
    d = root / "skills" / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(text, encoding="utf-8")
    return d


class ParseFrontmatterTests(unittest.TestCase):
    def setUp(self):
        self.v = load_vendor()

    def test_parses_simple_keys_and_body(self):
        fields, body = self.v.parse_frontmatter(
            "---\nname: automatis-fix-pr\ndescription: Fix a PR\n---\n\n# Title\n\nHello\n"
        )
        self.assertEqual(fields["name"], "automatis-fix-pr")
        self.assertEqual(fields["description"], "Fix a PR")
        self.assertEqual(body, "# Title\n\nHello\n")

    def test_strips_quotes(self):
        fields, _ = self.v.parse_frontmatter(
            '---\ndescription: "Fix a PR"\n---\n\n# T\n'
        )
        self.assertEqual(fields["description"], "Fix a PR")

    def test_rejects_missing_fences(self):
        with self.assertRaises(self.v.FrontmatterError):
            self.v.parse_frontmatter("# no fences\n")

    def test_rejects_block_scalar(self):
        with self.assertRaises(self.v.FrontmatterError):
            self.v.parse_frontmatter("---\ndescription: |\n  nope\n---\n\n# T\n")


class LoadSkillTests(unittest.TestCase):
    def setUp(self):
        self.v = load_vendor()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_load_and_discover(self):
        write_skill(
            self.root,
            "automatis-fix-pr",
            "---\nname: automatis-fix-pr\ndescription: Fix a PR\n---\n\n# T\n",
        )
        write_skill(
            self.root,
            "automatis-ports-release",
            "---\nname: automatis-ports-release\ndescription: Free ports\n---\n\n# T\n",
        )
        dirs = self.v.discover_skills(self.root)
        self.assertEqual(
            [p.name for p in dirs],
            ["automatis-fix-pr", "automatis-ports-release"],
        )
        skill = self.v.load_skill(dirs[0])
        self.assertEqual(skill.name, "automatis-fix-pr")
        self.assertEqual(skill.fields["description"], "Fix a PR")

    def test_name_must_match_folder(self):
        d = write_skill(
            self.root,
            "automatis-fix-pr",
            "---\nname: automatis-other\ndescription: x\n---\n\n# T\n",
        )
        with self.assertRaises(self.v.SkillError):
            self.v.load_skill(d)

    def test_name_must_use_prefix(self):
        d = write_skill(
            self.root,
            "fix-pr",
            "---\nname: fix-pr\ndescription: x\n---\n\n# T\n",
        )
        with self.assertRaises(self.v.SkillError):
            self.v.load_skill(d)

    def test_requires_description(self):
        d = write_skill(
            self.root,
            "automatis-fix-pr",
            "---\nname: automatis-fix-pr\n---\n\n# T\n",
        )
        with self.assertRaises(self.v.SkillError):
            self.v.load_skill(d)


def plugin_fixture(root: Path) -> Path:
    plugin = root / "automatis"
    write_skill(
        plugin,
        "automatis-fix-pr",
        "---\nname: automatis-fix-pr\ndescription: Fix a PR\nargument-hint: \"[pr]\"\nallowed-tools: Bash, Read\n---\n\n# Fix PR\n\nDo the work.\n",
    )
    extra = plugin / "skills" / "automatis-fix-pr" / "scripts"
    extra.mkdir()
    (extra / "helper.sh").write_text("echo ok\n", encoding="utf-8")
    write_skill(
        plugin,
        "automatis-ports-release",
        "---\nname: automatis-ports-release\ndescription: Free ports\n---\n\n# Ports\n",
    )
    return plugin


class VendorTests(unittest.TestCase):
    def setUp(self):
        self.v = load_vendor()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.target = self.root / "product"
        self.source.mkdir()
        self.target.mkdir()
        plugin_fixture(self.source)

    def tearDown(self):
        self.tmp.cleanup()

    def test_render_omits_name(self):
        skill = self.v.load_skill(
            self.source / "automatis" / "skills" / "automatis-fix-pr"
        )
        rendered = self.v.render_claude_command(skill)
        self.assertTrue(rendered.startswith("---\n"))
        self.assertIn("description: Fix a PR\n", rendered)
        self.assertIn("argument-hint: [pr]\n", rendered)
        self.assertIn("allowed-tools: Bash, Read\n", rendered)
        self.assertNotIn("\nname:", rendered)
        self.assertIn("# Fix PR\n", rendered)

    def test_vendor_writes_skills_commands_and_manifest(self):
        logs = self.v.vendor(self.source, self.target)
        self.assertTrue(any("automatis-fix-pr" in line for line in logs))
        skill_dir = self.target / ".agents" / "skills" / "automatis-fix-pr"
        self.assertTrue((skill_dir / "SKILL.md").is_file())
        self.assertTrue((skill_dir / "scripts" / "helper.sh").is_file())
        cmd = (self.target / ".claude" / "commands" / "automatis-fix-pr.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("description: Fix a PR", cmd)
        self.assertNotIn("\nname:", cmd)
        manifest = json.loads(
            (self.target / ".automatis-commands.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["source"], "automatis-tools/automatis-skills")
        self.assertEqual(
            manifest["skills"],
            ["automatis-fix-pr", "automatis-ports-release"],
        )

    def test_vendor_refuses_missing_and_self(self):
        with self.assertRaises(self.v.SkillError):
            self.v.vendor(self.source, self.root / "nope")
        with self.assertRaises(self.v.SkillError):
            self.v.vendor(self.source, self.source)

    def test_dry_run_writes_nothing(self):
        self.v.vendor(self.source, self.target, dry_run=True)
        self.assertFalse((self.target / ".agents").exists())
        self.assertFalse((self.target / ".automatis-commands.json").exists())

    def test_leaves_unmanaged_files(self):
        other = self.target / ".agents" / "skills" / "team-other"
        other.mkdir(parents=True)
        (other / "SKILL.md").write_text("# other\n", encoding="utf-8")
        extra_cmd = self.target / ".claude" / "commands"
        extra_cmd.mkdir(parents=True)
        (extra_cmd / "local-cmd.md").write_text("# local\n", encoding="utf-8")
        self.v.vendor(self.source, self.target)
        self.assertTrue((other / "SKILL.md").is_file())
        self.assertTrue((extra_cmd / "local-cmd.md").is_file())

    def test_prune_removes_dropped_managed_names_only(self):
        self.v.vendor(self.source, self.target)
        dropped = self.target / ".agents" / "skills" / "automatis-old"
        dropped.mkdir(parents=True)
        (dropped / "SKILL.md").write_text("x\n", encoding="utf-8")
        old_cmd = self.target / ".claude" / "commands" / "automatis-old.md"
        old_cmd.write_text("x\n", encoding="utf-8")
        manifest_path = self.target / ".automatis-commands.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        data["skills"].append("automatis-old")
        manifest_path.write_text(json.dumps(data), encoding="utf-8")
        other = self.target / ".agents" / "skills" / "team-other"
        other.mkdir(parents=True)
        (other / "SKILL.md").write_text("# other\n", encoding="utf-8")
        self.v.vendor(self.source, self.target, prune=True)
        self.assertFalse(dropped.exists())
        self.assertFalse(old_cmd.exists())
        self.assertTrue((other / "SKILL.md").is_file())
        self.assertTrue(
            (self.target / ".agents" / "skills" / "automatis-fix-pr" / "SKILL.md").is_file()
        )

    def test_non_prune_keeps_dropped_names_in_manifest(self):
        self.v.vendor(self.source, self.target)
        dropped = "automatis-ports-release"
        shutil.rmtree(self.source / "automatis" / "skills" / dropped)
        self.v.vendor(self.source, self.target)
        skill_dir = self.target / ".agents" / "skills" / dropped
        cmd = self.target / ".claude" / "commands" / f"{dropped}.md"
        self.assertTrue((skill_dir / "SKILL.md").is_file())
        self.assertTrue(cmd.is_file())
        manifest = json.loads(
            (self.target / ".automatis-commands.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            manifest["skills"],
            ["automatis-fix-pr", "automatis-ports-release"],
        )
        self.v.vendor(self.source, self.target, prune=True)
        self.assertFalse(skill_dir.exists())
        self.assertFalse(cmd.exists())
        self.assertTrue(
            (self.target / ".agents" / "skills" / "automatis-fix-pr" / "SKILL.md").is_file()
        )
        manifest = json.loads(
            (self.target / ".automatis-commands.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["skills"], ["automatis-fix-pr"])


import io
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def complete_source(source: Path) -> None:
    write_json(
        source / ".claude-plugin" / "marketplace.json",
        {
            "name": "automatis-tools",
            "plugins": [{"name": "automatis", "source": "./automatis"}],
        },
    )
    write_json(
        source / "automatis" / ".claude-plugin" / "plugin.json",
        {"name": "automatis", "version": "1.0.0"},
    )


class CheckRepoTests(unittest.TestCase):
    def setUp(self):
        self.v = load_vendor()
        self.tmp = tempfile.TemporaryDirectory()
        self.source = Path(self.tmp.name) / "source"
        self.source.mkdir()
        plugin_fixture(self.source)
        complete_source(self.source)

    def tearDown(self):
        self.tmp.cleanup()

    def test_check_ok(self):
        self.assertEqual(self.v.check_repo(self.source), [])

    def test_check_rejects_commands_dir(self):
        (self.source / "automatis" / "commands").mkdir()
        (self.source / "automatis" / "commands" / "fix-pr.md").write_text("x\n")
        errors = self.v.check_repo(self.source)
        self.assertTrue(any("commands" in e for e in errors))

    def test_check_rejects_bad_source(self):
        write_json(
            self.source / ".claude-plugin" / "marketplace.json",
            {
                "name": "automatis-tools",
                "plugins": [{"name": "automatis", "source": "automatis"}],
            },
        )
        errors = self.v.check_repo(self.source)
        self.assertTrue(any("source" in e for e in errors))


class MainTests(unittest.TestCase):
    def setUp(self):
        self.v = load_vendor()
        self.tmp = tempfile.TemporaryDirectory()
        self.source = Path(self.tmp.name) / "source"
        self.target = Path(self.tmp.name) / "product"
        self.source.mkdir()
        self.target.mkdir()
        plugin_fixture(self.source)
        complete_source(self.source)

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, args):
        stderr = io.StringIO()
        stdout = io.StringIO()
        with mock.patch.object(self.v, "SOURCE_REPO", self.source):
            with redirect_stderr(stderr), redirect_stdout(stdout):
                code = self.v.main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_usage_without_args(self):
        code, _, err = self.run_main([])
        self.assertEqual(code, 1)
        self.assertIn("usage", err.lower())

    def test_check_ok_and_fail(self):
        code, _, err = self.run_main(["--check"])
        self.assertEqual(code, 0)
        (self.source / "automatis" / "commands").mkdir()
        code, _, err = self.run_main(["--check"])
        self.assertEqual(code, 1)
        self.assertTrue(err)

    def test_check_rejects_extra_path(self):
        code, _, err = self.run_main(["--check", str(self.target)])
        self.assertEqual(code, 1)

    def test_vendor_via_main(self):
        code, out, err = self.run_main([str(self.target)])
        self.assertEqual(code, 0, err)
        self.assertTrue(
            (self.target / ".claude" / "commands" / "automatis-fix-pr.md").is_file()
        )


if __name__ == "__main__":
    unittest.main()
