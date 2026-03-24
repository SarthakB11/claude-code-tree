# SPEC: Claude Code Conversation Tree Navigator

**Status:** Completed
**Phase:** Released (v0.2.0)
**Date:** 2026-03-24

---

## 1. Problem Statement

Claude Code conversations are linear and hard to navigate. When a conversation takes a wrong turn or the user wants to explore an alternative approach from a past message, there is no way to:
- Visualize the conversation as a tree/mind-map
- Navigate to a specific past message interactively
- Fork a new branch from any point in the conversation
- Overwrite/replace all messages after a chosen point

The existing `/fork` and `--fork-session` create independent sessions from a shared history point, but there is no tree view, no visual navigation, and no "fork vs overwrite" choice. GitHub issue #32631 confirms the community wants exactly this.

## 2. User Stories

### US-1: Visualize Conversation Tree
**As a** Claude Code CLI user
**I want to** see my current conversation rendered as an interactive tree in the terminal
**So that** I can understand the structure of my conversation, including branches and sidechains

**Acceptance Criteria:**
- Tree renders in the terminal with clear parent-child relationships
- User messages and assistant messages are visually distinct (color/icon)
- Each node shows a truncated preview of the message content
- Subagent sidechains (`isSidechain: true`) are visually differentiated
- Tree is navigable with keyboard arrow keys (up/down/left/right)
- Currently selected node is highlighted

### US-2: Navigate to a Specific Message
**As a** Claude Code CLI user
**I want to** use arrow keys to traverse the conversation tree and select any message
**So that** I can quickly find the exact point where I want to branch or review

**Acceptance Criteria:**
- Up/Down arrows move between sibling nodes
- Left arrow collapses/moves to parent
- Right arrow expands/moves to first child
- Enter key selects the current node
- `q` or Escape exits without action
- Node metadata (timestamp, role, token usage) shown in a detail pane

### US-3: Fork a New Branch from Any Message
**As a** Claude Code CLI user
**I want to** select a message in the tree and create a new conversation branch from that point
**So that** I can explore an alternative approach without losing the original conversation

**Acceptance Criteria:**
- After selecting a node, user is prompted: "Fork new branch from here?"
- Forking creates a new session that inherits all messages up to and including the selected node
- The new session is a valid Claude Code session (loadable with `--resume`)
- Original conversation remains untouched
- User is informed of the new session ID

### US-4: Overwrite (Truncate) from a Message
**As a** Claude Code CLI user
**I want to** select a message and discard everything after it
**So that** I can continue the conversation from that point as if the later messages never happened

**Acceptance Criteria:**
- After selecting a node, user can choose: "Overwrite — remove all messages after this point?"
- Confirmation required (destructive action)
- A backup of the original JSONL is created before truncation
- The session continues from the selected message
- File-history snapshots after the truncation point are cleaned up

### US-5: Invoke via Slash Command
**As a** Claude Code CLI user
**I want to** type `/tree` (or similar) to launch the conversation tree navigator
**So that** it's quick and discoverable

**Acceptance Criteria:**
- Custom slash command registered in `~/.claude/commands/`
- Command launches the TUI tree navigator for the current session
- Works from any project directory
- Falls back gracefully if no conversation exists yet

## 3. Out of Scope (v1)

These are explicitly NOT part of the initial version:

1. **Merge branches** — Combining two conversation branches back together (complex LLM summarization problem)
2. **Cross-session tree** — Visualizing trees across multiple sessions (v1 is single-session only)
3. **Web UI / Chrome extension** — This is CLI-only; web version is a separate project
4. **VS Code extension** — VS Code integration is a separate project
5. **Diff between branches** — Comparing two conversation paths side-by-side
6. **Collaborative/multi-user** — Single user, local machine only
7. **Real-time updates** — Tree is a snapshot at invocation time, not live-updating
8. **Editing message content** — Nodes are read-only in the tree view; only structure changes (fork/truncate) are supported
9. **Automatic branch suggestions** — No AI-powered "you should branch here" recommendations
10. **Persistent tree metadata** — No separate tree state file; tree is always computed from JSONL

## 4. Data Model (Existing — No Changes Needed)

Claude Code already stores conversations with tree-compatible structure:

```
{sessionId}.jsonl — one JSON object per line:
{
  "uuid": "...",           // unique node ID
  "parentUuid": "...",     // parent node ID (null for root)
  "type": "user|assistant|progress|file-history-snapshot",
  "isSidechain": false,    // true for subagent branches
  "timestamp": "ISO-8601",
  "sessionId": "...",
  "message": {
    "role": "user|assistant",
    "content": "string | array"
  }
}
```

**Key paths:**
- Session files: `~/.claude/projects/{projectId}/{sessionId}.jsonl`
- Subagents: `~/.claude/projects/{projectId}/{sessionId}/subagents/agent-{agentId}.jsonl`
- Session metadata: `~/.claude/sessions/{pid}.json`
- File history: `~/.claude/file-history/{sessionId}/`

## 5. Architecture (High-Level)

```
User types /tree
       |
       v
[Slash Command: tree.md]
       |
       v
[Skill: conversation-tree-explorer] (non-forked, interactive)
       |
       v
[Bash tool invokes external TUI script]
       |
       v
[Python TUI: mindmap-tui.py]
  - Reads current session JSONL
  - Builds tree from uuid/parentUuid
  - Renders interactive tree in terminal
  - User navigates with arrow keys
  - Returns selected node + action (fork/overwrite/cancel) as JSON to stdout
       |
       v
[Skill processes the action]
  - Fork: creates new session JSONL with messages up to selected node
  - Overwrite: backs up + truncates JSONL after selected node
  - Cancel: no-op
```

## 6. Technical Constraints

- **TUI library:** Python with `curses` (stdlib, no deps) or `textual` (richer but requires pip install)
- **Performance:** Must handle conversations with 500+ messages without lag
- **No terminal corruption:** TUI must cleanly restore terminal state on exit (even on crash)
- **Cross-platform:** Must work on Windows (Git Bash/MSYS2), macOS, Linux
- **Session integrity:** Fork/overwrite operations must produce valid JSONL that Claude Code can resume
- **Backup before destructive ops:** Always create `.bak` before overwriting

## 7. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| JSONL format changes in future Claude Code versions | Extension breaks silently | Version check field; validate schema on load |
| Large conversations (1000+ messages) render slowly | Bad UX | Lazy rendering, collapse by default, pagination |
| Windows terminal doesn't support curses well | Broken on user's platform | Use `windows-curses` package or `textual` which handles Windows |
| Forked session missing required fields | Claude Code can't resume it | Copy all fields verbatim; test with actual resume |
| Terminal state corruption on crash | User's terminal broken | atexit handler + try/finally for curses cleanup |

## 8. Success Metrics

- User can invoke `/tree`, see the tree, navigate with arrows, and fork/overwrite within 5 seconds for a typical conversation
- Zero data loss: original conversation always backed up before destructive operations
- Works on Windows (user's primary platform)

## 9. Resolved Questions

1. **Session discovery:** Auto-detect current session by default. Support explicit flag `/tree --session <id>` to pick a specific session (mirrors `claude --resume <id>` pattern).
2. **Node filtering:** Yes — hide `progress` and `file-history-snapshot` entries by default. Only show user/assistant message nodes in the tree.
3. **Subagent integration:** Show a one-liner summary inline in the tree for each sidechain. Toggle to expand and see full sidechain messages.
4. **Resume after fork:** Auto-switch to the new forked session immediately after creation.
