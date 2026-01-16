# Engineering Standards & Agent Protocol

This document serves as the **Single Source of Truth** for engineering standards and protocols for this project. Any AI Agent working on this codebase MUST strictly adhere to these guidelines.

## 1. Toolchain & Environment (`uv`)

We use **[uv](https://github.com/astral-sh/uv)** for fast, reliable Python package management.

*   **Virtual Environment**: Always operate within the `.venv` managed by `uv`.
*   **Dependency Management**:
    *   Add runtime usage: `uv pip install <package>` (and update `pyproject.toml` dependencies if needed).
    *   Add dev usage: `uv pip install <package>` (and update `[project.optional-dependencies] dev`).
*   **Running Commands**: Prefer invoking tools via `sys.executable` or `python3` within the active venv to avoid path issues.
    *   Correct: `python3 -m pytest`
    *   Incorrect: `pytest` (if relying on global or unverified PATH)

## 2. Code Style & Quality (`ruff`)

We use **[Ruff](https://docs.astral.sh/ruff/)** for both linting and formatting.

*   **Configuration**: Defined in `pyproject.toml` under `[tool.ruff]`.
*   **Enforcement**:
    *   **Lint**: `ruff check .` (Selected rules: E, F, I, B, UP)
    *   **Format**: `ruff check --fix .` (Auto-fix imports via I001)
*   **Agent Rule**:
    *   Before submitting any code or finishing a task, run: `ruff check .`
    *   If errors exist, fix them immediately. Do not ask for user permission to fix lint errors.

## 3. Static Typing (`mypy`)

We use **[MyPy](https://mypy-lang.org/)** in **Strict Mode**.

*   **Configuration**: `[tool.mypy]` in `pyproject.toml` (`strict = true`).
*   **Constraint**:
    *   All new code MUST be fully typed.
    *   Use `from __future__ import annotations`.
    *   Avoid `Any` unless absolutely necessary.
    *   **Never** leave `type: ignore` comments unless you have a specific, documented reason that is verified to be unavoidable.
*   **Agent Rule**:
    *   Run `mypy .` after any code change.
    *   If you see `Call to untyped function "..." in typed context`, you likely missed a `-> None` or return type annotation. Fix it.

## 4. Testing (`pytest`)

We use **[pytest](https://docs.pytest.org/)**.

*   **Structure**: Tests live in `tests/`.
*   **Invocation**: `python3 -m pytest` (avoids `sys.path` issues).
*   **Agent Rule**:
    *   **Regression**: Always run relevant tests before and after changes.
    *   **New Features**: Every new feature MUST have a corresponding test in `tests/`.
    *   **Golden Rule**: If you fix a bug, add a regression test case first.

## 5. Project Layout

We follow the **`src`-layout** convention.

*   **Source**: `src/<package>/...`
*   **Tests**: `tests/`
*   **Build Artifacts**: `target/` or `build/` (Never verify in-place source files).

## 6. Agent Behavior Protocol

1.  **Be Proactive**: If you break the build (lint/type/test), fix it immediately.
2.  **Verify First**: Do not assume your code works. Run the `verify` CLI or tests.
3.  **No Magic**: Avoid implicit behaviors. e.g., in Project 009, we moved to *explicit* dependencies in `build.py` to avoid "magic" prelude loading.
4.  **Ephemerality**: Build artifacts (`.mm` files) are transient. Do not commit them.

---
*Last Updated: 2026-01-16*
