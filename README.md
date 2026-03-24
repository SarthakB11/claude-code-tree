# cctree

**Conversation tree navigator for Claude Code** — visualize, fork, and rewind your AI coding sessions.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests: 72 passing](https://img.shields.io/badge/tests-72%20passing-brightgreen.svg)](#)
[![Version: 0.2.0](https://img.shields.io/badge/version-0.2.0-orange.svg)](CHANGELOG.md)

---

Claude Code conversations are linear. When a conversation takes a wrong turn, there's no way to see the structure, navigate to a past message, or branch off to try something different. The built-in `/fork` and `/rewind` work but are blind — no visual tree, no context about where you are.

**cctree** reads Claude Code's session files, builds a conversation tree from the `uuid`/`parentUuid` chain, and lets you fork new branches or rewind from any point.

## How It Works

### Inside Claude Code

Type `/tree` in any session. Claude renders your conversation as a numbered tree:

```
  1. [U] You: I want to build a REST API for a todo app...
  2. [A] Claude: I'd recommend Python+FastAPI or Node+Express...
  3. [U] You: Let's go with Python + FastAPI
  4. [A] Claude: Let me set up the project structure...
     ...
  8. [A] Claude: Basic CRUD API is ready...                   <-- fork here
  9. [S] Subagent: Database research... [+collapsed]
 10. [U] You: Add JWT auth first
     ...

> "fork from 8"
> Fork created! Switch with: /resume abc-123-def
```

- Say **"fork from 8"** (or reference by content) to branch from any message
- New session created instantly — switch with `/resume <id>`
- For rewinding, Claude suggests the built-in `/rewind` which also restores code

### Standalone Terminal UI

Full keyboard-driven tree navigator using [Textual](https://textual.textualize.io/):

```bash
python -m cctree --session-file path/to/session.jsonl
```

| Key | Action |
|-----|--------|
| `↑↓` / `jk` | Navigate nodes |
| `←→` / `hl` | Collapse/expand |
| `f` | Fork from selected |
| `o` | Overwrite (truncate) |
| `Enter` | Action menu |
| `q` | Quit |

Color-coded nodes: **cyan** (user), **green** (assistant), **yellow** (sidechains). Sidechains collapsed by default. Fork and overwrite execute inside the TUI with a confirmation screen.

## Installation

```bash
git clone https://github.com/SarthakB11/claude-code-tree.git
cd claude-code-tree
./install.sh
```

This copies the `/tree` command, skill, and cctree package into `~/.claude/`.

```bash
./install.sh --check      # verify installation
./install.sh --uninstall   # remove
```

**Requirements:** Python 3.10+, [Textual](https://textual.textualize.io/) (auto-installed)

## CLI Reference

```bash
python -m cctree --render-text --session-file <path>   # inline numbered tree
python -m cctree --fork <uuid> --session-file <path>   # fork at node
python -m cctree --overwrite <uuid> --session-file <path>  # truncate at node
python -m cctree --stats --session-file <path>         # JSON statistics
python -m cctree --session-file <path>                 # interactive TUI
python -m cctree                                       # auto-detect session
```

## Architecture

```
Claude Code (/tree)              Standalone
      |                              |
      v                              v
  Skill: render tree            Textual TUI
  inline, user picks node       keyboard navigation
      |                              |
      v                              v
  --render-text / --fork        default TUI mode
      |                              |
      +-------------+----------------+
                    |
                    v
           cctree Python package
           parser.py   JSONL parsing, conversation turn filtering
           tree.py     Tree data structure, uuid/parentUuid linkage
           actions.py  Fork (new session) & overwrite (backup + truncate)
           renderer.py Textual TUI with modals and keybindings
           cli.py      Arg parsing, session auto-detection
```

**Key design decisions:**
- Conversation turns filtered to skip tool_use/tool_result noise (623 raw messages → 149 readable turns)
- Fork creates a new JSONL with the ancestor chain; original untouched
- Overwrite creates a timestamped backup before truncation
- Cross-platform advisory file locking on destructive operations

## Data Model

Claude Code stores conversations as JSONL with natural tree structure:

```jsonl
{"uuid": "abc", "parentUuid": null,  "type": "user",      "message": {...}, "isSidechain": false}
{"uuid": "def", "parentUuid": "abc", "type": "assistant",  "message": {...}, "isSidechain": false}
{"uuid": "ghi", "parentUuid": "abc", "type": "user",      "message": {...}, "isSidechain": true, "agentId": "..."}
```

Session files live at `~/.claude/projects/{projectId}/{sessionId}.jsonl`.

## Project Structure

```
cctree/                          # Python package (6 modules)
  __init__.py  __main__.py  cli.py  parser.py  tree.py  renderer.py  actions.py
commands/tree.md                 # Claude Code /tree slash command
skills/conversation-tree/SKILL.md  # Skill definition for inline mode
tests/                           # 72 tests across 4 files
  test_parser.py  test_tree.py  test_actions.py  test_conversation_turns.py
```

## Documentation

| Document | Purpose |
|----------|---------|
| [SPEC.md](SPEC.md) | User stories, acceptance criteria, scope boundaries |
| [DESIGN.md](DESIGN.md) | Architecture, component design, technology choices |
| [PLAN.md](PLAN.md) | Implementation waves, task breakdown, agent assignments |
| [CHANGELOG.md](CHANGELOG.md) | Version history following Keep a Changelog |

## Contributing

This project was built as a Claude Code extension. To develop:

```bash
git clone https://github.com/SarthakB11/claude-code-tree.git
cd claude-code-tree
pip install -r requirements.txt
pip install pytest
python -m pytest tests/ -v        # run tests
python -m cctree --help           # see CLI options
```

## License

[MIT](LICENSE)
