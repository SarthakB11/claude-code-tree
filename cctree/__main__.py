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
from .parser import filter_messages, parse_session_file
from .tree import build_tree, tree_stats


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

    # --stats: print JSON stats and exit
    if args.stats:
        print(json.dumps(stats, indent=2))
        return 0

    # Determine session ID from first entry or filename
    session_id = args.session_id
    if not session_id and messages:
        session_id = messages[0].get("sessionId", session_file.stem)

    # Launch TUI
    from .renderer import ActionResult, CCTreeApp

    app = CCTreeApp(
        roots=roots,
        session_id=session_id,
        session_file=str(session_file),
    )
    result: ActionResult | None = app.run()

    # Handle result
    if result is None or result.action == "cancel":
        return 0

    # Actions were already executed inside the TUI.
    # Print the resume command so the user can easily copy-paste it.
    if args.output_only:
        output = {
            "action": result.action,
            "node_uuid": result.node_uuid,
            "session_id": result.session_id,
            "session_file": result.session_file,
            "new_session_id": getattr(result, "new_session_id", None),
        }
        print(json.dumps(output))
    else:
        # Print a clear next-step for the user
        if result.action == "fork" and hasattr(result, "new_session_id") and result.new_session_id:
            print(f"\n  To open the forked session, run:")
            print(f"  claude --resume {result.new_session_id}\n")
        elif result.action == "fork":
            # new_session_id not on the tuple — read from the session dir
            from pathlib import Path
            session_dir = Path(result.session_file).parent if result.session_file else None
            if session_dir:
                # Find the newest JSONL that isn't the current session
                candidates = sorted(session_dir.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
                for c in candidates:
                    if c.stem != result.session_id:
                        print(f"\n  To open the forked session, run:")
                        print(f"  claude --resume {c.stem}\n")
                        break
        elif result.action == "overwrite":
            print(f"\n  Session truncated. To resume from the new endpoint, run:")
            print(f"  claude --resume {result.session_id}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
