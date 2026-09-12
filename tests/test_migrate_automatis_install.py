from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "migrate-automatis-install"
MANIFEST = ".automatis-commands.json"
BACKUPS = ".automatis-migration-backups"
SKILL = ".agents/skills/automatis-fix-pr"
COMMAND = ".claude/commands/automatis-fix-pr.md"


def snapshot(root: Path) -> dict:
    """Record content, kinds, links, and permissions without following links."""
    result = {}
    for path in sorted(root.rglob("*")):
        mode = path.lstat().st_mode
        relative = str(path.relative_to(root))
        if stat.S_ISLNK(mode):
            result[relative] = ("link", os.readlink(path))
        elif stat.S_ISDIR(mode):
            result[relative] = ("directory", stat.S_IMODE(mode))
        else:
            result[relative] = ("file", path.read_bytes(), stat.S_IMODE(mode))
    return result


def write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


class MigrationTests(unittest.TestCase):
    def setUp(self):
        loader = importlib.machinery.SourceFileLoader("migrate_automatis_install", str(SCRIPT))
        spec = importlib.util.spec_from_file_location(loader.name, SCRIPT, loader=loader)
        self.migration = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = self.migration
        loader.exec_module(self.migration)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.target = self.root / "product"
        self.target.mkdir()

    def manifest(self, skills=None, *, target=None):
        target = self.target if target is None else target
        write(
            target / MANIFEST,
            (json.dumps({
                "source": "automatis-tools/automatis-skills",
                "skills": ["automatis-fix-pr"] if skills is None else skills,
            }, indent=2) + "\n").encode(),
        )

    def managed(self):
        self.manifest()
        write(self.target / SKILL / "SKILL.md", b"# Locally modified skill\n")
        helper = self.target / SKILL / "scripts" / "helper"
        write(helper, b"#!/bin/sh\nprintf 'custom helper\\n'\n")
        helper.chmod(0o751)
        write(self.target / SKILL / "data.bin", b"\x00\xff\r\n")
        write(self.target / COMMAND, b"# Locally modified command\r\n")

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            text=True, capture_output=True, check=False,
        )

    def backup(self):
        backups = list((self.target / BACKUPS).iterdir())
        self.assertEqual(len(backups), 1)
        return backups[0]

    def test_archives_only_manifest_owned_paths_and_preserves_local_edits(self):
        self.managed()
        untouched = {
            ".agents/skills/automatis-unlisted/SKILL.md": b"unlisted Automatis skill",
            ".agents/skills/team-other/SKILL.md": b"other team's skill",
            ".claude/commands/automatis-unlisted.md": b"unlisted command",
            ".claude/commands/local-command.md": b"local command",
            ".codex/config.toml": b"[local]\nenabled = true\n",
            "README.md": b"product documentation",
        }
        for relative, content in untouched.items():
            write(self.target / relative, content)
        original_skill = snapshot(self.target / SKILL)
        original_manifest = (self.target / MANIFEST).read_bytes()

        result = self.run_cli(self.target)

        self.assertEqual(result.returncode, 0, result.stderr)
        backup = self.backup()
        self.assertIn(str(backup), result.stdout)
        self.assertEqual(snapshot(backup / SKILL), original_skill)
        self.assertEqual((backup / COMMAND).read_bytes(), b"# Locally modified command\r\n")
        self.assertEqual((backup / MANIFEST).read_bytes(), original_manifest)
        for relative in (SKILL, COMMAND, MANIFEST):
            self.assertFalse((self.target / relative).exists())
        for relative, content in untouched.items():
            self.assertEqual((self.target / relative).read_bytes(), content)
            self.assertFalse((backup / relative).exists())

    def test_dry_run_reports_paths_without_any_writes(self):
        self.managed()
        before = snapshot(self.target)

        result = self.run_cli(self.target, "--dry-run")

        self.assertEqual(result.returncode, 0, result.stderr)
        for relative in (SKILL, COMMAND, MANIFEST):
            self.assertIn(relative, result.stdout)
        self.assertIn("dry run", result.stdout.lower())
        self.assertEqual(snapshot(self.target), before)

    def test_no_manifest_is_a_clear_noop(self):
        write(self.target / SKILL / "SKILL.md", b"unowned skill")
        before = snapshot(self.target)

        result = self.run_cli(self.target)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no migration needed", result.stdout.lower())
        self.assertEqual(snapshot(self.target), before)

    def test_second_run_does_not_create_another_backup(self):
        self.managed()
        self.migration.migrate(self.target)
        before = snapshot(self.target)

        result = self.run_cli(self.target)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no migration needed", result.stdout.lower())
        self.assertEqual(snapshot(self.target), before)

    def test_missing_managed_paths_are_skipped_and_manifest_is_archived(self):
        self.manifest(["automatis-fix-pr", "automatis-missing"])
        write(self.target / COMMAND, b"remaining command")

        self.migration.migrate(self.target)

        backup = self.backup()
        self.assertEqual((backup / COMMAND).read_bytes(), b"remaining command")
        self.assertTrue((backup / MANIFEST).is_file())
        self.assertFalse((backup / ".agents").exists())

    def test_empty_ownership_list_archives_only_the_manifest(self):
        self.manifest([])
        write(self.target / SKILL / "SKILL.md", b"unlisted")

        self.migration.migrate(self.target)

        self.assertEqual(list(self.backup().iterdir()), [self.backup() / MANIFEST])
        self.assertEqual((self.target / SKILL / "SKILL.md").read_bytes(), b"unlisted")

    def test_rejects_malformed_foreign_and_unsafe_manifests_before_writes(self):
        self.managed()
        invalid = [
            b"{not json", b"\xff", b"[]", b"null", b"{}",
            b'{"source": "another/project", "skills": ["automatis-fix-pr"]}',
            b'{"source": "automatis-tools/automatis-skills"}',
        ]
        for skills in (
            "automatis-fix-pr", None, [1], [True], [{}],
            ["automatis-fix-pr", "automatis-fix-pr"],
            ["../escape"], ["automatis-../escape"], ["automatis-x/../../escape"],
            ["/automatis-absolute"], ["automatis-Fix"], ["automatis-x\n"],
            ["automatis-"], ["automatis-x--y"], ["automatis-x_y"],
        ):
            invalid.append(json.dumps({
                "source": "automatis-tools/automatis-skills", "skills": skills,
            }).encode())
        for content in invalid:
            with self.subTest(content=content):
                write(self.target / MANIFEST, content)
                before = snapshot(self.target)
                with self.assertRaises(self.migration.MigrationError):
                    self.migration.migrate(self.target)
                self.assertEqual(snapshot(self.target), before)

    def test_all_source_types_are_validated_before_any_move(self):
        cases = [
            (SKILL, "file"), (COMMAND, "directory"), (MANIFEST, "directory"),
            (".agents", "file"), (".agents/skills", "file"),
            (".claude", "file"), (".claude/commands", "file"),
            (BACKUPS, "file"),
        ]
        for index, (relative, kind) in enumerate(cases):
            with self.subTest(path=relative, kind=kind):
                target = self.root / f"case-{index}"
                target.mkdir()
                self.manifest(target=target)
                if relative == MANIFEST:
                    (target / MANIFEST).unlink()
                if kind == "directory":
                    (target / relative).mkdir(parents=True)
                else:
                    write(target / relative, b"wrong path type")
                before = snapshot(target)
                with self.assertRaises(self.migration.MigrationError):
                    self.migration.migrate(target)
                self.assertEqual(snapshot(target), before)

    def test_later_invalid_skill_prevents_archiving_earlier_valid_skill(self):
        self.managed()
        self.manifest(["automatis-fix-pr", "automatis-ports-release"])
        write(self.target / ".agents/skills/automatis-ports-release", b"wrong type")
        before = snapshot(self.target)

        with self.assertRaises(self.migration.MigrationError):
            self.migration.migrate(self.target)

        self.assertEqual(snapshot(self.target), before)

    def test_rejects_symlinked_parents_and_source_leaves(self):
        external = self.root / "external"
        external.mkdir()
        write(external / "keep", b"external content")
        for index, relative in enumerate([
            ".agents", ".agents/skills", ".claude", ".claude/commands",
            SKILL, COMMAND, MANIFEST, BACKUPS,
        ]):
            with self.subTest(path=relative):
                target = self.root / f"case-{index}"
                target.mkdir()
                self.manifest(target=target)
                link = target / relative
                if relative == MANIFEST:
                    link.unlink()
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(external, target_is_directory=True)
                before = snapshot(self.root)
                with self.assertRaisesRegex(self.migration.MigrationError, "symlink"):
                    self.migration.migrate(target)
                self.assertEqual(snapshot(self.root), before)

    def test_rejects_dangling_source_symlink(self):
        self.manifest()
        link = self.target / COMMAND
        link.parent.mkdir(parents=True)
        link.symlink_to(self.root / "missing")
        before = snapshot(self.target)

        with self.assertRaisesRegex(self.migration.MigrationError, "symlink"):
            self.migration.migrate(self.target)

        self.assertEqual(snapshot(self.target), before)

    def test_rejects_symlinked_target_and_target_ancestor(self):
        self.managed()
        link = self.root / "alias"
        link.symlink_to(self.target, target_is_directory=True)
        parent_link = self.root / "parent-alias"
        parent_link.symlink_to(self.root, target_is_directory=True)
        before = snapshot(self.target)

        for target in (link, parent_link / self.target.name):
            with self.subTest(target=target):
                with self.assertRaisesRegex(self.migration.MigrationError, "symlink"):
                    self.migration.migrate(target)
        self.assertEqual(snapshot(self.target), before)

    def test_moving_skill_directory_preserves_nested_symlinks_without_following_them(self):
        self.managed()
        external = self.root / "private-data"
        external.write_bytes(b"do not read or move through symlink")
        (self.target / SKILL / "reference").symlink_to(external)

        self.migration.migrate(self.target)

        moved_link = self.backup() / SKILL / "reference"
        self.assertTrue(moved_link.is_symlink())
        self.assertEqual(os.readlink(moved_link), str(external))
        self.assertEqual(external.read_bytes(), b"do not read or move through symlink")

    def test_manifest_is_moved_last_and_mid_move_failure_restores_originals(self):
        self.managed()
        before = snapshot(self.target)
        original_error = OSError("forced manifest move failure")
        rename = self.migration.os.rename

        def fail_manifest(source, destination):
            if Path(source) == self.target / MANIFEST:
                self.assertFalse((self.target / SKILL).exists())
                self.assertFalse((self.target / COMMAND).exists())
                raise original_error
            return rename(source, destination)

        with mock.patch.object(self.migration.os, "rename", side_effect=fail_manifest):
            with self.assertRaises(OSError) as raised:
                self.migration.migrate(self.target)

        self.assertIs(raised.exception, original_error)
        # Empty backup directories are harmless; all original content must be restored.
        restored = snapshot(self.target)
        restored = {path: value for path, value in restored.items()
                    if path != BACKUPS and not path.startswith(BACKUPS + "/")}
        self.assertEqual(restored, before)
        backup_root = self.target / BACKUPS
        if backup_root.exists():
            self.assertFalse(any(path.is_file() for path in backup_root.rglob("*")))

    def test_failed_rollback_keeps_backup_and_reports_both_failures(self):
        self.managed()
        original_error = OSError("forced forward failure")
        rollback_error = OSError("forced recovery failure")
        rename = self.migration.os.rename

        def fail_forward_and_recovery(source, destination):
            source = Path(source)
            if source == self.target / MANIFEST:
                raise original_error
            if BACKUPS in source.parts and source.name == "automatis-fix-pr":
                raise rollback_error
            return rename(source, destination)

        with mock.patch.object(self.migration.os, "rename", side_effect=fail_forward_and_recovery):
            with self.assertRaises(self.migration.MigrationError) as raised:
                self.migration.migrate(self.target)

        self.assertIs(raised.exception.__cause__, original_error)
        self.assertIn(str(original_error), str(raised.exception))
        self.assertIn(str(rollback_error), str(raised.exception))
        backup = self.backup()
        self.assertIn(str(backup), str(raised.exception))
        self.assertEqual((backup / SKILL / "SKILL.md").read_bytes(), b"# Locally modified skill\n")
        self.assertTrue((self.target / MANIFEST).is_file())
        self.assertEqual((self.target / COMMAND).read_bytes(), b"# Locally modified command\r\n")

    def test_rollback_does_not_overwrite_a_new_file_at_the_original_path(self):
        self.managed()
        rename = self.migration.os.rename

        def create_conflict_and_fail(source, destination):
            if Path(source) == self.target / MANIFEST:
                write(self.target / COMMAND, b"new content from another process")
                raise OSError("forced failure after concurrent write")
            return rename(source, destination)

        with mock.patch.object(self.migration.os, "rename", side_effect=create_conflict_and_fail):
            with self.assertRaisesRegex(self.migration.MigrationError, "refusing to overwrite"):
                self.migration.migrate(self.target)

        self.assertEqual((self.target / COMMAND).read_bytes(), b"new content from another process")
        self.assertEqual((self.backup() / COMMAND).read_bytes(), b"# Locally modified command\r\n")
        self.assertTrue((self.target / SKILL / "SKILL.md").is_file())
        self.assertTrue((self.target / MANIFEST).is_file())

    def test_existing_backups_are_preserved_and_new_backup_is_unique(self):
        self.managed()
        write(self.target / BACKUPS / "previous" / "keep", b"previous backup")

        self.migration.migrate(self.target)

        self.assertEqual((self.target / BACKUPS / "previous" / "keep").read_bytes(), b"previous backup")
        self.assertEqual(len(list((self.target / BACKUPS).iterdir())), 2)

    def test_cli_requires_target_and_reports_invalid_target(self):
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("usage", result.stderr.lower())
        missing = self.run_cli(self.root / "missing")
        self.assertNotEqual(missing.returncode, 0)
        self.assertFalse((self.root / "missing").exists())

    def test_cli_invalid_manifest_fails_without_a_traceback_or_writes(self):
        write(self.target / MANIFEST, b"[]")
        before = snapshot(self.target)

        result = self.run_cli(self.target)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("JSON object", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(snapshot(self.target), before)


if __name__ == "__main__":
    unittest.main()
