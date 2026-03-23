# DESIGN: Claude Code Conversation Tree Navigator

**Status:** Draft
**Phase:** 1 — Design (spec -> design -> plan -> implement -> validate -> release)
**Date:** 2026-03-24
**Spec:** [SPEC.md](./SPEC.md)

---

## 1. System Architecture

```
                          User types /tree [--session <id>]
                                     |
                                     v
                    +--------------------------------+
                    |  Slash Command: tree.md         |
                    |  (registers /tree in Claude)    |
                    +--------------------------------+
                                     |
                                     v
                    +--------------------------------+
                    |  Skill: conversation-tree       |
                    |  (non-forked, orchestrator)     |
                    |  - Resolves session ID          |
                    |  - Invokes TUI via Bash         |
                    |  - Processes returned action     |
                    |  - Executes fork/overwrite      |
                    |  - Auto-switches session        |
                    +--------------------------------+
                                     |
                              Bash tool call
                                     |
                                     v
                    +--------------------------------+
                    |  Python TUI: cctree             |
                    |  (standalone terminal app)      |
                    |  - Parses JSONL session file    |
                    |  - Builds tree data structure   |
                    |  - Renders interactive tree     |
                    |  - Handles keyboard navigation  |
                    |  - Returns action JSON on exit  |
                    +--------------------------------+
                                     |
                              JSON on stdout
                                     |
                                     v
                    +--------------------------------+
                    |  Skill processes action:         |
                    |  - "fork": copy JSONL up to     |
                    |    selected node, create new    |
                    |    session, auto-switch          |
                    |  - "overwrite": backup + truncate|
                    |    JSONL after selected node     |
                    |  - "cancel": no-op              |
                    +--------------------------------+
```

## 2. Component Design

### 2.1 Slash Command — `tree.md`

**Location:** `~/.claude/commands/tree.md`

**Behavior:**
- Registers `/tree` in Claude Code's command discovery
- Accepts optional `--session <id>` argument
- Routes to the `conversation-tree` skill

```yaml
---
name: tree
description: "Explore conversation as an interactive tree — fork or overwrite from any message"
version: 1.0.0
---
```

The command markdown body instructs Claude to:
1. Determine the current session ID (from context or `--session` flag)
2. Locate the session JSONL file
3. Invoke the TUI script via Bash
4. Process the returned action

### 2.2 Python TUI — `cctree`

**Location:** `~/.claude/scripts/cctree/` (symlinked from repo)

This is the core interactive component. It's a standalone Python package.

#### 2.2.1 Module Structure

```
cctree/
  __init__.py
  __main__.py          # Entry point: python -m cctree
  cli.py               # Argument parsing
  parser.py            # JSONL parsing, tree construction
  tree.py              # Tree data structure and operations
  renderer.py          # Terminal UI rendering
  actions.py           # Fork/overwrite action output
```

#### 2.2.2 Tree Data Structure

```python
@dataclass
class TreeNode:
    uuid: str
    parent_uuid: str | None
    role: str                    # "user" | "assistant"
    content_preview: str         # First ~80 chars of message
    timestamp: datetime
    is_sidechain: bool
    sidechain_summary: str | None  # One-liner for collapsed sidechains
    children: list["TreeNode"]
    raw_entry: dict              # Full JSONL entry for fork/overwrite ops

    # UI state
    expanded: bool = True
    selected: bool = False
```

**Tree construction from JSONL:**
1. Read all lines from `{sessionId}.jsonl`
2. Filter: keep only `type == "user"` or `type == "assistant"`
3. Build lookup: `uuid -> TreeNode`
4. Link children via `parentUuid`
5. For `isSidechain` nodes: generate one-liner summary, set `expanded = False`
6. Also read `subagents/agent-{id}.jsonl` files if they exist, attach to parent tree

#### 2.2.3 Terminal Rendering

**Layout:**

