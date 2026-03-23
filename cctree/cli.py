"""CLI argument parsing and session discovery for cctree."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cctree",
        description="Interactive conversation tree navigator for Claude Code",
    )
    parser.add_argument(
        "--session-file",
        type=Path,
        help="Path to a session JSONL file (overrides auto-detection)",
    )
    parser.add_argument(
        "--session-id",
        type=str,
        help="Session ID to load (used with auto-detection)",
    )
    parser.add_argument(
        "--output-only",
        action="store_true",
        help="Output action JSON only (for skill integration)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print tree statistics and exit (no TUI)",
    )
    return parser


def get_claude_dir() -> Path:
    """Get the ~/.claude directory path."""
    return Path.home() / ".claude"


def get_project_id(cwd: str | None = None) -> str:
    """Convert a working directory path to a Claude Code project ID.

    Claude Code uses the path with separators replaced by '--' and
    colons removed as the project directory name.
    """
    if cwd is None:
        cwd = os.getcwd()
    # Normalize the path
    cwd = str(Path(cwd).resolve())
    # On Windows, remove the drive letter colon: C:\foo -> C-\foo
    # Claude Code format: C--Users-sarth-Documents-...
    project_id = cwd.replace(":\\", "--").replace("\\", "-").replace("/", "-")
    return project_id


def find_session_file(
    session_id: str | None = None, cwd: str | None = None
) -> Path | None:
    """Auto-detect the session JSONL file for the current project.

    Strategy:
    1. If session_id is given, look for that specific session file
    2. Otherwise, scan ~/.claude/sessions/ for sessions matching the cwd
    3. Fall back to the most recently modified .jsonl in the project dir
    """
    claude_dir = get_claude_dir()
    project_id = get_project_id(cwd)
    project_dir = claude_dir / "projects" / project_id

    if not project_dir.is_dir():
        return None

    # If session_id specified, look for it directly
    if session_id:
        candidate = project_dir / f"{session_id}.jsonl"
        if candidate.is_file():
            return candidate
        return None

    # Try to find the active session from ~/.claude/sessions/
    sessions_dir = claude_dir / "sessions"
    if sessions_dir.is_dir():
        active_cwd = str(Path(cwd or os.getcwd()).resolve())
        best_session = None
        best_time = 0

        for session_file in sessions_dir.glob("*.json"):
            try:
                data = json.loads(session_file.read_text(encoding="utf-8"))
                session_cwd = str(Path(data.get("cwd", "")).resolve())
                if session_cwd == active_cwd:
                    started = data.get("startedAt", 0)
                    if started > best_time:
                        best_time = started
                        best_session = data.get("sessionId")
            except (json.JSONDecodeError, OSError):
                continue

        if best_session:
            candidate = project_dir / f"{best_session}.jsonl"
            if candidate.is_file():
                return candidate

    # Fall back to most recently modified .jsonl in project dir
    jsonl_files = list(project_dir.glob("*.jsonl"))
    if jsonl_files:
        return max(jsonl_files, key=lambda f: f.stat().st_mtime)

    return None
