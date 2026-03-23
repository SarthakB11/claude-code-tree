# PLAN: Claude Code Conversation Tree Navigator

**Status:** Active
**Phase:** 2 — Plan (spec -> design -> plan -> implement -> validate -> release)
**Date:** 2026-03-24
**Spec:** [SPEC.md](./SPEC.md) | **Design:** [DESIGN.md](./DESIGN.md)

---

## Implementation Waves

Tasks are ordered by dependency. Each wave can be worked on once the previous wave is complete.

---

### Wave 1: Core Data Layer

Foundation — parse JSONL, build tree structure, no UI yet.

#### Task 1.1: JSONL Parser (`cctree/parser.py`)
- Read a session JSONL file line by line
- Deserialize each line to a dict
- Filter: keep only `type == "user"` and `type == "assistant"` entries
- Handle malformed lines gracefully (skip + warn to stderr)
- Return list of parsed entries
- **Test:** `tests/test_parser.py` with `tests/fixtures/sample_session.jsonl`

#### Task 1.2: Tree Builder (`cctree/tree.py`)
- Define `TreeNode` dataclass (uuid, parent_uuid, role, content_preview, timestamp, is_sidechain, children, raw_entry, expanded, selected)
- Build tree from parsed entries using `uuid` / `parentUuid` linkage
- Generate content preview (first 80 chars, strip newlines)
- Handle missing `parentUuid` (treat as root)
- Handle orphaned nodes (parent not found — attach to root)
- Generate sidechain one-liner summaries
- **Test:** `tests/test_tree.py` — tree construction, orphan handling, sidechain summary

#### Task 1.3: CLI Entry Point (`cctree/cli.py`, `cctree/__main__.py`, `cctree/__init__.py`)
- `argparse` setup: `--session-file <path>` (required for now, session discovery comes later)
- `--session-id <id>` optional override
- Entry point that parses args, calls parser, builds tree
- `__main__.py` with `main()` function for `python -m cctree`
- No UI yet — just prints tree stats to verify pipeline works

---

### Wave 2: Terminal UI

Interactive tree rendering with Textual.

#### Task 2.1: Tree Renderer (`cctree/renderer.py`)
- Textual `App` subclass: `CCTreeApp`
- Layout: header (session info), tree panel (main area), detail footer (selected node info + keybindings)
- Populate Textual `Tree` widget from `TreeNode` structure
- Color coding: cyan for user `[U]`, green for assistant `[A]`, yellow for sidechain `[S]`
- Content preview as node label
- Sidechains collapsed by default

#### Task 2.2: Keyboard Navigation
- Arrow keys + `hjkl` vim bindings for tree traversal
- `Enter` opens action menu (fork / overwrite / cancel)
- `f` quick-fork, `o` quick-overwrite
- `q` / `Esc` exits with cancel action
- Focus management between tree and action menu

#### Task 2.3: Action Menu
- Modal overlay when user presses Enter or action key on a node
- Three options: Fork, Overwrite, Cancel
- Overwrite shows confirmation: "This will remove N messages. Are you sure? [y/N]"
- On selection, app exits and outputs action JSON to stdout

#### Task 2.4: Session Discovery
- Auto-detect current session: read `~/.claude/sessions/` to find the active session for the current project
- Match by `cwd` field in session metadata files
- Fallback to most recent session for the project
- `--session-file` flag overrides auto-detection
- Integrate with CLI args from Task 1.3

---

### Wave 3: Fork & Overwrite Operations

The action layer — executed by the skill, but we build the logic as reusable Python functions.

#### Task 3.1: Fork Operation (`cctree/actions.py`)
- `fork_session(session_file, node_uuid) -> new_session_path`
- Walk ancestor chain from selected node to root
- Collect all entries on that path (including interleaved progress/snapshot entries)
- Generate new session UUID
- Write new JSONL file with updated `sessionId`
- Copy relevant file-history entries
- Return path to new session file

#### Task 3.2: Overwrite Operation (`cctree/actions.py`)
- `overwrite_session(session_file, node_uuid) -> backup_path`
- Create timestamped backup of original JSONL
- Compute set of entries to keep (selected node + all ancestors)
- Remove all descendant entries after the selected node
- Write filtered entries back to original file
- Clean up orphaned file-history snapshots
- Return path to backup file

#### Task 3.3: Action Output Contract
- Unify TUI exit with action JSON output
- `{"action": "fork|overwrite|cancel", "node_uuid": "...", "session_id": "...", "session_file": "..."}`
- When run standalone (`python -m cctree`), execute the action directly and print result
- When run from skill, output JSON only (skill handles execution) — controlled by `--output-only` flag

---

### Wave 4: Claude Code Integration

Connect everything to Claude Code's extension system.

#### Task 4.1: Slash Command (`commands/tree.md`)
- Command definition with YAML frontmatter
- Instructions for Claude to resolve session, invoke `python -m cctree`, process result

#### Task 4.2: Skill Definition (`skills/conversation-tree/SKILL.md`)
- Non-forked skill (needs interactive context)
- Workflow: resolve session -> invoke TUI -> parse action JSON -> execute fork/overwrite -> auto-switch session
- Error handling guidance for skill

#### Task 4.3: Install Script (`install.sh`)
- Symlink `cctree/` to `~/.claude/scripts/cctree/`
- Symlink `commands/tree.md` to `~/.claude/commands/tree.md`
- Symlink `skills/conversation-tree/` to `~/.claude/skills/conversation-tree/`
- Install Python dependencies
- Verify Python 3.10+ and Textual available

---

### Wave 5: Polish & Validation

#### Task 5.1: Test Suite
- Unit tests for parser (malformed JSONL, empty file, large file)
- Unit tests for tree builder (orphans, sidechains, single node, deep nesting)
- Unit tests for fork/overwrite (verify JSONL integrity, backup creation)
- Integration test: full pipeline with sample session fixture

#### Task 5.2: Edge Cases & Hardening
- Empty conversation handling
- Very long messages (truncation)
- Binary/image content placeholders
- Concurrent write protection (advisory lock on JSONL during overwrite)
- Corrupted JSONL recovery

#### Task 5.3: Documentation
- Update README with final usage examples and screenshots/recordings
- Inline code comments for non-obvious logic
- CHANGELOG.md for v0.1.0

---

## Agent Assignments

| Task | Primary Agent | Notes |
|------|--------------|-------|
| 1.1-1.3 | python-general-engineer | Pure Python, data parsing, no UI |
| 2.1-2.4 | typescript-frontend-engineer + ui-design-engineer | Textual is Python but UI design principles apply |
| 3.1-3.3 | python-general-engineer | File I/O, JSONL manipulation |
| 4.1-4.2 | hook-development-engineer | Claude Code integration expertise |
| 4.3 | python-general-engineer | Shell scripting |
| 5.1-5.3 | testing-automation-engineer | Test design and coverage |

## Dependency Graph

```
Wave 1 (data) ──> Wave 2 (UI) ──> Wave 3 (actions) ──> Wave 4 (integration)
                                                              │
                                                              v
                                                       Wave 5 (polish)
```

Wave 1 is fully independent. Wave 2 depends on Wave 1. Wave 3 depends on Wave 1 (not Wave 2 — actions can be tested without UI). Wave 4 depends on Waves 2+3. Wave 5 depends on all.