```
+------------------------------------------------------------------+
| Claude Code Conversation Tree   Session: 19aac04e...  [q: quit]  |
+------------------------------------------------------------------+
|                                                                    |
|  [U] You: "I want to create a claude code extension..."           |
|  └─[A] Claude: "Let me look up that repository..."               |
|    └─[U] You: "Now I am giving you a thought I had..."           |
|      └─[A] Claude: "This is a great idea. Let me scan..."        |
|        ├─[U] You: "I prefer starting with CLI..."                 |
|        │ └─[A] Claude: "Good answers. Let me update..."          |
|        └─[S] Subagent: "Explored session storage..." [Enter: expand] |
|                                                                    |
+------------------------------------------------------------------+
| Node: You (2026-03-24 03:10:15)                                   |
| "I prefer starting with claude code cli extension..."             |
| [Enter: select]  [f: fork]  [o: overwrite]  [Esc: cancel]        |
+------------------------------------------------------------------+
```

**Visual elements:**
- `[U]` = User message (cyan)
- `[A]` = Assistant message (green)
- `[S]` = Sidechain summary (yellow, collapsed)
- Selected node: inverse/highlight colors
- Tree lines: Unicode box-drawing characters (├─, └─, │)

**Keyboard controls:**

| Key | Action |
|-----|--------|
| Up / k | Move selection to previous visible node |
| Down / j | Move selection to next visible node |
| Right / l | Expand collapsed node / move to first child |
| Left / h | Collapse node / move to parent |
| Enter | Open action menu for selected node |
| f | Quick-fork from selected node |
| o | Quick-overwrite from selected node |
| q / Esc | Exit without action |
| / | Search node content (stretch goal) |

**Action menu (after Enter on a node):**
```
+----------------------------------+
| Action on this message:          |
|                                  |
|  [f] Fork new branch from here  |
|  [o] Overwrite (truncate after)  |
|  [Esc] Cancel                    |
+----------------------------------+
```

#### 2.2.4 Output Contract

TUI exits and prints JSON to stdout:

```json
{
  "action": "fork" | "overwrite" | "cancel",
  "node_uuid": "ebaa407b-...",
  "session_id": "19aac04e-...",
  "session_file": "/path/to/{sessionId}.jsonl"
}
```

Exit codes:
- `0` = action selected (read JSON from stdout)
- `1` = error (stderr has message)
- `130` = user cancelled (Ctrl+C)

### 2.3 Fork Operation

**Performed by the skill (not the TUI).**

Steps:
1. Read the session JSONL
2. Walk the tree from root to the selected node, collecting all ancestor entries (including progress/snapshot entries between them for completeness)
3. Generate a new session UUID
4. Write a new JSONL file at `~/.claude/projects/{projectId}/{newSessionId}.jsonl`
5. Update all entries to reference the new `sessionId`
6. Copy relevant file-history snapshots up to that point
7. Auto-switch: instruct Claude to resume the new session

**Key detail:** We collect entries by walking `parentUuid` chain from selected node to root, then include ALL entries whose `parentUuid` chain leads to any node on that path. This preserves assistant tool_use/tool_result pairs that aren't directly in the uuid chain but are needed for a valid conversation.

### 2.4 Overwrite (Truncate) Operation

**Performed by the skill (not the TUI).**

Steps:
1. Create backup: copy `{sessionId}.jsonl` to `{sessionId}.jsonl.bak.{timestamp}`
2. Read all entries
3. Find the selected node's UUID
4. Keep: all entries that are the selected node or its ancestors (by `parentUuid` chain)
5. Remove: all entries that are descendants of the selected node
6. Write the filtered entries back to the original JSONL file
7. Clean up file-history snapshots that reference removed message IDs

## 3. Technology Choices

| Decision | Choice | Rationale |
|----------|--------|-----------|
| TUI library | `textual` (Python) | Rich widget library, works on Windows natively (no curses issues), tree widget built-in, modern async architecture. Falls back to `curses` only if textual unavailable. |
| Language | Python | Consistent with toolkit ecosystem (all hooks are Python), stdlib JSONL parsing, no build step |
| Entry point | `python -m cctree` | Standard Python package invocation, easy to symlink |
| Tree rendering | Textual's `Tree` widget | Built-in expand/collapse, keyboard nav, scrolling — exactly what we need |
| Argument parsing | `argparse` | Stdlib, no deps beyond textual |

