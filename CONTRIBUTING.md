# Contributing to Apple Container MCP Server

Thank you for your interest in contributing! This project is a bridge between MCP and Apple's `container` CLI.

## Developer Setup

1. **Install Prerequisites**:
   - Python 3.11+
   - [uv](https://github.com/astral-sh/uv) package manager
   - Apple's `container` service (and ensure `container system start` is run)

2. **Clone and Install**:

   ```bash
   git clone https://github.com/joeshirey/AppleContainerMCP.git
   cd AppleContainerMCP
   uv sync --dev
   ```

3. **Running Tests**:
   We use `pytest` for unit testing.

   ```bash
   uv run pytest tests/
   ```

4. **Linting**:
   We use `ruff` to maintain code quality.

   ```bash
   uv run ruff check src/
   ```

5. **Local FastMCP Dev**:
   You can inspect the server interactively using the MCP inspector:

   ```bash
   uv run mcp dev src/apple_container_mcp/server.py
   ```

## Workflow

1. Create a branch for your fix/feature.
2. Ensure existing tests pass and add new tests if applicable.
3. Run linting to ensure standards are met.
4. Submit a Pull Request.

## Code Style

- Use Python 3.11+ type annotations.
- Follow the existing project structure (`src/apple_container_mcp/`).
- Ensure all MCP tools return standardized JSON shapes: `{"status": "ok/error", ...}`.
