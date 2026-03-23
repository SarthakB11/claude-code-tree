---
name: conversation-tree
description: |
  Interactive conversation tree navigation with fork and overwrite capabilities.
  Renders the current session as a navigable tree in the terminal, allowing the
  user to fork new branches or rewind to any message point.

  Use when: "show tree", "conversation tree", "navigate history", "fork from",
  "rewind to", "branch conversation", "/tree"
version: 1.0.0
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

Allow users to visualize their Claude Code conversation as an interactive tree, navigate to any message, and either fork a new branch or rewind (overwrite) from that point.

## Operator Context

### Hardcoded Behaviors (Always Apply)
- **Always create backups** before overwrite operations
- **Never modify session files** without user confirmation
- **Auto-detect session** when no explicit session ID is provided
- **Sidechain collapsed by default** — show one-liner summaries, expand on request

### Workflow

1. **Resolve session**: Determine which session JSONL to visualize
   - Check if user provided a session ID
   - Otherwise find the most recent session for the current project directory
   - Session files live at `~/.claude/projects/{projectId}/{sessionId}.jsonl`

2. **Launch TUI**: Invoke the cctree tool via Bash
   ```bash
   python -m cctree --session-file <path> --output-only
   ```

3. **Process result**: Parse the JSON output and take action
   - `fork`: New session file was created — report the path and suggest `claude --resume`
   - `overwrite`: Session was truncated with backup — report what was removed and backup location
   - `cancel`: No action needed

### User Interaction Patterns

**Basic usage:**
```
User: /tree
→ Launches TUI for current session
```

**With specific session:**
```
User: /tree --session abc-123
→ Launches TUI for session abc-123
```

**After fork:**
```
→ "New branch created: session def-456"
→ "Resume with: claude --resume def-456"
```

**After overwrite:**
```
→ "Removed 12 messages after the selected point"
→ "Backup saved to: session.jsonl.bak.20260324_120000"
→ "Resume with: claude --resume current-session"
```

## Error Handling

- **No session found**: Suggest using `--session-file` or `--session-id` flags
- **Empty session**: Inform user that the session has no messages to display
- **cctree not installed**: Guide user to run the install script
- **Textual not installed**: Guide user to `pip install textual`
