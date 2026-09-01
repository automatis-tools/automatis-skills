# Multi-harness Automatis commands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn this marketplace into a multi-harness Automatis command source: Agent Skills as the only authored form, a vendor script that copies them into product repos, and `/automatis-<name>` (Codex: `$automatis-<name>`) as the invocation.

**Architecture:** Canonical files live at `automatis/skills/automatis-<name>/SKILL.md`. `scripts/vendor-automatis-commands` validates them and writes `.agents/skills/` plus `.claude/commands/` into a target product repo. This plugin repo deletes `automatis/commands/` so the colon slash `/automatis:<name>` cannot come back.

**Tech Stack:** Python 3 stdlib (`unittest`, `argparse`, `pathlib`, `shutil`, `json`). No PyYAML, no `jq`, no new packages.

**Spec:** `docs/superpowers/specs/2026-09-01-multi-harness-automatis-commands-design.md`

## Global Constraints

- Invocation in skill bodies and docs is `/automatis-<name>`; Codex is `$automatis-<name>`. Never restore `/automatis:<name>` as an alias.
- Author only `automatis/skills/<name>/SKILL.md`. Do not create `automatis/commands/`.
- Vendor destinations are only `.agents/skills/<name>/`, `.claude/commands/<name>.md`, and `.automatis-commands.json`.
- `scripts/vendor-automatis-commands` is Python 3, stdlib only, shebang `#!/usr/bin/env python3`.
- Frontmatter is single-line `key: value` (optional quotes). Nested maps and `|` / `>` blocks are errors.
- Source repo for the CLI is the directory that contains `scripts/vendor-automatis-commands` (`Path(__file__).resolve().parent.parent`), not cwd.
- `git add`, `git commit`, and `git push` are separate commands. Never `--no-verify`. Never Claude/Grok coauthor trailers.
- This change set does not vendor into real product repos.

## File map

| File | Responsibility |
|------|----------------|
| `scripts/vendor-automatis-commands` | Parse skills, `--check`, vendor/prune/dry-run CLI |
| `tests/test_vendor_automatis_commands.py` | unittest for parser, vendor, CLI |
| `automatis/skills/automatis-*/SKILL.md` | Canonical procedures |
| `automatis/commands/` | Deleted after migration |
| `README.md`, `CLAUDE.md`, `AGENTS.md` | Multi-harness authoring and vendor usage |
| `automatis/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Non-Claude-only blurbs; mention git-cleanup |
| `.github/workflows/lint.yml` | Run `--check` |
| `.githooks/pre-push` | Run `--check` on push |
| `.gitignore` | Ignore `.gitworktrees/` |

---

### Task 1: Skill loader

**Files:**
- Create: `scripts/vendor-automatis-commands`
- Create: `tests/test_vendor_automatis_commands.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `class FrontmatterError(ValueError)`
  - `class SkillError(ValueError)`
  - `class Skill`: attributes `name: str`, `directory: Path`, `fields: dict[str, str]`, `body: str`
  - `parse_frontmatter(text: str) -> tuple[dict[str, str], str]`
  - `discover_skills(plugin_root: Path) -> list[Path]` — sorted child dirs of `plugin_root/skills` that contain `SKILL.md`
  - `load_skill(directory: Path) -> Skill` — requires `name` and `description`; `name` equals `directory.name`; `name` starts with `automatis-`

- [ ] **Step 1: Write failing tests for frontmatter and skill loading**

Create `tests/test_vendor_automatis_commands.py`:

```python
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "vendor-automatis-commands"


def load_vendor():
    spec = importlib.util.spec_from_file_location("vendor_automatis_commands", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m unittest discover -s tests -v
```

Expected: FAIL with `FileNotFoundError` or import error because `scripts/vendor-automatis-commands` does not exist.

- [ ] **Step 3: Implement the loader**

Create `scripts/vendor-automatis-commands`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

FRONTMATTER_LINE = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")


class FrontmatterError(ValueError):
    pass


class SkillError(ValueError):
    pass


