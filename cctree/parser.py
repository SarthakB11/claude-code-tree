"""Parse Claude Code session JSONL files into structured entries."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


# Entry types that represent actual conversation messages
MESSAGE_TYPES = {"user", "assistant"}


def parse_session_file(path: Path) -> list[dict[str, Any]]:
    """Read a session JSONL file and return all parsed entries.

    Each line is a JSON object. Malformed lines are skipped with a
    warning to stderr.
    """
    entries: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entries.append(entry)
            except json.JSONDecodeError:
                print(
                    f"warning: skipping malformed line {lineno} in {path}",
                    file=sys.stderr,
                )
    return entries


def filter_messages(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter entries to only user and assistant messages.

    Removes progress, file-history-snapshot, and other non-message entries.
    """
    return [e for e in entries if e.get("type") in MESSAGE_TYPES]


def filter_conversation_turns(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter to only meaningful conversation turns.

    Keeps:
    - User messages that are actual prompts (not tool results)
    - Assistant messages that contain text (not pure tool_use)

    This gives a compact view of the conversation as the user experienced it.
    """
    result = []
    for e in entries:
        if e.get("type") not in MESSAGE_TYPES:
            continue

        message = e.get("message", {})
        content = message.get("content", "")

        # User messages: skip tool_result entries
        if message.get("role") == "user":
            if isinstance(content, list):
                # Check if this is purely tool results
                has_text = any(
                    isinstance(b, dict) and b.get("type") == "text"
                    for b in content
                )
                is_all_tool_results = all(
                    isinstance(b, dict) and b.get("type") == "tool_result"
                    for b in content
                )
                if is_all_tool_results and not has_text:
                    continue
            if isinstance(content, str) and content.strip():
                result.append(e)
                continue
            if isinstance(content, list) and not all(
                isinstance(b, dict) and b.get("type") == "tool_result"
                for b in content
            ):
                result.append(e)
                continue
            continue

        # Assistant messages: skip pure tool_use without text
        if message.get("role") == "assistant":
            if isinstance(content, list):
                has_text = any(
                    isinstance(b, dict) and b.get("type") == "text"
                    and b.get("text", "").strip()
                    for b in content
                )
                if has_text:
                    result.append(e)
                    continue
                # Pure tool_use — skip
                continue
            if isinstance(content, str) and content.strip():
                result.append(e)
                continue

    return result


def extract_content_preview(message: dict[str, Any], max_length: int = 80) -> str:
    """Extract a short text preview from a message's content field."""
    content = message.get("content", "")

    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        # Content is an array of blocks — extract text from text blocks
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "tool_use":
                    parts.append(f"[tool: {block.get('name', '?')}]")
                elif block.get("type") == "tool_result":
                    result_content = block.get("content", "")
                    if isinstance(result_content, str):
                        parts.append(f"[result: {result_content[:30]}]")
                    else:
                        parts.append("[tool result]")
                elif block.get("type") == "thinking":
                    continue  # Skip thinking blocks from preview
        text = " ".join(parts)
    else:
        text = str(content)

    # Collapse whitespace and truncate
    text = " ".join(text.split())
    if len(text) > max_length:
        text = text[: max_length - 3] + "..."
    return text or "[empty message]"