### Why Textual over curses:
- **Windows support**: curses requires `windows-curses` and has rendering bugs on Windows Terminal. Textual works natively.
- **Tree widget**: Textual has a built-in `Tree` widget with expand/collapse, keyboard navigation, and scrolling — we'd have to build all of this from scratch with curses.
- **Rich text**: Color, bold, unicode box-drawing all work out of the box.
- **Modern**: Async event loop, CSS-like styling, responsive layout.

### Why not Node.js / Ink:
- The entire toolkit ecosystem is Python. Adding Node.js as a dependency breaks consistency.
- Textual's `Tree` widget is more mature than Ink's tree solutions.

## 4. File Layout (In This Repo)

```
claude-code-mindmap-visualizer/
  SPEC.md
  DESIGN.md
  PLAN.md                    # (next phase)
  cctree/                    # Python package
    __init__.py
    __main__.py
    cli.py
    parser.py
    tree.py
    renderer.py
    actions.py
  commands/
    tree.md                  # Slash command definition
  skills/
    conversation-tree/
      SKILL.md               # Skill definition
  install.sh                 # Symlinks cctree + command + skill into ~/.claude/
  requirements.txt           # textual
  pyproject.toml
  tests/
    test_parser.py
    test_tree.py
    fixtures/
      sample_session.jsonl   # Test data
```

## 5. Trade-offs & Alternatives Considered

### 5.1 TUI in skill vs external script
- **Chosen:** External Python script invoked via Bash
- **Alternative:** Pure skill-based text rendering (no TUI)
- **Why:** A real TUI with keyboard events requires terminal control. Skills communicate via text — they can't capture raw keystrokes. The external script approach cleanly separates concerns: TUI handles navigation, skill handles actions.

### 5.2 Textual vs curses vs blessed
- **Chosen:** Textual
- **Alternative:** curses (stdlib, no deps) or blessed (Node.js)
- **Why:** curses has poor Windows support and no built-in tree widget. blessed requires Node.js. Textual gives us a tree widget, Windows support, and stays in Python.

### 5.3 Fork in TUI vs fork in skill
- **Chosen:** TUI selects, skill executes
- **Alternative:** TUI does everything (parse, navigate, fork, write)
- **Why:** Separation of concerns. The TUI is a read-only navigator that outputs a decision. The skill (with Claude's help) handles the complex JSONL manipulation, session creation, and auto-switch. This makes the TUI simpler and more testable.

### 5.4 Auto-switch after fork
- **Chosen:** Auto-switch to new session
- **Alternative:** Print session ID, user manually resumes
- **Why:** User preference. Reduces friction. The skill will use Claude Code's session management to switch context.

## 6. Edge Cases

1. **Empty conversation** — TUI shows "No messages in this session" and exits
2. **Single message** — Tree shows one node; fork creates a session with just that message
3. **Very long messages** — Content preview truncated to 80 chars with "..."
4. **Binary/image content in messages** — Show "[image]" or "[binary content]" placeholder
5. **Conversation with only subagent sidechains** — Main thread may be short; sidechains shown collapsed
6. **Concurrent writes** — If Claude is still generating while TUI is open, TUI works on snapshot at invocation time. No live updates.
7. **Corrupted JSONL** — Skip malformed lines, log warning, continue with valid entries
8. **Missing parentUuid** — Treat as root node (defensive)

## 7. Open Design Questions for Implementation Phase

1. **Textual CSS theme** — exact colors/styling TBD during implementation
2. **Search (/ key)** — listed as stretch goal; implement if time permits
3. **Auto-switch mechanism** — need to verify how Claude Code handles session switching mid-conversation; may need to exit and relaunch with `--resume`
