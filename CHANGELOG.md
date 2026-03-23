# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Wave 5: Polish, edge case hardening, documentation finalization

## [0.1.0] - 2026-03-24

### Added
- **JSONL Parser** (`cctree/parser.py`): reads Claude Code session files, filters to user/assistant messages, extracts content previews from text/tool_use/tool_result blocks, skips thinking blocks
- **Tree Builder** (`cctree/tree.py`): TreeNode dataclass with uuid/parentUuid linkage, sidechain detection, orphan handling, timestamp-sorted children, ancestor chain computation
- **Interactive TUI** (`cctree/renderer.py`): Textual-based tree navigator with color-coded nodes (cyan/green/yellow), arrow keys + hjkl vim bindings, expand/collapse, action menu modal, overwrite confirmation with descendant count
- **Fork Operation** (`cctree/actions.py`): creates new session JSONL with ancestor chain up to selected node, generates new session UUID, preserves interleaved snapshots
- **Overwrite Operation** (`cctree/actions.py`): creates timestamped backup, truncates JSONL to ancestor chain, cleans up orphaned entries
- **CLI** (`cctree/cli.py`, `__main__.py`): session auto-detection from ~/.claude/sessions/, --session-file/--session-id/--stats/--output-only flags, Windows Unicode support
- **Slash Command** (`commands/tree.md`): registers `/tree` in Claude Code with session argument support
- **Skill Definition** (`skills/conversation-tree/SKILL.md`): non-forked skill with workflow instructions for session resolution, TUI launch, and result processing
- **Install Script** (`install.sh`): symlinks command, skill, and cctree package into ~/.claude/ with dependency installation, --check and --uninstall modes
- **Test Suite**: 52 tests covering parser, tree builder, fork, overwrite, content extraction, sidechain handling, orphan recovery, edge cases

## [0.0.1] - 2026-03-24

### Added
- Project specification (SPEC.md) with user stories, acceptance criteria, and scope boundaries
- Architecture and design document (DESIGN.md) with three-layer architecture, component design, and technology choices
- Implementation plan (PLAN.md) with 5 waves, 16 tasks, and dependency graph
- Project scaffolding: pyproject.toml, requirements.txt, .gitignore, LICENSE (MIT)
- README with project overview, architecture summary, and installation instructions

[Unreleased]: https://github.com/SarthakB11/claude-code-tree/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/SarthakB11/claude-code-tree/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/SarthakB11/claude-code-tree/releases/tag/v0.0.1
