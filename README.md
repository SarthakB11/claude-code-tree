# cctree — Claude Code Conversation Tree Navigator

An interactive terminal UI for navigating Claude Code conversations as a tree. Fork new branches or rewind to any point in your conversation history.

## The Problem

Claude Code conversations are linear and hard to navigate. When a conversation takes a wrong turn, there's no way to:
- **See** your conversation structure at a glance
- **Navigate** to a specific past message
- **Fork** a new branch from any point to explore alternatives
- **Rewind** by truncating everything after a chosen message

The existing `/fork` and `--fork-session` are blind — no visual tree, no keyboard navigation, no "fork vs rewind" choice.

## What This Does

```
/tree                          # launch tree for current session
/tree --session <session-id>   # launch tree for a specific session
python -m cctree --help        # standalone CLI usage
```

```
  [U] You: "I want to create a CLI extension..."
  └─[A] Claude: "Let me look up that repository..."
    └─[U] You: "Now here's my idea..."
      ├─[A] Claude: "Great idea. Let me scan..."     <-- you are here
      │ └─[U] You: "I prefer CLI..."
      └─[S] Subagent: "Explored session storage..." [expand]
```

### Keyboard Controls

| Key | Action |
|-----|--------|
| `↑` `↓` / `j` `k` | Navigate between nodes |
| `←` `→` / `h` `l` | Collapse/expand, move to parent/child |
| `Enter` | Open action menu |
| `f` | Fork new branch from selected message |
| `o` | Overwrite (truncate after selected message) |
| `Space` | Toggle expand/collapse |
| `q` / `Esc` | Quit |

### Features

- Color-coded nodes: cyan (user), green (assistant), yellow (sidechains)
- Sidechains collapsed by default with one-liner summaries
- Overwrite confirmation with descendant count
- Automatic backup before destructive operations
- `--output-only` mode for Claude Code skill integration

## Installation

```bash
git clone https://github.com/SarthakB11/claude-code-tree.git
cd claude-code-tree
./install.sh
```

The install script:
1. Checks Python 3.10+ is available
2. Installs Textual dependency
3. Symlinks `/tree` command into `~/.claude/commands/`
4. Symlinks conversation-tree skill into `~/.claude/skills/`
5. Symlinks cctree package into `~/.claude/scripts/`

Verify with `./install.sh --check`. Uninstall with `./install.sh --uninstall`.

## Standalone Usage

Works independently of Claude Code:

```bash
# View tree stats
python -m cctree --session-file path/to/session.jsonl --stats

# Launch interactive TUI
python -m cctree --session-file path/to/session.jsonl

# Auto-detect current session
python -m cctree

# Output action JSON (for scripting)
python -m cctree --output-only
```

## Architecture

```
/tree command ──> Skill (orchestrator) ──> python -m cctree (TUI)
                                                  │
                                           Action JSON on exit
                                                  │
                                                  v
                                      Fork: new session JSONL
                                      Overwrite: backup + truncate
```

Three-layer design:

1. **Slash Command** (`/tree`) — entry point registered in Claude Code
2. **Skill** (orchestrator) — resolves session, invokes TUI, processes result
3. **Python TUI** (`cctree`) — standalone Textual app, returns decision as JSON

The TUI is read-only. All JSONL manipulation (fork/truncate) happens in the action layer.

## Project Structure

```
cctree/
  __init__.py       # Package version
  __main__.py       # Entry point (python -m cctree)
  cli.py            # Argument parsing, session discovery
  parser.py         # JSONL parsing, content preview extraction
  tree.py           # Tree data structure, node operations
  renderer.py       # Textual TUI (tree widget, modals, keybindings)
  actions.py        # Fork and overwrite operations
commands/
  tree.md           # Claude Code slash command definition
skills/
  conversation-tree/
    SKILL.md        # Claude Code skill definition
tests/
  test_parser.py    # 17 tests
  test_tree.py      # 22 tests
  test_actions.py   # 13 tests
  fixtures/
    sample_session.jsonl
```

## Requirements

- Python 3.10+
- [Textual](https://textual.textualize.io/) >= 0.50.0
- Claude Code CLI (for `/tree` slash command integration)

## Project Status

| Phase | Status |
|-------|--------|
| Specification | Done |
| Design | Done |
| Implementation Plan | Done |
| Core Data Layer (Wave 1) | Done |
| Terminal UI (Wave 2) | Done |
| Fork & Overwrite (Wave 3) | Done |
| Claude Code Integration (Wave 4) | Done |
| Polish & Validation (Wave 5) | In Progress |

## License

MIT
