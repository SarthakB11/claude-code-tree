"""Interactive TUI for navigating conversation trees using Textual."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import ClassVar, NamedTuple

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Label, Static, Tree
from textual.widgets._tree import TreeNode as TextualTreeNode

from .tree import TreeNode as CCTreeNode


class ActionResult(NamedTuple):
    """Result returned from the TUI when the user selects an action."""

    action: str  # "fork", "overwrite", "cancel"
    node_uuid: str | None
    session_id: str | None
    session_file: str | None


# ---------------------------------------------------------------------------
# Custom Tree widget
# ---------------------------------------------------------------------------

class ConversationTree(Tree[CCTreeNode]):
    """Tree widget specialized for Claude Code conversation nodes."""

    DEFAULT_CSS = """
    ConversationTree {
        padding: 1;
    }
    """

    def render_label(
        self,
        node: TextualTreeNode[CCTreeNode],
        base_style,
        style,
    ) -> Text:
        data = node.data
        if data is None:
            return Text(str(node.label))

        prefix_style = "bold cyan" if data.role == "user" else "bold green"
        if data.is_sidechain:
            prefix_style = "bold yellow"

        prefix = Text(data.label_prefix + " ", style=prefix_style)

        role_name = "You" if data.role == "user" else "Claude"
        if data.is_sidechain and data.sidechain_slug:
            role_name = f"Subagent ({data.sidechain_slug})"

        role_text = Text(f"{role_name}: ", style="bold")
        content = Text(data.content_preview, style="dim" if data.is_sidechain else "")

        return prefix + role_text + content


# ---------------------------------------------------------------------------
# Action menu (modal)
# ---------------------------------------------------------------------------

class ActionMenuScreen(ModalScreen[str]):
    """Modal dialog for choosing an action on a selected node."""

    DEFAULT_CSS = """
    ActionMenuScreen {
        align: center middle;
    }

    #action-dialog {
        width: 50;
        height: 14;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #action-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    #action-preview {
        color: $text-muted;
        margin-bottom: 1;
    }

    .action-option {
        margin: 0 1;
    }

    .action-key {
        text-style: bold;
        color: $accent;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("f", "fork", "Fork from here", show=True),
        Binding("o", "overwrite", "Overwrite (truncate after)", show=True),
        Binding("escape", "cancel", "Cancel", show=True),
    ]

    def __init__(self, node: CCTreeNode) -> None:
        super().__init__()
        self.node = node

    def compose(self) -> ComposeResult:
        role = "You" if self.node.role == "user" else "Claude"
        preview = self.node.content_preview[:60].replace("[", "\\[")
        with Container(id="action-dialog"):
            yield Label("Action on this message:", id="action-title")
            yield Label(f"{role}: {preview}", id="action-preview")
            yield Static("")
            yield Static("[bold $accent]f[/]  Fork new branch from here", classes="action-option")
            yield Static("[bold $accent]o[/]  Overwrite — remove all messages after this", classes="action-option")
            yield Static("")
            yield Static("[dim]Esc  Cancel[/dim]", classes="action-option")

    def action_fork(self) -> None:
        self.dismiss("fork")

    def action_overwrite(self) -> None:
        self.dismiss("overwrite")

    def action_cancel(self) -> None:
        self.dismiss("cancel")


# ---------------------------------------------------------------------------
# Overwrite confirmation modal
# ---------------------------------------------------------------------------

