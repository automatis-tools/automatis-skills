from __future__ import annotations

import importlib.machinery
import importlib.util
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


if __name__ == "__main__":
    unittest.main()
