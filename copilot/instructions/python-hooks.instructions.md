---
applyTo: "**/*.py,**/*.pyi,**/pyproject.toml"
---

# Python Hooks

> This file extends [common/hooks.md](../common/hooks.md) with Python specific content.

## PostToolUse Hooks

Configure in `~/.claude/settings.json`:

- **ruff format**: Auto-format `.py` files after edit (`hooks/post-edit-format.sh` does this when `ruff` is installed)
- **ruff check**: Lint the edited file
- **mypy**: Type-check the package after a batch of edits
