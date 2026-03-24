---
name: tree
description: |
  Visualize the current conversation as a numbered tree and fork or rewind
  from any message. Shows user/assistant messages with sidechains. Use when:
  "show tree", "conversation tree", "fork from", "rewind to", "branch from",
  "go back to message", "/tree"
disable-model-invocation: true
allowed-tools:
  - Bash
  - Read
---

# /tree — Conversation Tree Navigator

Visualize the current session as a tree. Fork new branches or rewind to any point.

## Step 1: Show the tree

Run this command to display the numbered conversation tree inline:

```bash
python -m cctree --render-text --session-file !`ls -t ~/.claude/projects/$(python -c "import os; p=os.getcwd().replace(':\\\\','--').replace('\\\\','-').replace('/','-'); print(p)")/*.jsonl | head -1`
```

Present the tree output to the user. Each node has a number and UUID.

## Step 2: Ask the user what to do

Ask the user which message they want to act on. They can reference by:
- Number: "fork from 5"
- Content: "fork from the message about auth"
- UUID: "fork from abc-123"

Then ask what action:
- **Fork**: Create a new conversation branch from that point
- **Rewind**: Use the built-in `/rewind` command instead (tell the user to type `/rewind`)

## Step 3: Execute fork

If the user wants to fork, extract the node UUID from the tree output and run:

```bash
python -m cctree --fork <NODE_UUID> --session-file <SAME_PATH_FROM_STEP_1>
```

This outputs JSON with the new session ID:
```json
{"action": "fork", "new_session_id": "abc-123", "new_session_file": "..."}
```

Tell the user the fork was created and instruct them to switch:

> **Fork created!** To switch to the new branch, type:
> `/resume <new_session_id>`

## Step 4: For rewind/overwrite

If the user wants to rewind (remove messages after a point), tell them to use the built-in `/rewind` command which handles this natively with code restoration:

> To rewind to that point, type `/rewind` and select the message.
> This will also restore any code changes made after that point.

The built-in `/rewind` is better than our overwrite because it also handles file checkpoints.

## Important Notes

- Fork creates a NEW session. The current session is untouched.
- After forking, the user MUST type `/resume <id>` to switch to it.
- For rewind, always prefer the built-in `/rewind` over our `--overwrite`.
- The `--render-text` output includes UUIDs for each node — use these for `--fork`.
