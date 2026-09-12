from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "build-automatis-release"
MANIFESTS = (
    "automatis/.claude-plugin/plugin.json",
    "automatis/.codex-plugin/plugin.json",
    "gemini-extension.json",
)


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        scripts = self.source / "scripts"
        scripts.mkdir()
        shutil.copy2(REPO / "scripts" / "vendor-automatis-commands", scripts)
        for rel in MANIFESTS:
            write_json(self.source / rel, {"name": "automatis", "version": "1.1.0"})
        write_json(
            self.source / ".claude-plugin/marketplace.json",
            {"name": "automatis-tools", "plugins": [{"name": "automatis", "source": "./automatis"}]},
        )
        write_json(
            self.source / ".agents/plugins/marketplace.json",
            {
                "name": "automatis-tools",
                "interface": {"displayName": "Automatis Tools"},
                "plugins": [{"name": "automatis", "source": {"source": "local", "path": "./automatis"}}],
            },
        )
        self.skill = self.source / "automatis/skills/automatis-example"
        self.skill.mkdir(parents=True)
        self.description = 'Explain "quotes", C:\\paths, tabs\tand café'
        (self.skill / "SKILL.md").write_text(
            "---\nname: automatis-example\ndescription: " + self.description +
            "\n---\n\n# Example\n\nUse [the reference](references/source.md).\n",
            encoding="utf-8",
        )
        (self.skill / "references").mkdir()
        (self.skill / "references/source.md").write_text("Reference text.\n", encoding="utf-8")
        (self.skill / "scripts").mkdir()
        self.helper = self.skill / "scripts/helper.sh"
        self.helper.write_text("#!/bin/sh\necho hello\n", encoding="utf-8")
        self.helper.chmod(0o755)
        self.output = self.root / "output"

    def run_builder(self, *args: str) -> subprocess.CompletedProcess[str]:
        self.assertTrue(SCRIPT.is_file(), "release builder is not implemented")
        shutil.copy2(SCRIPT, self.source / "scripts")
        return subprocess.run(
            [sys.executable, str(self.source / "scripts/build-automatis-release"), *args],
            cwd=self.source,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True,
            text=True,
        )

    def build(self, *args: str) -> Path:
        result = self.run_builder("--output", str(self.output), *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        archive = self.output / "automatis.tar.gz"
        self.assertTrue(archive.is_file(), result.stdout)
        return archive

    def test_check_validates_without_creating_output(self):
        before = sorted(path.relative_to(self.source) for path in self.source.rglob("*"))
        result = self.run_builder("--check", "--output", str(self.output), "--tag", "1.1.0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.output.exists())
        after = sorted(
            path.relative_to(self.source) for path in self.source.rglob("*")
            if path != self.source / "scripts/build-automatis-release"
        )
        self.assertEqual(before, after)

    def test_archive_preserves_skill_tree_and_excludes_repository_files(self):
        (self.source / "LICENSE").write_text("MIT fixture\n", encoding="utf-8")
        (self.source / "README.md").write_text("Repository only\n", encoding="utf-8")
        (self.source / ".git").mkdir()
        (self.source / ".git/config").write_text("Private repository config\n", encoding="utf-8")
        (self.skill / "empty-resource-directory").mkdir()
        archive = self.build("--tag", "1.1.0")
        with tarfile.open(archive) as tar:
            files = {member.name for member in tar.getmembers() if member.isfile()}
            self.assertEqual(files, {
                "gemini-extension.json", "LICENSE", "commands/automatis-example.toml",
                "skills/automatis-example/SKILL.md",
                "skills/automatis-example/references/source.md",
                "skills/automatis-example/scripts/helper.sh",
            })
            self.assertEqual(tar.extractfile("skills/automatis-example/SKILL.md").read(), (self.skill / "SKILL.md").read_bytes())
            self.assertEqual(tar.extractfile("skills/automatis-example/references/source.md").read(), b"Reference text.\n")
            self.assertTrue(tar.getmember("skills/automatis-example/empty-resource-directory").isdir())
            self.assertEqual(tar.getmember("skills/automatis-example/scripts/helper.sh").mode, 0o755)
            self.assertTrue(all(member.isfile() or member.isdir() for member in tar.getmembers()))

    def test_command_toml_preserves_description_and_activates_matching_skill(self):
        archive = self.build()
        with tarfile.open(archive) as tar:
            command = tomllib.loads(tar.extractfile("commands/automatis-example.toml").read().decode("utf-8"))
        self.assertEqual(command["description"], self.description)
        self.assertIn("activate_skill", command["prompt"])
        self.assertIn('"name": "automatis-example"', command["prompt"])
        self.assertIn("{{args}}", command["prompt"])
        self.assertIn("\n", command["prompt"])

    def test_command_toml_handles_del_and_non_bmp_unicode(self):
        description = "Handle DEL \x7f and emoji 🚀"
        (self.skill / "SKILL.md").write_text(
            "---\nname: automatis-example\ndescription: " + description + "\n---\n# Example\n",
            encoding="utf-8",
        )
        with tarfile.open(self.build()) as tar:
            text = tar.extractfile("commands/automatis-example.toml").read().decode("utf-8")
        try:
            command = tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            self.fail(f"Gemini command is not valid TOML: {exc}")
        self.assertEqual(command["description"], description)

    def test_rejects_output_inside_canonical_skills(self):
        output = self.skill / "generated"
        result = self.run_builder("--output", str(output))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("output", result.stderr.lower())
        self.assertFalse(output.exists())

    def test_default_output_is_dist(self):
        result = self.run_builder()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.source / "dist/automatis.tar.gz").is_file())

    def test_archive_is_identical_after_source_timestamps_change(self):
        archive = self.build()
        first = archive.read_bytes()
        for path in self.source.rglob("*"):
            os.utime(path, (1234567890, 1234567890))
        archive = self.build()
        self.assertEqual(first, archive.read_bytes())

    def test_rejects_version_mismatch_without_writes(self):
        for rel in MANIFESTS:
            with self.subTest(manifest=rel):
                write_json(self.source / rel, {"name": "automatis", "version": "1.2.0"})
                result = self.run_builder("--output", str(self.output))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("version", result.stderr.lower())
                self.assertFalse(self.output.exists())
                write_json(self.source / rel, {"name": "automatis", "version": "1.1.0"})

    def test_rejects_nonstable_or_invalid_versions(self):
        for version in ("1.1", "v1.1.0", "01.1.0", "1.1.0-rc.1", "1.1.0+build", 110, None):
            with self.subTest(version=version):
                for rel in MANIFESTS:
                    write_json(self.source / rel, {"name": "automatis", "version": version})
                result = self.run_builder("--check")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("version", result.stderr.lower())

    def test_rejects_mismatched_or_prefixed_tags(self):
        for tag in ("1.0.0", "v1.1.0"):
            with self.subTest(tag=tag):
                result = self.run_builder("--check", "--tag", tag)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("tag", result.stderr.lower())

    def test_rejects_wrong_native_package_names(self):
        for rel in MANIFESTS:
            with self.subTest(manifest=rel):
                write_json(self.source / rel, {"name": "other", "version": "1.1.0"})
                result = self.run_builder("--check")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("name", result.stderr.lower())
                write_json(self.source / rel, {"name": "automatis", "version": "1.1.0"})

    def test_rejects_invalid_codex_catalog_source_and_names(self):
        path = self.source / ".agents/plugins/marketplace.json"
        valid = json.loads(path.read_text(encoding="utf-8"))
        changes = [
            {"name": "other", "source": {"source": "local", "path": "./automatis"}},
            {"name": "automatis", "source": "./automatis"},
            {"name": "automatis", "source": {"source": "local", "path": "automatis"}},
            {"name": "automatis", "source": {"source": "local", "path": "../automatis"}},
            {"name": "automatis", "source": {"source": "git", "path": "./automatis"}},
        ]
        for plugin in changes:
            with self.subTest(plugin=plugin):
                write_json(path, {**valid, "plugins": [plugin]})
                result = self.run_builder("--check")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("marketplace", result.stderr.lower())

    def test_rejects_malformed_manifest_without_traceback(self):
        for value in ("{bad json", "[]", '"text"', "null"):
            with self.subTest(value=value):
                (self.source / "gemini-extension.json").write_text(value, encoding="utf-8")
                result = self.run_builder("--check")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("gemini-extension.json", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_rejects_missing_skills_or_invalid_frontmatter(self):
        (self.skill / "SKILL.md").write_text("No frontmatter\n", encoding="utf-8")
        result = self.run_builder("--check")
        self.assertNotEqual(result.returncode, 0)
        shutil.rmtree(self.skill)
        result = self.run_builder("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no Automatis skills", result.stderr)

    def test_rejects_noncanonical_skill_names(self):
        invalid = self.skill.with_name("automatis-bad_name")
        self.skill.rename(invalid)
        (invalid / "SKILL.md").write_text("---\nname: automatis-bad_name\ndescription: Invalid\n---\n# Bad\n", encoding="utf-8")
        result = self.run_builder("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("name", result.stderr.lower())

    def test_rejects_symlinked_skill_resources(self):
        outside = self.root / "outside.txt"
        outside.write_text("Do not package\n", encoding="utf-8")
        link = self.skill / "references/linked.md"
        for target in (outside, self.skill / "references/source.md", self.root / "missing"):
            with self.subTest(target=target):
                link.symlink_to(target)
                try:
                    result = self.run_builder("--output", str(self.output))
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("symlink", result.stderr.lower())
                    self.assertFalse(self.output.exists())
                finally:
                    link.unlink()

    def test_rejects_symlinked_skill_parent(self):
        skills = self.source / "automatis/skills"
        outside = self.root / "external-skills"
        skills.rename(outside)
        skills.symlink_to(outside, target_is_directory=True)
        result = self.run_builder("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", result.stderr.lower())

    def test_rejects_symlinked_manifest(self):
        manifest = self.source / "gemini-extension.json"
        outside = self.root / "external-manifest.json"
        manifest.rename(outside)
        manifest.symlink_to(outside)
        result = self.run_builder("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", result.stderr.lower())

    def test_rejects_legacy_authored_commands(self):
        (self.source / "automatis/commands").mkdir()
        result = self.run_builder("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("commands", result.stderr)


if __name__ == "__main__":
    unittest.main()
