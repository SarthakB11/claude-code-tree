---
description: "Navigate conversation history as an interactive tree — fork or rewind from any message"
argument-hint: "[--session <id>]"
allowed-tools: ["Read", "Bash", "Grep", "Glob"]
---

# /tree — Conversation Tree Navigator

Launch an interactive tree view of the current conversation session. Navigate with arrow keys, fork new branches, or rewind to any message.

## Instructions

### Step 1: Resolve the session file

- If the user provided `--session <id>`, find the JSONL file for that session ID
- Otherwise, auto-detect by finding the most recent `.jsonl` file for this project in `~/.claude/projects/`

To find the project directory, convert the current working directory to a Claude Code project ID:
- Replace `:\` with `--`, then all `\` and `/` with `-`
- Example: `C:\Users\sarth\Documents\project` becomes `C--Users-sarth-Documents-project`
- Session files are at: `~/.claude/projects/{projectId}/{sessionId}.jsonl`

Use Bash to list and find the most recent session file:
```bash
ls -t ~/.claude/projects/{projectId}/*.jsonl | head -1
```

### Step 2: Ask the user to launch the TUI

IMPORTANT: The TUI requires direct terminal access for keyboard navigation. It CANNOT be launched via the Bash tool (which runs in a pipe without TTY). Instead, present the user with the exact command to run using the `!` prefix.

Tell the user:
```
Run this command to open the interactive tree:

! python -m cctree --session-file <resolved-path> --output-only
```

Explain the keyboard controls:
- Arrow keys or `hjkl` to navigate
- `Enter` for action menu, `f` to fork, `o` to overwrite
- `q` or `Esc` to quit

The `--output-only` flag makes the TUI print action JSON to stdout on exit, which will appear in this conversation for processing.

### Step 3: Wait for and process the result

After the user runs the command, the output will appear in the conversation as JSON:
```json
{
  "action": "fork",
  "node_uuid": "abc-123",
  "session_id": "current-session-id",
  "session_file": "/path/to/session.jsonl"
}
```

Handle based on `action`:

- **`fork`**: A new session JSONL was created. Tell the user the new session ID and that they can resume with `claude --resume <new-session-id>`.
- **`overwrite`**: The session was truncated with a backup. Tell the user that messages after the selected point were removed, and where the backup was saved.
- **`cancel`**: User exited without action. Acknowledge briefly.

### Step 4: Auto-switch (for fork)

If the action was `fork`, suggest the user start a new Claude session with the forked conversation:
```
! claude --resume <new-session-id>
```
