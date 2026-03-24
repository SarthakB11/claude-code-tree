"""Tests for filter_conversation_turns and --render-text / --fork / --overwrite CLI modes."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from cctree.parser import extract_content_preview, filter_conversation_turns

FIXTURES = Path(__file__).parent / "fixtures"
CCTREE = [sys.executable, "-m", "cctree"]


class TestFilterConversationTurns:
    def test_keeps_user_text_prompts(self):
        entries = [
            {"type": "user", "uuid": "1", "message": {"role": "user", "content": "Hello"}},
        ]
        result = filter_conversation_turns(entries)
        assert len(result) == 1

    def test_skips_tool_result_only_user_messages(self):
        entries = [
            {
                "type": "user", "uuid": "1",
                "message": {"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": "t1", "content": "done"}
                ]},
            },
        ]
        result = filter_conversation_turns(entries)
        assert len(result) == 0

    def test_keeps_user_message_with_mixed_content(self):
        entries = [
            {
                "type": "user", "uuid": "1",
                "message": {"role": "user", "content": [
                    {"type": "text", "text": "Here's what I think"},
                    {"type": "tool_result", "tool_use_id": "t1", "content": "ok"},
                ]},
            },
        ]
        result = filter_conversation_turns(entries)
        assert len(result) == 1

    def test_keeps_assistant_with_text(self):
        entries = [
            {
                "type": "assistant", "uuid": "1",
                "message": {"role": "assistant", "content": [
                    {"type": "text", "text": "Here's my response"},
                ]},
            },
        ]
        result = filter_conversation_turns(entries)
        assert len(result) == 1

    def test_skips_assistant_pure_tool_use(self):
        entries = [
            {
                "type": "assistant", "uuid": "1",
                "message": {"role": "assistant", "content": [
                    {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "ls"}},
                ]},
            },
        ]
        result = filter_conversation_turns(entries)
        assert len(result) == 0

    def test_keeps_assistant_with_text_and_tool_use(self):
        entries = [
            {
                "type": "assistant", "uuid": "1",
                "message": {"role": "assistant", "content": [
                    {"type": "text", "text": "Let me check that."},
                    {"type": "tool_use", "id": "t1", "name": "Read", "input": {}},
                ]},
            },
        ]
        result = filter_conversation_turns(entries)
        assert len(result) == 1

    def test_skips_assistant_with_empty_text(self):
        entries = [
            {
                "type": "assistant", "uuid": "1",
                "message": {"role": "assistant", "content": [
                    {"type": "text", "text": ""},
                    {"type": "tool_use", "id": "t1", "name": "Read", "input": {}},
                ]},
            },
        ]
        result = filter_conversation_turns(entries)
        assert len(result) == 0

    def test_skips_non_message_types(self):
        entries = [
            {"type": "file-history-snapshot", "messageId": "1"},
            {"type": "progress", "uuid": "2", "data": {}},
            {"type": "user", "uuid": "3", "message": {"role": "user", "content": "Hi"}},
        ]
        result = filter_conversation_turns(entries)
        assert len(result) == 1
        assert result[0]["uuid"] == "3"

    def test_empty_input(self):
        assert filter_conversation_turns([]) == []

    def test_keeps_assistant_string_content(self):
        entries = [
            {
                "type": "assistant", "uuid": "1",
                "message": {"role": "assistant", "content": "Plain text response"},
            },
        ]
        result = filter_conversation_turns(entries)
        assert len(result) == 1

    def test_sample_fixture_is_compact(self):
        """Compact filter should return fewer entries than full filter."""
        from cctree.parser import filter_messages, parse_session_file
        entries = parse_session_file(FIXTURES / "sample_session.jsonl")
        full = filter_messages(entries)
        compact = filter_conversation_turns(entries)
        assert len(compact) < len(full)


class TestExtractContentPreviewEdgeCases:
    def test_image_block(self):
        msg = {"content": [{"type": "image", "source": {"data": "base64..."}}]}
        assert "[image]" in extract_content_preview(msg)

    def test_image_url_block(self):
        msg = {"content": [{"type": "image_url", "url": "https://example.com/img.png"}]}
        assert "[image]" in extract_content_preview(msg)

    def test_mixed_image_and_text(self):
        msg = {"content": [
            {"type": "text", "text": "Look at this:"},
            {"type": "image", "source": {"data": "..."}},
        ]}
        preview = extract_content_preview(msg)
        assert "Look at this:" in preview
        assert "[image]" in preview


class TestRenderTextCLI:
    def test_render_text_output(self):
        result = subprocess.run(
            CCTREE + ["--render-text", "--session-file", str(FIXTURES / "sample_session.jsonl")],
            capture_output=True, text=True, encoding="utf-8",
        )
        assert result.returncode == 0
        assert "Session:" in result.stdout
        assert "Messages:" in result.stdout
        # Should have numbered nodes
        assert "  1." in result.stdout
        # Should contain UUIDs for fork reference
        assert "(uuid:" in result.stdout

    def test_render_text_empty_session(self, tmp_path):
        f = tmp_path / "empty.jsonl"
        f.write_text("")
        result = subprocess.run(
            CCTREE + ["--render-text", "--session-file", str(f)],
            capture_output=True, text=True, encoding="utf-8",
        )
        assert result.returncode == 1
        assert "No conversation messages" in result.stderr


@pytest.fixture
def session_copy(tmp_path):
    """Copy sample fixture to tmp_path for tests that modify the session."""
    src = FIXTURES / "sample_session.jsonl"
    dst = tmp_path / "test.jsonl"
    shutil.copy2(src, dst)
    return dst


class TestForkCLI:
    def test_fork_outputs_json(self, session_copy):
        result = subprocess.run(
            CCTREE + ["--fork", "msg-008", "--session-file", str(session_copy)],
            capture_output=True, text=True, encoding="utf-8",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["action"] == "fork"
        assert "new_session_id" in data
        assert "new_session_file" in data

    def test_fork_nonexistent_node(self, session_copy):
        result = subprocess.run(
            CCTREE + ["--fork", "nonexistent", "--session-file", str(session_copy)],
            capture_output=True, text=True, encoding="utf-8",
        )
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert "error" in data


class TestOverwriteCLI:
    def test_overwrite_outputs_json(self, session_copy):
        result = subprocess.run(
            CCTREE + ["--overwrite", "msg-008", "--session-file", str(session_copy)],
            capture_output=True, text=True, encoding="utf-8",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["action"] == "overwrite"
        assert "backup_file" in data

    def test_overwrite_nonexistent_node(self, session_copy):
        result = subprocess.run(
            CCTREE + ["--overwrite", "nonexistent", "--session-file", str(session_copy)],
            capture_output=True, text=True, encoding="utf-8",
        )
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert "error" in data
