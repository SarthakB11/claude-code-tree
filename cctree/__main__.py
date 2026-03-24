"""Entry point for `python -m cctree`."""

from __future__ import annotations

import io
import json
import sys

# Ensure stdout handles Unicode on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace"
    )

from .cli import build_arg_parser, find_session_file
from .parser import filter_conversation_turns, filter_messages, parse_session_file
from .tree import TreeNode, build_tree, find_node, tree_stats


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    # Resolve session file
    session_file = args.session_file
    if session_file:
        session_file = session_file.expanduser()
    else:
        session_file = find_session_file(session_id=args.session_id)

    if not session_file or not session_file.is_file():
        print("error: no session file found", file=sys.stderr)
        if not args.session_file:
            print(
                "hint: use --session-file <path> or --session-id <id>",
                file=sys.stderr,
            )
        return 1

    # Parse and build tree
    entries = parse_session_file(session_file)
    messages = filter_messages(entries)

    if not messages:
        print("No conversation messages found in this session.", file=sys.stderr)
        return 1

    roots = build_tree(messages)
    stats = tree_stats(roots)

    # Determine session ID
    session_id = args.session_id
    if not session_id and messages:
        session_id = messages[0].get("sessionId", session_file.stem)

    # --stats: print JSON stats and exit
    if args.stats:
        print(json.dumps(stats, indent=2))
        return 0

    # --render-text: print compact numbered tree for inline display
    if args.render_text:
        compact_messages = filter_conversation_turns(entries)
        compact_roots = build_tree(compact_messages)
        compact_stats = tree_stats(compact_roots)
        _render_text_tree(compact_roots, compact_stats, session_id)
        return 0

    # --fork: non-interactive fork
    if args.fork:
        return _do_fork(session_file, args.fork)

    # --overwrite: non-interactive overwrite
    if args.overwrite:
        return _do_overwrite(session_file, args.overwrite)

    # Default: launch TUI
    from .renderer import ActionResult, CCTreeApp

    app = CCTreeApp(
        roots=roots,
        session_id=session_id,
        session_file=str(session_file),
    )
    result: ActionResult | None = app.run()

    if result is None or result.action == "cancel":
        return 0

    if args.output_only:
        output = {
            "action": result.action,
            "node_uuid": result.node_uuid,
            "session_id": result.session_id,
            "session_file": result.session_file,
        }
        print(json.dumps(output))
    else:
        if result.action == "fork":
            from pathlib import Path
            session_dir = Path(result.session_file).parent if result.session_file else None
            if session_dir:
                candidates = sorted(session_dir.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
                for c in candidates:
                    if c.stem != result.session_id:
                        print(f"\n  Forked session: {c.stem}")
                        print(f"  Switch with: /resume {c.stem}\n")
                        break
        elif result.action == "overwrite":
            print(f"\n  Session truncated.")
            print(f"  Switch with: /resume {result.session_id}\n")

    return 0


def _render_text_tree(roots: list[TreeNode], stats: dict, session_id: str | None) -> None:
    """Render a numbered tree for inline display in Claude Code."""
    print(f"Session: {session_id or 'unknown'}")
    print(f"Messages: {stats['total_nodes']} ({stats['user_messages']} user, {stats['assistant_messages']} assistant)")
    if stats['sidechain_nodes']:
        print(f"Sidechains: {stats['sidechain_nodes']}")
    print()

    counter = [0]  # mutable counter for closure

    def render_node(node: TreeNode, prefix: str = "", is_last: bool = True, is_root: bool = True) -> None:
        counter[0] += 1
        num = counter[0]

        if is_root:
            connector = ""
            child_prefix = ""
        else:
            connector = "└─" if is_last else "├─"
            child_prefix = prefix + ("  " if is_last else "│ ")

        # Role indicator
        if node.is_sidechain:
            tag = "[S]"
            role = f"Subagent"
            if node.sidechain_slug:
                role = f"Subagent ({node.sidechain_slug})"
        elif node.role == "user":
            tag = "[U]"
            role = "You"
        else:
            tag = "[A]"
            role = "Claude"

        preview = node.content_preview
        sidechain_marker = " [+collapsed]" if node.is_sidechain and node.children else ""

        print(f"{prefix}{connector}{num:>3}. {tag} {role}: {preview}{sidechain_marker}  (uuid:{node.uuid})")

        # Show children (skip sidechain children in collapsed view)
        visible_children = node.children if not node.is_sidechain else []
        for i, child in enumerate(visible_children):
            last = i == len(visible_children) - 1
            render_node(child, child_prefix, last, is_root=False)

    for root in roots:
        render_node(root)

    print()
    print("To fork:      python -m cctree --session-file <path> --fork <uuid>")
    print("To overwrite: python -m cctree --session-file <path> --overwrite <uuid>")


def _do_fork(session_file, node_uuid: str) -> int:
    """Non-interactive fork."""
    from .actions import fork_session
    new_path = fork_session(session_file, node_uuid)
    if new_path:
        result = {"action": "fork", "new_session_id": new_path.stem, "new_session_file": str(new_path)}
        print(json.dumps(result))
        return 0
    else:
        print(json.dumps({"error": "fork failed — node not found"}))
        return 1


def _do_overwrite(session_file, node_uuid: str) -> int:
    """Non-interactive overwrite."""
    from .actions import overwrite_session
    backup_path = overwrite_session(session_file, node_uuid)
    if backup_path:
        result = {"action": "overwrite", "backup_file": str(backup_path)}
        print(json.dumps(result))
        return 0
    else:
        print(json.dumps({"error": "overwrite failed — node not found"}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
