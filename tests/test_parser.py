"""Tests for cctree.parser module."""

import json
import tempfile
from pathlib import Path

import pytest

from cctree.parser import extract_content_preview, filter_messages, parse_session_file

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseSessionFile:
    def test_parses_sample_fixture(self):
        entries = parse_session_file(FIXTURES / "sample_session.jsonl")
        assert len(entries) > 0
        # Should have various types
        types = {e.get("type") for e in entries}
        assert "user" in types
        assert "assistant" in types
        assert "file-history-snapshot" in types

    def test_skips_malformed_lines(self, capsys):
        entries = parse_session_file(FIXTURES / "sample_session.jsonl")
        captured = capsys.readouterr()
        assert "malformed line 17" in captured.err

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.jsonl"
        f.write_text("")
        entries = parse_session_file(f)
        assert entries == []

    def test_blank_lines_skipped(self, tmp_path):
        f = tmp_path / "blanks.jsonl"
        content = '{"type": "user", "uuid": "1"}\n\n\n{"type": "assistant", "uuid": "2"}\n'
        f.write_text(content)
        entries = parse_session_file(f)
        assert len(entries) == 2

    def test_all_malformed(self, tmp_path, capsys):
        f = tmp_path / "bad.jsonl"
        f.write_text("not json\nalso bad\n")
        entries = parse_session_file(f)
        assert entries == []
        captured = capsys.readouterr()
        assert "malformed line 1" in captured.err
        assert "malformed line 2" in captured.err


class TestFilterMessages:
    def test_filters_to_user_and_assistant(self):
        entries = parse_session_file(FIXTURES / "sample_session.jsonl")
        messages = filter_messages(entries)
        types = {e.get("type") for e in messages}
        assert types == {"user", "assistant"}

    def test_removes_file_history_snapshots(self):
        entries = parse_session_file(FIXTURES / "sample_session.jsonl")
        snapshot_count = sum(1 for e in entries if e.get("type") == "file-history-snapshot")
        assert snapshot_count > 0  # Fixture has snapshots
        messages = filter_messages(entries)
        snapshot_after = sum(1 for e in messages if e.get("type") == "file-history-snapshot")
        assert snapshot_after == 0

    def test_removes_progress_entries(self):
        entries = parse_session_file(FIXTURES / "sample_session.jsonl")
        progress_count = sum(1 for e in entries if e.get("type") == "progress")
        assert progress_count > 0  # Fixture has progress
        messages = filter_messages(entries)
        progress_after = sum(1 for e in messages if e.get("type") == "progress")
        assert progress_after == 0

    def test_empty_input(self):
        assert filter_messages([]) == []


class TestExtractContentPreview:
    def test_simple_string_content(self):
        msg = {"content": "Hello, world!"}
        assert extract_content_preview(msg) == "Hello, world!"

    def test_truncates_long_content(self):
        msg = {"content": "x" * 200}
        preview = extract_content_preview(msg, max_length=80)
        assert len(preview) == 80
        assert preview.endswith("...")

    def test_text_block_content(self):
        msg = {"content": [{"type": "text", "text": "Some response text"}]}
        assert extract_content_preview(msg) == "Some response text"

    def test_tool_use_block(self):
        msg = {"content": [
            {"type": "text", "text": "Let me check."},
            {"type": "tool_use", "name": "Read", "id": "t1", "input": {}},
        ]}
        preview = extract_content_preview(msg)
        assert "Let me check." in preview
        assert "[tool: Read]" in preview

    def test_tool_result_block(self):
        msg = {"content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": "File contents here"},
        ]}
        preview = extract_content_preview(msg)
        assert "[result:" in preview

    def test_thinking_blocks_excluded(self):
        msg = {"content": [
            {"type": "thinking", "thinking": "secret thoughts"},
            {"type": "text", "text": "Visible response"},
        ]}
        preview = extract_content_preview(msg)
        assert "secret" not in preview
        assert "Visible response" in preview

    def test_empty_content(self):
        assert extract_content_preview({}) == "[empty message]"
        assert extract_content_preview({"content": ""}) == "[empty message]"

    def test_collapses_whitespace(self):
        msg = {"content": "hello\n\n  world\t\tthere"}
        assert extract_content_preview(msg) == "hello world there"