class ConfirmOverwriteScreen(ModalScreen[bool]):
    """Confirmation dialog for the destructive overwrite operation."""

    DEFAULT_CSS = """
    ConfirmOverwriteScreen {
        align: center middle;
    }

    #confirm-dialog {
        width: 55;
        height: 10;
        border: thick $error;
        background: $surface;
        padding: 1 2;
    }

    #confirm-title {
        text-style: bold;
        color: $error;
        margin-bottom: 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("y", "confirm", "Yes, overwrite", show=True),
        Binding("n,escape", "deny", "No, cancel", show=True),
    ]

    def __init__(self, descendant_count: int) -> None:
        super().__init__()
        self.descendant_count = descendant_count

    def compose(self) -> ComposeResult:
        with Container(id="confirm-dialog"):
            yield Label("WARNING: Destructive operation", id="confirm-title")
            yield Static(
                f"This will remove [bold]{self.descendant_count}[/bold] message(s) "
                f"after the selected point."
            )
            yield Static("A backup will be created before truncation.")
            yield Static("")
            yield Static("[bold red]y[/]  Yes, overwrite    [bold]n[/]  No, cancel")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_deny(self) -> None:
        self.dismiss(False)


# ---------------------------------------------------------------------------
# Result notification (shown before exit)
# ---------------------------------------------------------------------------

class ResultNotificationScreen(ModalScreen[bool]):
    """Shows the result of a fork/overwrite before the TUI exits."""

    DEFAULT_CSS = """
    ResultNotificationScreen {
        align: center middle;
    }

    #result-dialog {
        width: 65;
        height: auto;
        max-height: 14;
        border: thick $success;
        background: $surface;
        padding: 1 2;
    }

    #result-title {
        text-style: bold;
        color: $success;
        margin-bottom: 1;
    }

    #result-hint {
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter,escape,q", "dismiss_result", "OK", show=True),
    ]

    def __init__(self, title: str, body: str, hint: str = "") -> None:
        super().__init__()
        self._title = title
        self._body = body
        self._hint = hint

    def compose(self) -> ComposeResult:
        with Container(id="result-dialog"):
            yield Label(self._title, id="result-title")
            yield Static(self._body)
            if self._hint:
                yield Static(self._hint, id="result-hint")
            yield Static("")
            yield Static("[dim]Press Enter to exit[/dim]")

    def action_dismiss_result(self) -> None:
        self.dismiss(True)


# ---------------------------------------------------------------------------
# Detail panel
# ---------------------------------------------------------------------------