@dataclass
class Skill:
    name: str
    directory: Path
    fields: dict[str, str]
    body: str


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        raise FrontmatterError("missing opening ---")
    rest = text[3:]
    if rest.startswith("\n"):
        rest = rest[1:]
    end = rest.find("\n---")
    if end < 0:
        raise FrontmatterError("missing closing ---")
    raw_fields = rest[:end]
    body = rest[end + 4 :]
    if body.startswith("\n"):
        body = body[1:]
    fields: dict[str, str] = {}
    for line in raw_fields.splitlines():
        if not line.strip():
            continue
        match = FRONTMATTER_LINE.match(line)
        if not match:
            raise FrontmatterError(f"unsupported frontmatter line: {line!r}")
        key, value = match.group(1), match.group(2).strip()
        if value in ("|", ">", ">-", "|-") or value.startswith("|") or value.startswith(">"):
            raise FrontmatterError(f"block scalars are not supported: {key}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        fields[key] = value
    return fields, body


def discover_skills(plugin_root: Path) -> list[Path]:
    skills_root = plugin_root / "skills"
    if not skills_root.is_dir():
        return []
    found: list[Path] = []
    for child in sorted(skills_root.iterdir()):
        if child.is_dir() and (child / "SKILL.md").is_file():
            found.append(child)
    return found


def load_skill(directory: Path) -> Skill:
    path = directory / "SKILL.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SkillError(f"cannot read {path}: {exc}") from exc
    try:
        fields, body = parse_frontmatter(text)
    except FrontmatterError as exc:
        raise SkillError(f"{path}: {exc}") from exc
    name = fields.get("name", "")
    if not name:
        raise SkillError(f"{path}: missing name")
    if "description" not in fields or not fields["description"]:
        raise SkillError(f"{path}: missing description")
    if name != directory.name:
        raise SkillError(f"{path}: name {name!r} does not match folder {directory.name!r}")
    if not name.startswith("automatis-"):
        raise SkillError(f"{path}: name must start with 'automatis-'")
    return Skill(name=name, directory=directory, fields=fields, body=body)
```

Then `chmod +x scripts/vendor-automatis-commands`.

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m unittest discover -s tests -v
```

Expected: PASS (all Task 1 tests).

- [ ] **Step 5: Commit**

```bash
git add tests/test_vendor_automatis_commands.py
```

```bash
git add scripts/vendor-automatis-commands
```

```bash
git commit -m "$(cat <<'EOF'
Add skill frontmatter loader for Automatis vendor script

Parse SKILL.md metadata with stdlib-only rules so later vendor
steps can validate names before copying into product repos.
EOF
)"
```

---

### Task 2: Vendor writes

**Files:**
- Modify: `scripts/vendor-automatis-commands`
- Modify: `tests/test_vendor_automatis_commands.py`

**Interfaces:**
- Consumes: `Skill`, `discover_skills`, `load_skill` from Task 1
- Produces:
  - `COMMAND_KEYS = ("description", "argument-hint", "allowed-tools")`
  - `render_claude_command(skill: Skill) -> str`
  - `load_skills(plugin_root: Path) -> list[Skill]`
  - `vendor(source_repo: Path, target_repo: Path, *, prune: bool = False, dry_run: bool = False) -> list[str]`
  - Manifest path `target_repo / ".automatis-commands.json"` with keys `source` (`"automatis-tools/claude-code-plugins"`) and `skills` (sorted names)
  - Raises `SkillError` if `target_repo` is missing, not a directory, or `resolve()`s to `source_repo`

Replace a managed skill directory by deleting it then copying (`shutil.rmtree` + `shutil.copytree`) so files removed from the source skill do not linger.

- [ ] **Step 1: Write failing vendor tests**

Append to `tests/test_vendor_automatis_commands.py`:

```python
import json
import os


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
        self.assertEqual(manifest["source"], "automatis-tools/claude-code-plugins")
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m unittest discover -s tests -v
```

Expected: FAIL with `AttributeError: module ... has no attribute 'vendor'` (or `render_claude_command`).

- [ ] **Step 3: Implement render + vendor**

Append to `scripts/vendor-automatis-commands` (keep Task 1 code):

```python
import json
import shutil

COMMAND_KEYS = ("description", "argument-hint", "allowed-tools")
MANIFEST_NAME = ".automatis-commands.json"
MANIFEST_SOURCE = "automatis-tools/claude-code-plugins"


def load_skills(plugin_root: Path) -> list[Skill]:
    return [load_skill(path) for path in discover_skills(plugin_root)]


def render_claude_command(skill: Skill) -> str:
    lines = ["---"]
    for key in COMMAND_KEYS:
        if key in skill.fields:
            lines.append(f"{key}: {skill.fields[key]}")
    lines.append("---")
    body = skill.body
    if not body.endswith("\n"):
        body += "\n"
    return "\n".join(lines) + "\n" + body


def _read_manifest(target_repo: Path) -> list[str]:
    path = target_repo / MANIFEST_NAME
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    skills = data.get("skills", [])
    if not isinstance(skills, list):
        raise SkillError(f"{path}: skills must be a list")
    return [str(name) for name in skills]


def _write_manifest(target_repo: Path, names: list[str]) -> None:
    payload = {"source": MANIFEST_SOURCE, "skills": names}
    (target_repo / MANIFEST_NAME).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def vendor(
    source_repo: Path,
    target_repo: Path,
    *,
    prune: bool = False,
    dry_run: bool = False,
) -> list[str]:
    source_repo = source_repo.resolve()
    if not target_repo.exists():
        raise SkillError(f"target does not exist: {target_repo}")
    if not target_repo.is_dir():
        raise SkillError(f"target is not a directory: {target_repo}")
    target_repo = target_repo.resolve()
    if target_repo == source_repo:
        raise SkillError("refusing to vendor into the plugin repository")
    skills = load_skills(source_repo / "automatis")
    names = [skill.name for skill in skills]
    logs: list[str] = []
    previous = _read_manifest(target_repo)
    to_prune = [name for name in previous if name not in names] if prune else []

    def log(action: str, rel: str) -> None:
        logs.append(f"{action} {rel}")

    for skill in skills:
        log("copy", f".agents/skills/{skill.name}/")
        log("write", f".claude/commands/{skill.name}.md")
    for name in to_prune:
        log("prune", f".agents/skills/{name}/")
        log("prune", f".claude/commands/{name}.md")
    log("write", MANIFEST_NAME)
    if dry_run:
        return logs

    agents = target_repo / ".agents" / "skills"
    commands = target_repo / ".claude" / "commands"
    agents.mkdir(parents=True, exist_ok=True)
    commands.mkdir(parents=True, exist_ok=True)
    for skill in skills:
        dest = agents / skill.name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(skill.directory, dest)
        (commands / f"{skill.name}.md").write_text(
            render_claude_command(skill), encoding="utf-8"
        )
    for name in to_prune:
        dest = agents / name
        if dest.exists():
            shutil.rmtree(dest)
        cmd = commands / f"{name}.md"
        if cmd.exists():
            cmd.unlink()
    _write_manifest(target_repo, names)
    return logs
```

If `test_render_omits_name` fails because `argument-hint: [pr]` still has quotes, strip quotes in `parse_frontmatter` (already in Task 1) and assert against the unquoted value.

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_vendor_automatis_commands.py
```

```bash
git add scripts/vendor-automatis-commands
```

```bash
git commit -m "$(cat <<'EOF'
Add vendor copy into product-repo skill and command paths

Write .agents/skills, generated .claude/commands markdown, and a
manifest, with dry-run and prune behavior covered by tests.
EOF
)"
```

---

### Task 3: CLI and `--check`

**Files:**
- Modify: `scripts/vendor-automatis-commands`
- Modify: `tests/test_vendor_automatis_commands.py`

**Interfaces:**
- Consumes: `vendor`, `load_skills`, `FrontmatterError`, `SkillError`
- Produces:
  - `SOURCE_REPO = Path(__file__).resolve().parent.parent`
  - `check_repo(repo_root: Path) -> list[str]` — empty list means OK. Errors (each a string) for: unreadable/invalid `repo_root/.claude-plugin/marketplace.json`; unreadable/invalid `repo_root/automatis/.claude-plugin/plugin.json`; marketplace plugin `source` not `./automatis` or that dir missing; `repo_root/automatis/commands` exists; any `load_skill` failure
  - `main(argv: list[str] | None = None) -> int`
  - CLI:
    - `vendor-automatis-commands --check` → `check_repo(SOURCE_REPO)`, print errors on stderr, exit 1 if any
    - `vendor-automatis-commands <product-repo> [--dry-run] [--prune]`
    - no args → print usage to stderr, exit 1
    - `--check` with a product-repo argument is an error (usage, exit 1)

Do not call `check_repo` on this real repository in tests until Task 4 deletes `automatis/commands/`.

- [ ] **Step 1: Write failing CLI tests**

Append:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m unittest discover -s tests -v
```

