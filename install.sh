#!/bin/bash
#
# cctree — Install script
#
# Symlinks the cctree command, skill, and package into ~/.claude/
# so it's available globally across all Claude Code sessions.
#
# Usage:
#   ./install.sh            # Install (symlink mode)
#   ./install.sh --check    # Verify installation
#   ./install.sh --uninstall # Remove symlinks
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${HOME}/.claude"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Parse arguments
MODE="install"
case "${1:-}" in
    --check)   MODE="check" ;;
    --uninstall) MODE="uninstall" ;;
    --help|-h)
        echo "Usage: $0 [--check|--uninstall]"
        echo ""
        echo "  (default)    Install cctree into ~/.claude/"
        echo "  --check      Verify installation is working"
        echo "  --uninstall  Remove cctree from ~/.claude/"
        exit 0
        ;;
esac

# ---- Check Python ----
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}Error: Python not found. Install Python 3.10+${NC}"
        exit 1
    fi

    VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    MAJOR=$(echo "$VERSION" | cut -d. -f1)
    MINOR=$(echo "$VERSION" | cut -d. -f2)

    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
        echo -e "${RED}Error: Python 3.10+ required, found $VERSION${NC}"
        exit 1
    fi
    echo -e "${GREEN}Python $VERSION${NC}"
}

# ---- Uninstall ----
if [ "$MODE" = "uninstall" ]; then
    echo "Removing cctree from ~/.claude/..."
    for item in commands/tree.md skills/conversation-tree scripts/cctree; do
        target="${CLAUDE_DIR}/${item}"
        if [ -L "$target" ]; then
            rm "$target"
            echo -e "  ${GREEN}Removed${NC} $target"
        elif [ -e "$target" ]; then
            echo -e "  ${YELLOW}Skipped${NC} $target (not a symlink — remove manually)"
        fi
    done
    echo -e "${GREEN}Done.${NC}"
    exit 0
fi

# ---- Check ----
if [ "$MODE" = "check" ]; then
    echo "Checking cctree installation..."
    OK=true

    check_python

    for item in commands/tree.md skills/conversation-tree scripts/cctree; do
        target="${CLAUDE_DIR}/${item}"
        if [ -L "$target" ] || [ -e "$target" ]; then
            echo -e "  ${GREEN}OK${NC}  $target"
        else
            echo -e "  ${RED}MISSING${NC}  $target"
            OK=false
        fi
    done

    if $PYTHON_CMD -c "import textual" 2>/dev/null; then
        echo -e "  ${GREEN}OK${NC}  textual installed"
    else
        echo -e "  ${RED}MISSING${NC}  textual (pip install textual)"
        OK=false
    fi

    if $OK; then
        echo -e "\n${GREEN}Installation OK.${NC} Try: /tree"
    else
        echo -e "\n${RED}Issues found.${NC} Re-run ./install.sh to fix."
    fi
    exit 0
fi

# ---- Install ----
echo "Installing cctree into ~/.claude/..."
echo ""

check_python

# Ensure target directories exist
mkdir -p "${CLAUDE_DIR}/commands"
mkdir -p "${CLAUDE_DIR}/skills"
mkdir -p "${CLAUDE_DIR}/scripts"

# Helper: create or update symlink
link_item() {
    local source="$1"
    local target="$2"
    local label="$3"

    if [ -L "$target" ]; then
        rm "$target"
    elif [ -e "$target" ]; then
        echo -e "  ${YELLOW}Warning${NC}: $target exists and is not a symlink. Skipping."
        return
    fi

    ln -s "$source" "$target"
    echo -e "  ${GREEN}Linked${NC}  $label"
}

# Symlink command
link_item "${SCRIPT_DIR}/commands/tree.md" "${CLAUDE_DIR}/commands/tree.md" "commands/tree.md"

# Symlink skill
link_item "${SCRIPT_DIR}/skills/conversation-tree" "${CLAUDE_DIR}/skills/conversation-tree" "skills/conversation-tree/"

# Symlink cctree package
link_item "${SCRIPT_DIR}/cctree" "${CLAUDE_DIR}/scripts/cctree" "scripts/cctree/"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
if $PYTHON_CMD -m pip install textual --quiet 2>/dev/null; then
    echo -e "  ${GREEN}OK${NC}  textual installed"
elif $PYTHON_CMD -m pip install textual --user --quiet 2>/dev/null; then
    echo -e "  ${GREEN}OK${NC}  textual installed (user mode)"
else
    echo -e "  ${YELLOW}Warning${NC}: could not auto-install textual"
    echo "  Run manually: pip install textual"
fi

echo ""
echo -e "${GREEN}Installation complete.${NC}"
echo ""
echo "Usage:"
echo "  /tree                        Launch tree for current session"
echo "  /tree --session <id>         Launch tree for a specific session"
echo "  python -m cctree --help      Standalone CLI usage"
echo ""
echo "Verify with: ./install.sh --check"
