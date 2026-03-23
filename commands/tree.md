---
description: "Navigate conversation history as an interactive tree — fork or rewind from any message"
argument-hint: "[--session <id>]"
allowed-tools: ["Read", "Bash", "Grep", "Glob"]
---

# /tree — Conversation Tree Navigator

Launch an interactive tree view of the current conversation session. Navigate with arrow keys, fork new branches, or rewind to any message.

## Instructions

### Step 1: Resolve the session

- If the user provided `--session <id>`, use that session ID
- Otherwise, auto-detect the current session by finding the most recent `.jsonl` file for this project in `~/.claude/projects/`

### Step 2: Launch the TUI

Run the cctree TUI tool:

```bash
python -m cctree --session-file <path-to-session.jsonl> --output-only
```

If `--session <id>` was given:
```bash
python -m cctree --session-id <id> --output-only
```

The `--output-only` flag ensures the tool outputs a JSON result for you to process.

### Step 3: Process the result

The TUI will output JSON like:
```json
{
  "action": "fork",
  "node_uuid": "abc-123",
  "session_id": "current-session-id",
  "session_file": "/path/to/session.jsonl"
}
```

Handle based on `action`:

- **`fork`**: A new session JSONL has been created. Inform the user of the new session ID and suggest they resume it with `claude --resume <new-session-id>`.
- **`overwrite`**: The session has been truncated with a backup created. Inform the user that messages after the selected point have been removed and a backup was saved.
- **`cancel`**: User exited without action. No message needed.

### Step 4: Auto-switch (for fork)

If the action was `fork`, suggest the user start a new Claude session with the forked conversation:
```
claude --resume <new-session-id>
```
