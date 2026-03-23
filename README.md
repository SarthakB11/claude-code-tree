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
```

```
  [U] You: "I want to create a CLI extension..."
  └─[A] Claude: "Let me look up that repository..."
    └─[U] You: "Now here's my idea..."
      ├─[A] Claude: "Great idea. Let me scan..."     <-- you are here
      │ └─[U] You: "I prefer CLI..."
      └─[S] Subagent: "Explored session storage..." [expand]
```

- **Arrow keys** (or `hjkl`) to navigate the tree
- **`f`** to fork a new branch from any message
- **`o`** to rewind (truncate everything after a message)
- **Sidechains** shown as collapsed one-liners, expandable inline
- **Auto-switch** to forked sessions immediately

## Architecture

Three-layer design:

1. **Slash Command** (`/tree`) — entry point registered in Claude Code
2. **Skill** (orchestrator) — resolves session, invokes TUI, processes the returned action
3. **Python TUI** (`cctree`) — standalone Textual app that reads session JSONL, renders the interactive tree, returns user's decision as JSON

The TUI is read-only. All JSONL manipulation (fork/truncate) happens in the skill layer.

## Installation

```bash
git clone https://github.com/SarthakB11/claude-code-tree.git
cd claude-code-tree
pip install -r requirements.txt
./install.sh    # symlinks command, skill, and cctree into ~/.claude/
```

## Requirements

- Python 3.10+
- [Textual](https://textual.textualize.io/) (installed via requirements.txt)
- Claude Code CLI

## Project Status

| Phase | Status |
|-------|--------|
| Specification | Done |
| Design | Done |
| Implementation Plan | In Progress |
| Implementation | Not Started |
| Validation | Not Started |

## How It Works (Data Model)

Claude Code already stores conversations with a tree-compatible structure:

```jsonl
{"uuid": "abc-123", "parentUuid": null,      "type": "user",      "message": {"role": "user", "content": "..."}}
{"uuid": "def-456", "parentUuid": "abc-123",  "type": "assistant", "message": {"role": "assistant", "content": "..."}}
```

Each message has a `uuid` and `parentUuid`, forming a natural tree. Subagent conversations are stored in separate files with `isSidechain: true`. This tool reads that structure and renders it interactively.

## License

MIT
