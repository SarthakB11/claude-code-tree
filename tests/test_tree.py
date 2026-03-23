"""Tests for cctree.tree module."""

from pathlib import Path

import pytest

from cctree.parser import filter_messages, parse_session_file
from cctree.tree import (
    TreeNode,
    build_tree,
    find_node,
    flatten_tree,
    get_ancestor_uuids,
    get_depth,
    tree_stats,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load_sample_tree():
    entries = parse_session_file(FIXTURES / "sample_session.jsonl")
    messages = filter_messages(entries)
    return build_tree(messages)


class TestBuildTree:
    def test_builds_from_sample(self):
        roots = _load_sample_tree()
        assert len(roots) == 1  # Single root
        assert roots[0].role == "user"
        assert roots[0].parent_uuid is None

    def test_parent_child_linkage(self):
        roots = _load_sample_tree()
        root = roots[0]
        assert len(root.children) == 1  # One direct child (assistant response)
        child = root.children[0]
        assert child.role == "assistant"
        assert child.parent_uuid == root.uuid

    def test_sidechain_detected(self):
        roots = _load_sample_tree()
        stats = tree_stats(roots)
        assert stats["sidechain_nodes"] == 2  # User + assistant in sidechain

    def test_sidechain_collapsed_by_default(self):
        roots = _load_sample_tree()
        node = find_node(roots, "msg-009")  # Sidechain user
        assert node is not None
        assert node.is_sidechain
        assert not node.expanded

    def test_branching_point(self):
        """msg-008 should have two children: sidechain msg-009 and main msg-012."""
        roots = _load_sample_tree()
        node = find_node(roots, "msg-008")
        assert node is not None
        assert len(node.children) == 2
        child_uuids = {c.uuid for c in node.children}
        assert "msg-009" in child_uuids
        assert "msg-012" in child_uuids

    def test_children_sorted_by_timestamp(self):
        roots = _load_sample_tree()
        node = find_node(roots, "msg-008")
        assert node is not None
        # msg-009 (10:01:16) should come before msg-012 (10:02:00)
        assert node.children[0].uuid == "msg-009"
        assert node.children[1].uuid == "msg-012"

    def test_orphan_becomes_root(self):
        """An entry with a parentUuid that doesn't exist should become a root."""
        messages = [
            {
                "uuid": "orphan-1",
                "parentUuid": "nonexistent-parent",
                "type": "user",
                "message": {"role": "user", "content": "I am an orphan"},
                "timestamp": "2026-01-01T00:00:00.000Z",
            }
        ]
        roots = build_tree(messages)
        assert len(roots) == 1
        assert roots[0].uuid == "orphan-1"

    def test_empty_input(self):
        roots = build_tree([])
        assert roots == []

    def test_single_message(self):
        messages = [
            {
                "uuid": "only-one",
                "parentUuid": None,
                "type": "user",
                "message": {"role": "user", "content": "Solo message"},
                "timestamp": "2026-01-01T00:00:00.000Z",
            }
        ]
        roots = build_tree(messages)
        assert len(roots) == 1
        assert roots[0].children == []

    def test_entries_without_uuid_skipped(self):
        messages = [
            {"type": "user", "message": {"role": "user", "content": "no uuid"}},
            {
                "uuid": "valid",
                "parentUuid": None,
                "type": "user",
                "message": {"role": "user", "content": "has uuid"},
                "timestamp": "2026-01-01T00:00:00.000Z",
            },
        ]
        roots = build_tree(messages)
        assert len(roots) == 1
        assert roots[0].uuid == "valid"


class TestTreeNode:
    def test_display_label_user(self):
        node = TreeNode(
            uuid="1", parent_uuid=None, role="user",
            content_preview="Hello", timestamp=None,
        )
        assert node.display_label == "[U] You: 'Hello'"

    def test_display_label_assistant(self):
        node = TreeNode(
            uuid="1", parent_uuid=None, role="assistant",
            content_preview="Hi there", timestamp=None,
        )
        assert node.display_label == "[A] Claude: 'Hi there'"

    def test_display_label_sidechain(self):
        node = TreeNode(
            uuid="1", parent_uuid=None, role="user",
            content_preview="Task", timestamp=None,
            is_sidechain=True, sidechain_slug="golden-river",
        )
        assert "Subagent (golden-river)" in node.display_label
        assert "[S]" in node.display_label

    def test_sidechain_summary(self):
        node = TreeNode(
            uuid="1", parent_uuid=None, role="user",
            content_preview="Explore files", timestamp=None,
            is_sidechain=True,
        )
        assert node.sidechain_summary is not None
        assert "Subagent" in node.sidechain_summary

    def test_non_sidechain_no_summary(self):
        node = TreeNode(
            uuid="1", parent_uuid=None, role="user",
            content_preview="Normal", timestamp=None,
        )
        assert node.sidechain_summary is None


class TestFlattenTree:
    def test_flatten_respects_expanded(self):
        roots = _load_sample_tree()
        flat = flatten_tree(roots)
        # Sidechain nodes are collapsed, so their children should not appear
        sidechain_child = find_node(roots, "msg-010")  # Child of collapsed sidechain
        flat_uuids = {n.uuid for n in flat}
        assert "msg-009" in flat_uuids  # The sidechain root itself is visible
        assert "msg-010" not in flat_uuids  # Its child is hidden (collapsed)

    def test_flatten_all_expanded(self):
        roots = _load_sample_tree()
        # Expand everything
        def expand_all(node):
            node.expanded = True
            for c in node.children:
                expand_all(c)
        for r in roots:
            expand_all(r)
        flat = flatten_tree(roots)
        stats = tree_stats(roots)
        assert len(flat) == stats["total_nodes"]


class TestGetAncestorUuids:
    def test_leaf_to_root(self):
        roots = _load_sample_tree()
        leaf = find_node(roots, "msg-015")
        assert leaf is not None
        ancestors = get_ancestor_uuids(leaf, roots)
        assert "msg-015" in ancestors
        assert "msg-001" in ancestors  # Root

    def test_root_has_only_self(self):
        roots = _load_sample_tree()
        ancestors = get_ancestor_uuids(roots[0], roots)
        assert ancestors == {roots[0].uuid}


class TestFindNode:
    def test_finds_existing(self):
        roots = _load_sample_tree()
        node = find_node(roots, "msg-008")
        assert node is not None
        assert node.uuid == "msg-008"

    def test_returns_none_for_missing(self):
        roots = _load_sample_tree()
        assert find_node(roots, "nonexistent") is None


class TestTreeStats:
    def test_sample_stats(self):
        roots = _load_sample_tree()
        stats = tree_stats(roots)
        assert stats["total_nodes"] == 14
        assert stats["user_messages"] == 7
        assert stats["assistant_messages"] == 7
        assert stats["sidechain_nodes"] == 2
        assert stats["root_count"] == 1
        assert stats["max_depth"] > 0
