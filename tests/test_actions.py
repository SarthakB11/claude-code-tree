"""Tests for cctree.actions module."""

import json
import shutil
from pathlib import Path

import pytest

from cctree.actions import fork_session, overwrite_session
from cctree.parser import filter_messages, parse_session_file
from cctree.tree import build_tree, find_node, tree_stats

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_session(tmp_path):
    """Copy sample fixture to tmp_path so tests can modify it."""
    src = FIXTURES / "sample_session.jsonl"
    dst = tmp_path / "test-session.jsonl"
    shutil.copy2(src, dst)
    return dst


class TestForkSession:
    def test_fork_from_midpoint(self, sample_session):
        """Fork from msg-008 should create a new file with messages up to msg-008."""
        new_path = fork_session(sample_session, "msg-008")
        assert new_path is not None
        assert new_path.is_file()
        assert new_path != sample_session

        # New session should have entries up to and including msg-008
        entries = parse_session_file(new_path)
        messages = filter_messages(entries)
        uuids = {e.get("uuid") for e in messages}
        assert "msg-001" in uuids  # Root
        assert "msg-008" in uuids  # Target
        assert "msg-012" not in uuids  # After target
        assert "msg-015" not in uuids  # Way after target

    def test_fork_from_root(self, sample_session):
        """Fork from root should create a file with just the root message."""
        new_path = fork_session(sample_session, "msg-001")
        assert new_path is not None
        entries = parse_session_file(new_path)
        messages = filter_messages(entries)
        assert len(messages) == 1
        assert messages[0].get("uuid") == "msg-001"

    def test_fork_from_leaf(self, sample_session):
        """Fork from leaf (msg-015) should include the full ancestor chain."""
        new_path = fork_session(sample_session, "msg-015")
        assert new_path is not None
        entries = parse_session_file(new_path)
        messages = filter_messages(entries)
        uuids = {e.get("uuid") for e in messages}
        assert "msg-001" in uuids
        assert "msg-015" in uuids

    def test_fork_generates_new_session_id(self, sample_session):
        """Forked entries should have a new sessionId."""
        new_path = fork_session(sample_session, "msg-003")
        entries = parse_session_file(new_path)
        session_ids = {e.get("sessionId") for e in entries if "sessionId" in e}
        assert len(session_ids) == 1
        assert "session-001" not in session_ids  # Should be different

    def test_fork_nonexistent_node_returns_none(self, sample_session):
        result = fork_session(sample_session, "nonexistent")
        assert result is None

    def test_fork_preserves_original(self, sample_session):
        """Original session file should be untouched after fork."""
        original_content = sample_session.read_text()
        fork_session(sample_session, "msg-008")
        assert sample_session.read_text() == original_content

    def test_forked_file_is_valid_jsonl(self, sample_session):
        """Every line in the forked file should be valid JSON."""
        new_path = fork_session(sample_session, "msg-008")
        with open(new_path) as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    json.loads(line)  # Should not raise


class TestOverwriteSession:
    def test_overwrite_creates_backup(self, sample_session):
        backup = overwrite_session(sample_session, "msg-008")
        assert backup is not None
        assert backup.is_file()
        assert ".bak." in str(backup)

    def test_overwrite_truncates_descendants(self, sample_session):
        overwrite_session(sample_session, "msg-008")
        entries = parse_session_file(sample_session)
        messages = filter_messages(entries)
        uuids = {e.get("uuid") for e in messages}
        assert "msg-001" in uuids
        assert "msg-008" in uuids
        # Messages after msg-008 in the main chain should be removed
        assert "msg-012" not in uuids
        assert "msg-015" not in uuids

    def test_overwrite_keeps_ancestor_chain(self, sample_session):
        overwrite_session(sample_session, "msg-008")
        entries = parse_session_file(sample_session)
        messages = filter_messages(entries)
        uuids = [e.get("uuid") for e in messages]
        # Ancestor chain from msg-008 to root
        assert "msg-001" in uuids
        assert "msg-002" in uuids
        assert "msg-003" in uuids
        assert "msg-004" in uuids
        assert "msg-008" in uuids

    def test_overwrite_nonexistent_node_returns_none(self, sample_session):
        result = overwrite_session(sample_session, "nonexistent")
        assert result is None

    def test_backup_matches_original(self, sample_session):
        original_content = sample_session.read_text()
        backup = overwrite_session(sample_session, "msg-008")
        assert backup.read_text() == original_content

    def test_overwrite_result_is_valid_jsonl(self, sample_session):
        overwrite_session(sample_session, "msg-008")
        with open(sample_session) as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    json.loads(line)  # Should not raise
