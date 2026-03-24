"""Fork and overwrite operations on Claude Code session JSONL files."""

from __future__ import annotations

import json
import shutil
import sys
import uuid as uuid_mod
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from .parser import filter_messages, parse_session_file
from .tree import build_tree, find_node, get_ancestor_uuids


@contextmanager
def _advisory_lock(path: Path):
    """Cross-platform advisory file lock for destructive operations.

    Locks the target file directly (no separate .lock file) to avoid
    stale lock files after crashes. Best-effort: proceeds without
    locking if the platform doesn't support it.
    """
    fd = None
    try:
        fd = open(path, "a")  # open in append to avoid truncation
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(fd.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    except (OSError, ImportError):
        yield
    finally:
        if fd:
            try:
                if sys.platform == "win32":
                    import msvcrt
                    msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_UN)
            except (OSError, ImportError):
                pass
            fd.close()


def fork_session(session_file: Path, node_uuid: str) -> Path | None:
    """Create a new session JSONL with messages up to and including the given node.

    Returns the path to the new session file, or None on failure.
    """
    session_file = Path(session_file)
    entries = parse_session_file(session_file)

    # Build tree from message entries to find ancestors
    messages = filter_messages(entries)
    roots = build_tree(messages)
    target = find_node(roots, node_uuid)
    if target is None:
        return None

    ancestor_uuids = get_ancestor_uuids(target, roots)

    # Collect all raw entries that are on the ancestor path.
    # We also include non-message entries (snapshots, progress) that sit
    # between ancestor messages to keep the session valid.
    keep_entries = []
    ancestor_seen = False
    for entry in entries:
        entry_uuid = entry.get("uuid") or entry.get("messageId")
        entry_type = entry.get("type", "")

        if entry_uuid in ancestor_uuids:
            keep_entries.append(entry)
            ancestor_seen = True
        elif entry_type in ("file-history-snapshot", "progress") and ancestor_seen:
            # Include interleaved non-message entries up to the target
            msg_id = entry.get("messageId", "")
            if msg_id in ancestor_uuids:
                keep_entries.append(entry)

        # Stop after the target node
        if entry_uuid == node_uuid and entry_type in ("user", "assistant"):
            break

    if not keep_entries:
        return None

    # Generate new session ID
    new_session_id = str(uuid_mod.uuid4())

    # Rewrite sessionId in all entries
    forked_entries = []
    for entry in keep_entries:
        new_entry = entry.copy()
        if "sessionId" in new_entry:
            new_entry["sessionId"] = new_session_id
        forked_entries.append(new_entry)

    # Write new session file alongside the original
    new_path = session_file.parent / f"{new_session_id}.jsonl"
    with open(new_path, "w", encoding="utf-8") as f:
        for entry in forked_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return new_path


def overwrite_session(session_file: Path, node_uuid: str) -> Path | None:
    """Truncate a session JSONL, removing all entries after the given node.

    Creates a timestamped backup before modifying. Returns the backup path,
    or None on failure.
    """
    session_file = Path(session_file)
    entries = parse_session_file(session_file)

    # Build tree to find the ancestor set
    messages = filter_messages(entries)
    roots = build_tree(messages)
    target = find_node(roots, node_uuid)
    if target is None:
        return None

    ancestor_uuids = get_ancestor_uuids(target, roots)

    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = session_file.with_suffix(f".jsonl.bak.{timestamp}")
    shutil.copy2(session_file, backup_path)

    # Filter entries: keep ancestors and associated non-message entries
    keep_entries = []
    for entry in entries:
        entry_uuid = entry.get("uuid") or entry.get("messageId")
        entry_type = entry.get("type", "")

        if entry_type in ("file-history-snapshot",):
            # Keep snapshots whose messageId is in the ancestor set
            msg_id = entry.get("messageId", "")
            if msg_id in ancestor_uuids:
                keep_entries.append(entry)
            continue

        if entry_type == "progress":
            # Keep progress entries tied to ancestor messages
            parent_uuid = entry.get("parentUuid", "")
            if parent_uuid in ancestor_uuids:
                keep_entries.append(entry)
            continue

        # For user/assistant messages, keep only ancestors
        if entry_uuid in ancestor_uuids:
            keep_entries.append(entry)

    if not keep_entries:
        return None

    # Write filtered entries back to original file (with advisory lock)
    with _advisory_lock(session_file):
        with open(session_file, "w", encoding="utf-8") as f:
            for entry in keep_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return backup_path
