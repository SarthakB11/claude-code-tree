---
name: conversation-tree
description: |
  Interactive conversation tree navigation with fork and overwrite capabilities.
  Renders the current session as a navigable tree in the terminal, allowing the
  user to fork new branches or rewind to any message point.

  Use when: "show tree", "conversation tree", "navigate history", "fork from",
  "rewind to", "branch conversation", "/tree"
version: 1.1.0
user-invocable: true
command: /tree
allowed-tools:
  - Read
  - Bash
  - Grep
  - Glob
routing:
  triggers:
    - show tree
    - conversation tree
    - navigate history
    - fork from
    - rewind to
    - branch conversation
    - tree view
  pairs_with:
    - resume-work
    - pause-work
  complexity: Simple
  category: navigation
---

# Conversation Tree Skill

## Purpose

Allow users to visualize their Claude Code conversation as an interactive tree, navigate to any message with keyboard controls, and either fork a new branch or rewind (overwrite) from that point.

## Operator Context

### Hardcoded Behaviors (Always Apply)
- **Always create backups** before overwrite operations
- **Never modify session files** without user confirmation
- **Auto-detect session** when no explicit session ID is provided
- **TUI requires direct terminal access** — present the user with a `! command` to run, do NOT attempt to launch via the Bash tool (it runs in a pipe without TTY)

### Workflow

1. **Resolve session**: Determine which session JSONL to visualize
   - Check if user provided a session ID
   - Otherwise find the most recent session for the current project directory
   - Session files live at `~/.claude/projects/{projectId}/{sessionId}.jsonl`
   - Convert cwd to project ID: replace `:\` with `--`, all `\` and `/` with `-`

2. **Present the TUI command**: Give the user the exact command to run with the `!` prefix:
   ```
   ! python -m cctree --session-file <resolved-path> --output-only
   ```
   Briefly explain: arrow keys/hjkl to navigate, `f` to fork, `o` to overwrite, `q` to quit.

3. **Wait for result**: The user runs the command. The TUI takes over their terminal with full keyboard control. On exit, action JSON appears in the conversation.

4. **Process result**: Parse the JSON output and take action
   - `fork`: New session file was created — report the path and suggest `! claude --resume <new-session-id>`
   - `overwrite`: Session was truncated with backup — report what was removed and backup location
   - `cancel`: Acknowledge briefly, no action needed

### User Interaction Flow

```
User: /tree

Claude: [resolves session path]
        Run this to open the interactive tree:
        ! python -m cctree --session-file ~/.claude/projects/.../session.jsonl --output-only

        Controls: ↑↓←→ or hjkl to navigate, f to fork, o to overwrite, q to quit

User: [runs the command, TUI opens, navigates, selects action, TUI exits]

[JSON output appears in conversation]

Claude: [processes the action — fork/overwrite/cancel]
```

### Keyboard Controls Reference
| Key | Action |
|-----|--------|
| ↑↓ / jk | Navigate between nodes |
| ←→ / hl | Collapse/expand, parent/child |
| Enter | Open action menu |
| f | Fork from selected message |
| o | Overwrite (truncate after selected) |
| Space | Toggle expand/collapse |
| q / Esc | Quit without action |

## Error Handling

- **No session found**: Suggest using `--session-file` or `--session-id` flags
- **Empty session**: Inform user that the session has no messages to display
- **cctree not installed**: Guide user to run `./install.sh` from the repo
- **Textual not installed**: Guide user to `pip install textual`