Expected: FAIL with missing `check_repo` or `main`.

- [ ] **Step 3: Implement check_repo and main**

Append to `scripts/vendor-automatis-commands`:

```python
import argparse
import sys

SOURCE_REPO = Path(__file__).resolve().parent.parent


def check_repo(repo_root: Path) -> list[str]:
    errors: list[str] = []
    marketplace = repo_root / ".claude-plugin" / "marketplace.json"
    plugin = repo_root / "automatis" / ".claude-plugin" / "plugin.json"
    try:
        market = json.loads(marketplace.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid marketplace.json: {exc}")
        market = None
    try:
        json.loads(plugin.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid plugin.json: {exc}")
    if isinstance(market, dict):
        plugins = market.get("plugins", [])
        if not plugins:
            errors.append("marketplace.json has no plugins")
        for entry in plugins:
            src = entry.get("source", "")
            name = entry.get("name", "?")
            if not isinstance(src, str) or not src.startswith("./"):
                errors.append(
                    f"plugin {name!r}: source must use './<dir>' form (got {src!r})"
                )
                continue
            root = repo_root / src[2:]
            if not root.is_dir():
                errors.append(f"plugin {name!r}: source dir {root} does not exist")
            manifest = root / ".claude-plugin" / "plugin.json"
            if not manifest.is_file():
                errors.append(f"plugin {name!r}: missing {manifest}")
    commands = repo_root / "automatis" / "commands"
    if commands.exists():
        errors.append("legacy automatis/commands/ must not exist")
    try:
        load_skills(repo_root / "automatis")
    except SkillError as exc:
        errors.append(str(exc))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vendor-automatis-commands",
        description="Vendor Automatis skills into a product repo.",
    )
    parser.add_argument("product_repo", nargs="?", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--prune", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        if args.product_repo is not None:
            print("usage: --check does not take a product repo", file=sys.stderr)
            return 1
        errors = check_repo(SOURCE_REPO)
        for item in errors:
            print(item, file=sys.stderr)
        return 1 if errors else 0
    if args.product_repo is None:
        parser.print_usage(sys.stderr)
        return 1
    try:
        logs = vendor(
            SOURCE_REPO,
            args.product_repo,
            prune=args.prune,
            dry_run=args.dry_run,
        )
    except SkillError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for line in logs:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_vendor_automatis_commands.py
```

