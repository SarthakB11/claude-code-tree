# cctree — Claude Code Conversation Tree Navigator

Visualize Claude Code conversations as a tree. Fork new branches or rewind to any point in your history.

## The Problem

Claude Code conversations are linear. When a conversation takes a wrong turn, there's no way to see the structure, navigate to a past message, or branch off to explore an alternative. The built-in `/fork` and `/rewind` work but are blind — no visual tree, no context.

## What This Does

### Inside Claude Code (inline mode)

Type `/tree` in any Claude Code session:

```
/tree

Session: 19aac04e-...
Messages: 20 (10 user, 10 assistant)

  1. [U] You: I want to build a REST API for a todo app...     (uuid:u1)
  2. [A] Claude: I'd recommend Python+FastAPI or Node+Express...  (uuid:a1)
  3. [U] You: Let's go with Python + FastAPI                     (uuid:u2)
  4. [A] Claude: Let me set up the project structure...           (uuid:a2)
  ...
  8. [A] Claude: Basic CRUD API is ready...                       (uuid:a4)  <-- fork here?
  9. [S] Subagent: Database research... [+collapsed]              (uuid:s1)
 10. [U] You: Add JWT auth first                                  (uuid:u5)
  ...

> "fork from 8"
> Fork created! Switch with: /resume <new-session-id>
```

- Claude renders the tree inline, you pick a node by number or content
- **Fork**: creates a new session, switch with `/resume <id>`
- **Rewind**: Claude tells you to use built-in `/rewind` (handles code restoration too)

### Standalone TUI (terminal mode)

Full interactive keyboard-driven tree navigator:

```bash
python -m cctree --session-file path/to/session.jsonl
```

| Key | Action |
|-----|--------|
| `↑↓` / `jk` | Navigate between nodes |
| `←→` / `hl` | Collapse/expand, parent/child |
| `Enter` | Open action menu |
| `f` | Fork from selected message |
| `o` | Overwrite (truncate after selected) |
| `Space` | Toggle expand/collapse |
| `q` / `Esc` | Quit |

Color-coded: cyan (user), green (assistant), yellow (sidechains). Fork and overwrite execute inside the TUI with result notification before exit.

## Installation

```bash
git clone https://github.com/SarthakB11/claude-code-tree.git
cd claude-code-tree
./install.sh
```

The install script copies the `/tree` command, skill, and cctree package into `~/.claude/`. Verify with `./install.sh --check`. Remove with `./install.sh --uninstall`.

Requires Python 3.10+ and [Textual](https://textual.textualize.io/).

## CLI Reference

```bash
# Inline tree (for Claude Code skill integration)
python -m cctree --render-text --session-file <path>

# Non-interactive fork
python -m cctree --fork <node-uuid> --session-file <path>

# Non-interactive overwrite
python -m cctree --overwrite <node-uuid> --session-file <path>

# Tree statistics (JSON)
python -m cctree --stats --session-file <path>

# Interactive TUI
python -m cctree --session-file <path>

# Auto-detect current session
python -m cctree
```

## Architecture

```
/tree (Claude Code)           Standalone TUI
      |                             |
      v                             v
  Skill renders tree         Textual interactive app
  inline in conversation     with keyboard navigation
      |                             |
      v                             v
  python -m cctree           python -m cctree
  --render-text / --fork     (default TUI mode)
      |                             |
      +----------+------------------+
                 |
                 v
        cctree Python package
        parser.py  - JSONL parsing, content filtering
        tree.py    - Tree data structure, node operations
        actions.py - Fork (new session) & overwrite (backup + truncate)
        cli.py     - Arg parsing, session auto-detection
```

## Project Structure

```
cctree/
  __init__.py              # Package version
  __main__.py              # Entry point
  cli.py                   # Argument parsing, session discovery
  parser.py                # JSONL parsing, conversation turn filtering
  tree.py                  # Tree data structure, node operations
  renderer.py              # Textual TUI (tree widget, modals, keybindings)
  actions.py               # Fork and overwrite with advisory locking
commands/
  tree.md                  # Claude Code slash command
skills/
  conversation-tree/
    SKILL.md               # Claude Code skill definition
tests/                     # 72 tests
  test_parser.py           # Parser, content preview, filtering
  test_tree.py             # Tree builder, nodes, traversal
  test_actions.py          # Fork, overwrite, backup integrity
  test_conversation_turns.py  # Compact filtering, CLI modes, edge cases
  fixtures/
    sample_session.jsonl   # Test fixture with sidechains and branches
```

## How It Works

Claude Code stores conversations as JSONL with `uuid` / `parentUuid` fields forming a natural tree:

```jsonl
{"uuid": "abc", "parentUuid": null,  "type": "user",      "message": {"role": "user", "content": "..."}}
{"uuid": "def", "parentUuid": "abc", "type": "assistant",  "message": {"role": "assistant", "content": "..."}}
```

cctree reads this structure, filters to meaningful conversation turns (skipping tool_use/tool_result noise), builds the tree, and lets you navigate and branch from any point.

**Fork** creates a new JSONL with the ancestor chain up to the selected node. **Overwrite** creates a timestamped backup, then truncates the JSONL.

## License

MIT
