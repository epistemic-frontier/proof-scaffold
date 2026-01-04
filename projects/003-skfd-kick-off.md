# SKFD: The ProofScaffold CLI (Status: Implemented)

## 1. Philosophy
`skfd` is the primary interface for ProofScaffold. It manages the lifecycle of proof projects, from initialization to verification. It behaves like a modern toolchain (git, cargo, npm).

**Core Principles:**
- **Verbs over Flags**: `skfd build` instead of `skfd --build`.
- **Project-Centric**: Commands operate on the current project context (looking for `pyproject.toml` or `scaffold.toml`).
- **Determinism**: Default to deterministic outputs.

## 2. Command Structure

### Global Options
- `-v, --verbose`: Enable detailed logging.
- `-q, --quiet`: Suppress non-error output.
- `--root <PATH>`: Specify project root (default: current directory).

### Subcommands

#### `init`
Initialize a new ProofScaffold project.
```bash
skfd init my-proofs
```
- Creates directory structure (`src/`, `tests/`).
- Generates `pyproject.toml` with `proof-scaffold` dependency.

#### `build` (formerly `smoke`/`link`)
Compile the project's proofs into Metamath artifacts.
```bash
skfd build [target]
```
- Scans for proof units.
- Links them using `LinkerV1`.
- Outputs `.mm` files to `build/`.

#### `verify`
Run the Metamath verifier on generated artifacts.
```bash
skfd verify [file]
```
- If no file specified, verifies all artifacts in `build/`.
- Wraps `verifier` module.

#### `doctor` (formerly `smoke`)
Check the environment and toolchain health.
```bash
skfd doctor
```
- **Environment**: Checks Python version, dependencies.
- **Sanity**: Runs internal `check_sanity` (the old `smoke` test).
- **Diagnostics**: Reports if the installation is broken or if external tools are missing.

## 3. Implementation Plan

### 3.1 `cli.py` Structure
Use `argparse` with sub-parsers.

```python
# src/proof_scaffold/cli.py

def main():
    parser = argparse.ArgumentParser(prog="skfd")
    subs = parser.add_subparsers(dest="cmd")
    
    # ... register commands ...
    
    args = parser.parse_args()
    # ... dispatch ...
```

### 3.2 Entry Point Registration
In `pyproject.toml`:
```toml
[project.scripts]
skfd = "proof_scaffold.cli:main"
```

## 4. Migration Strategy
1. Implement `cli.py`.
2. Register `skfd`.
3. Validated `skfd doctor` works.
4. Implement `skfd init` / `skfd build` (future).