```bash
git add scripts/vendor-automatis-commands
```

```bash
git commit -m "$(cat <<'EOF'
Add vendor CLI with --check, --dry-run, and --prune

Validate marketplace JSON, reject leftover commands/, and vendor
from the script's repository rather than the current directory.
EOF
)"
```

---

### Task 4: Migrate the three commands to skills

**Files:**
- Create: `automatis/skills/automatis-fix-pr/SKILL.md`
- Create: `automatis/skills/automatis-ports-release/SKILL.md`
- Create: `automatis/skills/automatis-git-cleanup/SKILL.md`
- Delete: `automatis/commands/fix-pr.md`
- Delete: `automatis/commands/ports-release.md`
- Delete: `automatis/commands/git-cleanup.md`
- Delete: `automatis/commands/` (directory)

**Interfaces:**
- Consumes: `--check` from Task 3
- Produces: three valid skills; `./scripts/vendor-automatis-commands --check` exits 0 on this repo

Do not rewrite procedure bash/Python. Move each command body as-is except:

1. Add `name: automatis-<cmd>` to frontmatter.
2. Replace every `/automatis:<cmd>` with `/automatis-<cmd>` (Arguments, example sessions, echo strings).
3. In **Arguments**, add one sentence before the bullets: `Invoke as `/automatis-<cmd>` (Codex: `$automatis-<cmd>`).`

- [ ] **Step 1: Create the three SKILL.md files**

Copy each `automatis/commands/<cmd>.md` to `automatis/skills/automatis-<cmd>/SKILL.md`.

Frontmatter for `automatis-fix-pr` (keep existing description, argument-hint, allowed-tools):