class NodeDetail(Static):
    """Shows details about the currently highlighted node."""

    DEFAULT_CSS = """
    NodeDetail {
        height: 4;
        padding: 0 2;
        background: $surface;
        border-top: solid $primary;
        color: $text-muted;
    }
    """

    def update_node(self, node: CCTreeNode | None) -> None:
        if node is None:
            self.update("[dim]No node selected[/dim]")
            return

        role = "You" if node.role == "user" else "Claude"
        if node.is_sidechain and node.sidechain_slug:
            role = f"Subagent ({node.sidechain_slug})"

        ts = node.timestamp.strftime("%Y-%m-%d %H:%M:%S") if node.timestamp else "?"
        # Escape Rich markup characters in user content to prevent MarkupError
        preview = node.content_preview[:120].replace("[", "\\[")
        sidechain_tag = " [yellow]\\[sidechain][/yellow]" if node.is_sidechain else ""

        self.update(
            f"[bold]{role}[/bold]{sidechain_tag}  {ts}\n"
            f"{preview}\n"
            f"[dim]Enter: action menu  f: fork  o: overwrite  q: quit[/dim]"
        )


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class CCTreeApp(App[ActionResult]):
    """Interactive conversation tree navigator."""

    TITLE = "cctree — Conversation Tree Navigator"

    CSS = """
    Screen {
        layout: vertical;
    }

    #tree-container {
        height: 1fr;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q,escape", "quit_app", "Quit", show=True),
        Binding("f", "quick_fork", "Fork", show=True),
        Binding("o", "quick_overwrite", "Overwrite", show=True),
        # Vim bindings that delegate to tree
        Binding("j", "tree_down", "Down", show=False),
        Binding("k", "tree_up", "Up", show=False),
        Binding("h", "tree_left", "Collapse/Parent", show=False),
        Binding("l", "tree_right", "Expand/Child", show=False),
    ]

    def __init__(
        self,
        roots: list[CCTreeNode],
        session_id: str | None = None,
        session_file: str | None = None,
    ) -> None:
        super().__init__()
        self.cc_roots = roots
        self.session_id = session_id
        self.session_file = session_file
        self._current_node: CCTreeNode | None = None
        # Map textual tree node IDs to our CCTreeNode
        self._node_map: dict[int, CCTreeNode] = {}

    def compose(self) -> ComposeResult:
        session_label = self.session_id[:12] + "..." if self.session_id and len(self.session_id) > 12 else (self.session_id or "unknown")
        yield Header(show_clock=False)
        yield Container(id="tree-container")
        yield NodeDetail(id="detail")
        yield Footer()

    def on_mount(self) -> None:
        container = self.query_one("#tree-container")
        session_label = self.session_id[:12] + "..." if self.session_id and len(self.session_id) > 12 else (self.session_id or "Session")
        tree = ConversationTree(f"Session: {session_label}", id="conversation-tree")
        tree.show_root = False
        tree.guide_depth = 3

        # Populate tree from our CCTreeNode structure
        for root in self.cc_roots:
            self._add_node_to_tree(tree.root, root)

        # Expand the root so top-level nodes are visible
        tree.root.expand()
        container.mount(tree)
        tree.focus()

    def _add_node_to_tree(
        self,
        parent: TextualTreeNode[CCTreeNode],
        node: CCTreeNode,
    ) -> None:
        """Recursively add CCTreeNodes to the Textual tree."""
        has_children = len(node.children) > 0
        if has_children:
            tree_node = parent.add(
                node.display_label,
                data=node,
                expand=node.expanded,
                allow_expand=True,
            )
        else:
            tree_node = parent.add_leaf(node.display_label, data=node)

        self._node_map[tree_node.id] = node

        for child in node.children:
            self._add_node_to_tree(tree_node, child)

    # ----- Event handlers -----

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted[CCTreeNode]) -> None:
        self._current_node = event.node.data
        detail = self.query_one("#detail", NodeDetail)
        detail.update_node(self._current_node)

    def on_tree_node_selected(self, event: Tree.NodeSelected[CCTreeNode]) -> None:
        """Enter key pressed — show action menu."""
        node = event.node.data
        if node is None:
            return
        self._current_node = node
        self._show_action_menu(node)

    # ----- Actions -----

    def action_quit_app(self) -> None:
        self.exit(ActionResult("cancel", None, self.session_id, self.session_file))

    def action_quick_fork(self) -> None:
        if self._current_node:
            self._do_fork(self._current_node)

    def action_quick_overwrite(self) -> None:
        if self._current_node:
            self._do_overwrite(self._current_node)

    def action_tree_down(self) -> None:
        tree = self.query_one(ConversationTree)
        tree.action_cursor_down()

    def action_tree_up(self) -> None:
        tree = self.query_one(ConversationTree)
        tree.action_cursor_up()

    def action_tree_left(self) -> None:
        tree = self.query_one(ConversationTree)
        node = tree.cursor_node
        if node and node.is_expanded:
            tree.action_toggle_node()
        else:
            tree.action_cursor_parent()

    def action_tree_right(self) -> None:
        tree = self.query_one(ConversationTree)
        node = tree.cursor_node
        if node and not node.is_expanded and node.allow_expand:
            tree.action_toggle_node()
        else:
            tree.action_cursor_down()

    # ----- Internal -----

    def _show_action_menu(self, node: CCTreeNode) -> None:
        def on_result(action: str | None) -> None:
            if action == "fork":
                self._do_fork(node)
            elif action == "overwrite":
                self._do_overwrite(node)

        self.push_screen(ActionMenuScreen(node), callback=on_result)

    def _do_fork(self, node: CCTreeNode) -> None:
        from .actions import fork_session
        from pathlib import Path

        session_path = Path(self.session_file) if self.session_file else None
        if not session_path:
            return

        new_path = fork_session(session_path, node.uuid)
        if new_path:
            result = ActionResult("fork", node.uuid, self.session_id, self.session_file)

            def on_dismiss(_: bool | None) -> None:
                self.exit(result)

            self.push_screen(
                ResultNotificationScreen(
                    title="Fork created successfully",
                    body=(
                        f"New session: [bold]{new_path.stem}[/bold]\n"
                        f"Saved to: {new_path.name}"
                    ),
                    hint=f"Resume with:  claude --resume {new_path.stem}",
                ),
                callback=on_dismiss,
            )
        else:
            self.notify("Fork failed — node not found", severity="error")

    def _do_overwrite(self, node: CCTreeNode) -> None:
        count = self._count_descendants(node)

        def on_confirm(confirmed: bool | None) -> None:
            if not confirmed:
                return

            from .actions import overwrite_session
            from pathlib import Path

            session_path = Path(self.session_file) if self.session_file else None
            if not session_path:
                return

            backup_path = overwrite_session(session_path, node.uuid)
            if backup_path:
                result = ActionResult("overwrite", node.uuid, self.session_id, self.session_file)

                def on_dismiss(_: bool | None) -> None:
                    self.exit(result)

                self.push_screen(
                    ResultNotificationScreen(
                        title="Overwrite complete",
                        body=(
                            f"Removed [bold]{count}[/bold] message(s) after selected point.\n"
                            f"Backup saved: {backup_path.name}"
                        ),
                        hint=f"Resume with:  claude --resume {self.session_id}",
                    ),
                    callback=on_dismiss,
                )
            else:
                self.notify("Overwrite failed — node not found", severity="error")

        self.push_screen(ConfirmOverwriteScreen(count), callback=on_confirm)

    def _count_descendants(self, node: CCTreeNode) -> int:
        count = 0
        for child in node.children:
            count += 1
            count += self._count_descendants(child)
        return count
