# ProofScaffold

A layered, sanity-checked scaffold for building modular Metamath artifacts.

This repository treats Python as the builder (compiler/linker) and Metamath as the verifier (semantic authority).
We follow a **Transient Monolith** verification strategy: explicit Python packages (`skfd.driver`) generate intermediate representations (LIR), which are concatenated into ephemeral `.mm` files for verification by `metamath-exe`.

## Quickstart

**Requirements**:
- Python >= 3.10
- [uv](https://github.com/astral-sh/uv) (Recommended)
- [metamath-exe](https://github.com/metamath/metamath-exe) (Optional, for verification)

**Installation**:

```bash
# Install dependencies (including dev tools)
uv pip install -e .[dev]

# Check environment health
python3 -m skfd.cli doctor
```

## Key Components

### 1. Generic Logic Driver (`skfd.driver`)

Manages the build lifecycle of logic packages.
- **Explicit Dependencies**: Packages declare deps in `build.py` (e.g., `prelude`, `logic`).
- **No Implicit Globals**: The driver injects dependencies explicitly.
- **Subcommand**: `skfd verify <package>`

### 2. Builder API (`skfd.builder`)

A fluent Python API for constructing Metamath databases.
- Supports atomic LIR generation.
- Handles symbol interning and origin tracking automatically.

### 3. Engineering Standards (`AGENT.md`)

We adhere to strict engineering standards enforced by CI:
- **Lint/Format**: Ruff
- **Typing**: MyPy (Strict)
- **Testing**: Pytest

See [AGENT.md](./AGENT.md) for the full protocol.

## Usage

### Run Tests
```bash
python3 -m pytest
```

### Build & Verify Logic
```bash
# Verify the 'logic' package (and its 'prelude' dependency)
python3 -m skfd.cli verify logic
```

This will:
1.  Discover all `build.py` files in `src/`.
2.  Topologically sort dependencies.
3.  Build each package in memory.
4.  Generate `target/logic_full.mm` (Transient Monolith).
5.  Run `metamath-exe` (if available).

## Documentation

- `projects/009-logic_driver.md`: Driver Design & Verification Strategy.
- `src/skfd/`: Core Toolchain Source.
- `examples/`: Minimal usage examples.