```markdown
---
name: automatis-fix-pr
description: Fix open review comments on a GitHub PR
argument-hint: "[pr-url | pr-number] [--review=ID] [--severity=high,medium,low,critical]"
allowed-tools: Bash, Read, Edit, Grep, Glob
---
```

Frontmatter for `automatis-ports-release`:

```markdown
---
name: automatis-ports-release
description: Release port conflicts on macOS by killing the offending process
argument-hint: "[port] [port...]"
allowed-tools: Bash
---
```

Frontmatter for `automatis-git-cleanup`:

```markdown
---
name: automatis-git-cleanup
description: Clean up local git branches — create PRs for unmerged work, delete merged/gone branches, end on up-to-date main
argument-hint: "[--dry-run] [--no-pr]"
allowed-tools: Bash
---
```

Replace strings in those three files:

| From | To |
|------|----|
| `/automatis:fix-pr` | `/automatis-fix-pr` |
| `/automatis:ports-release` | `/automatis-ports-release` |
| `/automatis:git-cleanup` | `/automatis-git-cleanup` |

In each skill’s Arguments section, insert this as the first line of that section (adjust `<cmd>`):

```markdown
Invoke as `/automatis-fix-pr` (Codex: `$automatis-fix-pr`).
```

```markdown
Invoke as `/automatis-ports-release` (Codex: `$automatis-ports-release`).
```

```markdown
Invoke as `/automatis-git-cleanup` (Codex: `$automatis-git-cleanup`).
```

- [ ] **Step 2: Delete legacy commands**

```bash
rm automatis/commands/fix-pr.md automatis/commands/ports-release.md automatis/commands/git-cleanup.md
rmdir automatis/commands
```

Confirm `automatis/commands` is gone:

```bash
test ! -e automatis/commands
```

Expected: exit 0.

- [ ] **Step 3: Run --check and unit tests**

```bash
python3 -m unittest discover -s tests -v
```

```bash
./scripts/vendor-automatis-commands --check
```

Expected: tests PASS; `--check` exits 0 and prints nothing.

If `--check` fails, fix the reported skill — do not delete or comment out procedures.

- [ ] **Step 4: Smoke-vendor into a throwaway directory**

```bash
mkdir -p /tmp/automatis-vendor-smoke
./scripts/vendor-automatis-commands /tmp/automatis-vendor-smoke
test -f /tmp/automatis-vendor-smoke/.agents/skills/automatis-fix-pr/SKILL.md
test -f /tmp/automatis-vendor-smoke/.claude/commands/automatis-fix-pr.md
test -f /tmp/automatis-vendor-smoke/.automatis-commands.json
grep -q 'name: automatis-fix-pr' /tmp/automatis-vendor-smoke/.agents/skills/automatis-fix-pr/SKILL.md
! grep -q '^name:' /tmp/automatis-vendor-smoke/.claude/commands/automatis-fix-pr.md
rm -rf /tmp/automatis-vendor-smoke
```

Expected: every `test`/`grep` succeeds.

- [ ] **Step 5: Commit**

```bash
git add automatis/skills
```

```bash
git add -u automatis/commands
```

```bash
git commit -m "$(cat <<'EOF'
Migrate Automatis commands to hyphen-prefixed Agent Skills

Move fix-pr, ports-release, and git-cleanup into skills/ and drop
plugin commands/ so /automatis:<name> is no longer defined here.
EOF
)"
```

---

