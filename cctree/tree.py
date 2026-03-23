"""Build a navigable tree from parsed session entries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .parser import extract_content_preview


@dataclass
class TreeNode:
    """A single node in the conversation tree."""

    uuid: str
    parent_uuid: str | None
    role: str  # "user" or "assistant"
    content_preview: str
    timestamp: datetime
    is_sidechain: bool = False
    sidechain_agent_id: str | None = None
    sidechain_slug: str | None = None
    children: list[TreeNode] = field(default_factory=list)
    raw_entry: dict[str, Any] = field(default_factory=dict, repr=False)

    # UI state
    expanded: bool = True
    selected: bool = False

    @property
    def label_prefix(self) -> str:
        if self.is_sidechain:
            return "[S]"
        return "[U]" if self.role == "user" else "[A]"

    @property
    def display_label(self) -> str:
        role_name = {
            "user": "You",
            "assistant": "Claude",
        }.get(self.role, self.role)
        if self.is_sidechain and self.sidechain_slug:
            role_name = f"Subagent ({self.sidechain_slug})"
        return f"{self.label_prefix} {role_name}: {self.content_preview!r}"

    @property
    def sidechain_summary(self) -> str | None:
        """One-liner summary for collapsed sidechain display."""
        if not self.is_sidechain:
            return None
        return f"{self.label_prefix} Subagent: {self.content_preview!r}"


def _parse_timestamp(entry: dict[str, Any]) -> datetime:
    ts = entry.get("timestamp", "")
    if isinstance(ts, str) and ts:
        # Handle ISO 8601 with Z suffix
        ts = ts.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            pass
    elif isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts / 1000)
    return datetime.min


def build_tree(messages: list[dict[str, Any]]) -> list[TreeNode]:
    """Build a tree of TreeNodes from filtered message entries.

    Returns a list of root nodes (typically one, but handles orphans).
    """
    nodes: dict[str, TreeNode] = {}

    # First pass: create all nodes
    for entry in messages:
        uuid = entry.get("uuid")
        if not uuid:
            continue

        message = entry.get("message", {})
        role = message.get("role", entry.get("type", "unknown"))
        preview = extract_content_preview(message)
        is_sidechain = entry.get("isSidechain", False)

        node = TreeNode(
            uuid=uuid,
            parent_uuid=entry.get("parentUuid"),
            role=role,
            content_preview=preview,
            timestamp=_parse_timestamp(entry),
            is_sidechain=is_sidechain,
            sidechain_agent_id=entry.get("agentId"),
            sidechain_slug=entry.get("slug"),
            raw_entry=entry,
            expanded=not is_sidechain,  # Sidechains collapsed by default
        )
        nodes[uuid] = node

    # Second pass: link children to parents
    roots: list[TreeNode] = []
    for node in nodes.values():
        if node.parent_uuid and node.parent_uuid in nodes:
            nodes[node.parent_uuid].children.append(node)
        else:
            # Root node or orphan (parent not found)
            roots.append(node)

    # Sort children by timestamp at each level
    def sort_children(node: TreeNode) -> None:
        node.children.sort(key=lambda n: n.timestamp)
        for child in node.children:
            sort_children(child)

    for root in roots:
        sort_children(root)

    roots.sort(key=lambda n: n.timestamp)
    return roots


def flatten_tree(roots: list[TreeNode]) -> list[TreeNode]:
    """Flatten the tree into a depth-first ordered list of visible nodes."""
    result: list[TreeNode] = []

    def walk(node: TreeNode) -> None:
        result.append(node)
        if node.expanded:
            for child in node.children:
                walk(child)

    for root in roots:
        walk(root)
    return result


def get_depth(node: TreeNode, roots: list[TreeNode]) -> int:
    """Get the depth of a node in the tree (0 for root)."""
    all_nodes: dict[str, TreeNode] = {}

    def collect(n: TreeNode) -> None:
        all_nodes[n.uuid] = n
        for c in n.children:
            collect(c)

    for r in roots:
        collect(r)

    depth = 0
    current = node
    while current.parent_uuid and current.parent_uuid in all_nodes:
        depth += 1
        current = all_nodes[current.parent_uuid]
    return depth


def find_node(roots: list[TreeNode], uuid: str) -> TreeNode | None:
    """Find a node by UUID in the tree."""
    for root in roots:
        if root.uuid == uuid:
            return root
        for child in root.children:
            found = find_node([child], uuid)
            if found:
                return found
    return None


def get_ancestor_uuids(node: TreeNode, roots: list[TreeNode]) -> set[str]:
    """Get the set of UUIDs from a node back to the root (inclusive)."""
    all_nodes: dict[str, TreeNode] = {}

    def collect(n: TreeNode) -> None:
        all_nodes[n.uuid] = n
        for c in n.children:
            collect(c)

    for r in roots:
        collect(r)

    ancestors: set[str] = set()
    current: TreeNode | None = node
    while current:
        ancestors.add(current.uuid)
        if current.parent_uuid and current.parent_uuid in all_nodes:
            current = all_nodes[current.parent_uuid]
        else:
            break
    return ancestors


def tree_stats(roots: list[TreeNode]) -> dict[str, int]:
    """Compute basic statistics about the tree."""
    total = 0
    user_count = 0
    assistant_count = 0
    sidechain_count = 0
    max_depth = 0

    def walk(node: TreeNode, depth: int) -> None:
        nonlocal total, user_count, assistant_count, sidechain_count, max_depth
        total += 1
        if node.role == "user":
            user_count += 1
        elif node.role == "assistant":
            assistant_count += 1
        if node.is_sidechain:
            sidechain_count += 1
        max_depth = max(max_depth, depth)
        for child in node.children:
            walk(child, depth + 1)

    for root in roots:
        walk(root, 0)

    return {
        "total_nodes": total,
        "user_messages": user_count,
        "assistant_messages": assistant_count,
        "sidechain_nodes": sidechain_count,
        "max_depth": max_depth,
        "root_count": len(roots),
    }
