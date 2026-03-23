"""Entry point for `python -m cctree`."""

from __future__ import annotations

import io
import json
import sys

from .cli import build_arg_parser, find_session_file


# Ensure stdout handles Unicode on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace"
    )
from .parser import filter_messages, parse_session_file
from .tree import build_tree, tree_stats


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    # Resolve session file
    session_file = args.session_file
    if not session_file:
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

    if args.stats:
        print(json.dumps(stats, indent=2))
        return 0

    # For now, print stats until TUI is implemented (Wave 2)
    print(f"Session: {session_file.stem}")
    print(f"Messages: {stats['total_nodes']} "
          f"({stats['user_messages']} user, {stats['assistant_messages']} assistant)")
    print(f"Sidechains: {stats['sidechain_nodes']}")
    print(f"Max depth: {stats['max_depth']}")
    print(f"Roots: {stats['root_count']}")
    print()
    print("Tree preview:")
    _print_tree(roots)
    print()
    print("[TUI not yet implemented — coming in Wave 2]")
    return 0


def _print_tree(
    roots: list,
    prefix: str = "",
    is_last: bool = True,
    is_root: bool = True,
) -> None:
    """Print an ASCII tree preview for verification."""
    for i, node in enumerate(roots):
        last = i == len(roots) - 1
        if is_root:
            connector = ""
            child_prefix = ""
        else:
            connector = "└─" if last else "├─"
            child_prefix = prefix + ("  " if last else "│ ")

        label = node.display_label
        if node.is_sidechain and not node.expanded:
            label += " [collapsed]"
        print(f"{prefix}{connector}{label}")

        if node.children and node.expanded:
            _print_tree(node.children, child_prefix, last, is_root=False)


if __name__ == "__main__":
    sys.exit(main())