### Task 5: Docs, CI, and pre-push hook

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Create: `AGENTS.md`
- Modify: `automatis/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `.github/workflows/lint.yml`
- Create: `.githooks/pre-push`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `./scripts/vendor-automatis-commands --check`
- Produces: docs that describe `/automatis-<name>` and the vendor CLI; CI and pre-push both run `--check`

- [ ] **Step 1: Update plugin and marketplace descriptions**

`automatis/.claude-plugin/plugin.json`:

```json
{
  "name": "automatis",
  "version": "1.0.0",
  "description": "Automatis team command toolbelt: fix GitHub PR review comments, release macOS port conflicts, clean up local git branches",
  "author": { "name": "Automatis Tools" },
  "keywords": ["pr", "review", "github", "port", "macos", "git", "productivity", "devops"]
}
```

In `.claude-plugin/marketplace.json`:
- `metadata.description`: `Automatis team commands for Claude Code, Grok, Codex, Gemini, and Kimi`
- plugin `description`: same as plugin.json description above
- plugin `tags`: add `"git"`

- [ ] **Step 2: Rewrite README.md**

Replace the file with:

````markdown
# Automatis Tools

Team commands for Claude Code, Grok, Codex, Gemini, and Kimi. Author once as Agent Skills in this repo; vendor a copy into each product repo.

## Invocation

| Tool | Example |
|------|---------|
| Claude Code, Grok, Gemini, Kimi | `/automatis-fix-pr` |
| Codex | `$automatis-fix-pr` |
| Kimi fallback | `/skill:automatis-fix-pr` |

The colon form `/automatis:fix-pr` is retired.

## Vendor into a product repo

From this checkout:

```bash
./scripts/vendor-automatis-commands /path/to/product-repo
./scripts/vendor-automatis-commands /path/to/product-repo --dry-run
./scripts/vendor-automatis-commands /path/to/product-repo --prune
```

That writes:

- `.agents/skills/automatis-<name>/` — Codex, Grok, Gemini, Kimi
- `.claude/commands/automatis-<name>.md` — Claude Code (`/automatis-<name>`)
- `.automatis-commands.json` — names this script manages

Commit those files in the product repo. Re-run the script when a command changes here.

## Commands

| Command | Description |
|---------|-------------|
| `/automatis-fix-pr` | Fix GitHub PR review comments |
| `/automatis-ports-release` | Release port conflicts on macOS |
| `/automatis-git-cleanup` | Clean up local git branches |

### /automatis-fix-pr

```bash
/automatis-fix-pr https://github.com/owner/repo/pull/123
/automatis-fix-pr 123
/automatis-fix-pr
```

### /automatis-ports-release

```bash
/automatis-ports-release 8000
/automatis-ports-release 8000 8001
/automatis-ports-release
```

### /automatis-git-cleanup

```bash
/automatis-git-cleanup
/automatis-git-cleanup --dry-run
/automatis-git-cleanup --no-pr
```

## Claude marketplace (source package)

This repo remains a Claude Code marketplace. Installing the plugin copies skills; it does **not** register `/automatis-fix-pr` on Claude (plugin components are colon-namespaced). Product repos should vendor as above.

```bash
/plugin marketplace add automatis-tools/claude-code-plugins
/plugin install automatis@automatis-tools
```

## Contributing

1. Add `automatis/skills/automatis-<name>/SKILL.md` with `name: automatis-<name>`.
2. Run `./scripts/vendor-automatis-commands --check`.
3. Commit here, then vendor into each product repo.

See [CLAUDE.md](CLAUDE.md) and [AGENTS.md](AGENTS.md) for house style, shell-safety, and git hooks.

## License

MIT
````

- [ ] **Step 3: Rewrite CLAUDE.md structure and add AGENTS.md**

`CLAUDE.md` changes (keep the Shell Safety section verbatim; rewrite the rest):

- Overview: multi-harness skills repo; product-repo invocation `/automatis-<name>`; Codex `$automatis-<name>`; marketplace is the source package, not the Claude slash path.
- Structure tree: `automatis/skills/…`, `scripts/vendor-automatis-commands`, no `commands/`.
- Naming: skill folder and `name:` are `automatis-<action>` (kebab-case after the prefix).
- Adding a command: the four-step list from the spec (create SKILL.md, `--check`, commit, vendor in product repos). Deleting: remove the folder, vendor with `--prune`.
- Command File Structure: retitle to Skill File Structure; frontmatter includes `name`; Arguments use `/automatis-<cmd>` and one Codex `$` line; reference `automatis/skills/automatis-fix-pr/SKILL.md`.
- Manual Verification: `./scripts/vendor-automatis-commands --check`; `python3 -m unittest discover -s tests -v`; JSON parse is included in `--check`.
- Git hooks: `git config core.hooksPath .githooks` so pre-push runs `--check`. Never `--no-verify`.

Create `AGENTS.md`:

```markdown
# AGENTS.md

This repository authors Automatis team commands as Agent Skills and vendors them into product repos.

Layout, invocation, vendor CLI, and how to add a command: see [CLAUDE.md](CLAUDE.md) (same rules for every harness).

Quick facts:

- Author `automatis/skills/automatis-<name>/SKILL.md` only. Do not add `automatis/commands/`.
- Invoke `/automatis-<name>` (Codex: `$automatis-<name>`).
- From this checkout: `./scripts/vendor-automatis-commands /path/to/product-repo`
- Validate: `./scripts/vendor-automatis-commands --check` and `python3 -m unittest discover -s tests -v`
- Enable hooks: `git config core.hooksPath .githooks`

Shell-safety rules for bash/Python blocks inside skills are in CLAUDE.md → **Shell Safety**. Copy those blocks exactly; never rewrite `jq` with `!=` from memory.
```

- [ ] **Step 4: CI, pre-push hook, gitignore**

Replace `.github/workflows/lint.yml` job steps after checkout with:

```yaml
      - name: Unit tests
        run: python3 -m unittest discover -s tests -v

      - name: Check Automatis skills and manifests
        run: ./scripts/vendor-automatis-commands --check
```

Remove the old inline JSON-only steps; `--check` already parses both JSON files and verifies `./automatis`.

Create `.githooks/pre-push`:

```bash
#!/bin/sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
python3 -m unittest discover -s tests -v
exec ./scripts/vendor-automatis-commands --check
```

```bash
chmod +x .githooks/pre-push
```

Add to `.gitignore`:

```
.gitworktrees/
```

Document in CLAUDE.md (already in Step 3) that contributors run `git config core.hooksPath .githooks`.

- [ ] **Step 5: Verify and commit**

```bash
python3 -m unittest discover -s tests -v
```

```bash
./scripts/vendor-automatis-commands --check
```

```bash
python3 -c "import json; json.load(open('.claude-plugin/marketplace.json')); json.load(open('automatis/.claude-plugin/plugin.json'))"
```

```bash
git config core.hooksPath .githooks
```

```bash
.githooks/pre-push
```

Expected: tests PASS, `--check` exits 0, hook exits 0.

Confirm skills do not still tell the model to run the colon form:

```bash
grep -R '/automatis:' automatis/skills
```

Expected: grep exits 1 (no matches). README/CLAUDE.md may mention `/automatis:fix-pr` only as a retired name.

```bash
git add README.md CLAUDE.md AGENTS.md automatis/.claude-plugin/plugin.json .claude-plugin/marketplace.json .github/workflows/lint.yml .githooks/pre-push .gitignore
```

```bash
git commit -m "$(cat <<'EOF'
Document multi-harness commands and enforce --check on push

README, CLAUDE.md, and AGENTS.md describe /automatis-<name> and the
vendor script. CI and .githooks/pre-push run the same checks.
EOF
)"
```

---

## Self-review

**Spec coverage**

| Spec section | Task |
|--------------|------|
| Goal / invocation table | 4 (skill text), 5 (docs) |
| Canonical skills layout | 4 |
| No `automatis/commands/` | 3 (`--check`), 4 (delete) |
| Skill frontmatter rules | 1, 4 |
| Generated Claude command shape | 2 |
| Vendor destinations + manifest | 2 |
| `--dry-run`, `--prune`, refuse self/missing | 2, 3 |
| `--check` rules | 3, 4 |
| Marketplace stays, skills-only plugin | 4, 5 |
| Breaking colon slash | 4, 5 |
| README / CLAUDE.md / AGENTS.md | 5 |
| Adding/deleting a command | 5 |
| CI `--check` | 5 |
| `.githooks/pre-push` | 5 |
| Implementation scope = this repo | all; smoke vendor uses `/tmp` |
| Error table | 1–3 |
| git-cleanup in README | 5 |
| plugin/marketplace blurbs | 5 |

**Out of scope (no task on purpose):** Gemini toml, extra harness dirs, submodules, repo rename, user-global installs, colon aliases, vendoring named product repos.

**Placeholder scan:** none.

**Type consistency:** `Skill`, `FrontmatterError`, `SkillError`, `parse_frontmatter`, `discover_skills`, `load_skill`, `load_skills`, `render_claude_command`, `vendor`, `check_repo`, `main`, `SOURCE_REPO`, `COMMAND_KEYS`, `MANIFEST_NAME` are named the same in Tasks 1–3.
