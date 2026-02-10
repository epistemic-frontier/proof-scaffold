# ProofScaffold

A layered, sanity-checked scaffold for building **modular Metamath** artifacts.

ProofScaffold treats **Python as the builder** (compiler/linker) and **Metamath as the verifier** (semantic authority).
It follows a **Transient Monolith** strategy: build modular packages into IR (LIR), then concatenate them into an **ephemeral `.mm`** file for verification by one or more verifiers (e.g. `metamath-exe`, `mmverify`, `metamath-knife`).

Install: `pip install proof-scaffold`  
Import: `import skfd`  
CLI: `python -m skfd.cli ...` (or `skfd ...` if installed)

> Note: the PyPI distribution name is `proof-scaffold`, while the Python import package is `skfd`.

---

## Why ProofScaffold

If you are maintaining a growing Metamath codebase, ProofScaffold aims to make it:

- **Modular by construction**: proofs live in explicit Python packages with declared dependencies.
- **Traceable**: symbol interning + origin tracking keep generated artifacts debuggable.
- **Sanity-checked**: the builder can enforce invariants before invoking verifiers.
- **Verifier-agnostic**: run multiple verifiers consistently via a single config (`.skfd`).
- **Deterministic**: canonical builds enable stable caching and reproducible verification.

---

## Unicode authoring, canonical builds

Proofs are authored in **Unicode** (e.g. `¬`, `→`, `∨`, `∧`) for readability.
Internally, the builder **canonicalizes** formulas into a stable ASCII representation for IR, caching, and verifier interop.

Canonicalization is deterministic and whitespace-insensitive: the same formula always maps to the same canonical token stream.

---

## Quickstart

```bash
pip install proof-scaffold
mkdir my-proofs
cd my-proofs
python -m skfd.cli init-pkg my-proofs
python -m skfd.cli doctor check
python -m skfd.cli verify my-proofs
````

This will:

1. Discover all `build.py` files under `src/`.
2. Topologically sort packages by declared deps.
3. Build each package in memory (LIR).
4. Emit `target/<project-name>_full.mm` (Transient Monolith).
5. Run configured verifiers (if available).

> Tip: `my-proofs` is a **project name** (from `pyproject.toml` → `[project].name`).
> `verify <project-name>` targets that project’s build unit (and its dependency closure).

---

## Example: a tiny proof script

```python
from logic.propositional.hilbert import HilbertSystem
from logic.propositional.hilbert.lemmas import LemmaBuilder, LemmaProof

def prove_modus_tollens(sys: HilbertSystem) -> LemmaProof:
    """Modus Tollens: φ → ψ, ¬ψ ⊢ ¬φ."""
    lb = LemmaBuilder(sys, "modus_tollens")

    h1 = lb.hyp("h1", "φ → ψ")
    h2 = lb.hyp("h2", "¬ψ")

    s1 = lb.ref("s1", "(φ → ψ) → (¬ψ → ¬φ)", ref="con3", note="con3")
    s2 = lb.mp("s2", h1, s1, note="MP h1, s1")
    s3 = lb.mp("s3", h2, s2, note="MP h2, s2")

    return lb.build(s3)
```

Verify:

```bash
python -m skfd.cli verify <project-name>
```

For a larger proof that showcases lifting/distribution patterns and origin tracking, see `examples/`.

---

## Concepts and layout

### Terminology

* **Project**: a ProofScaffold workspace root (contains `pyproject.toml` + `src/`).
* **Build unit**: what `skfd verify` targets; named by `pyproject.toml` → `[project].name`.
* **Package (Python)**: the import package under `src/<name>/` (often `<project-name>` with `-` → `_`).
* **Driver**: resolves deps, builds packages, emits transient monolith `.mm`.
* **LIR**: the builder’s intermediate representation emitted by packages.

### Key components

#### 1) Generic Logic Driver (`skfd.driver`)

Manages the build lifecycle of logic packages.

* **Explicit dependencies**: packages declare deps in `build.py` (e.g. `metamath-prelude`, `metamath-logic`).
* **No implicit globals**: dependencies are injected by the driver.
* **Primary command**: `python -m skfd.cli verify <project-name>`

#### 2) Builder API (`skfd.builder`)

A fluent Python API for constructing Metamath databases.

* Atomic LIR generation.
* Symbol interning + origin tracking (for debuggability).

#### 3) Engineering standards (`AGENT.md`)

CI-enforced discipline:

* Ruff (lint/format)
* MyPy (strict typing)
* Pytest

See [`AGENT.md`](./AGENT.md) for the contributor protocol.

---

## Verifier configuration (`.skfd`)

ProofScaffold can run multiple verifiers in a single `verify` pass. The active set is controlled by `.skfd`.

### Minimal config (single verifier)

Example: only `metamath-exe` (adapt `command` to your environment)

```toml
active = ["metamath-exe"]

[verifiers.metamath-exe]
command = "metamath"
args = ["target/<project-name>_full.mm"]
```

### Advanced config (multiple verifiers + shims)

Example (mmverify + metamath-knife + metamath-exe + shim):

```toml
active = ["mmverify", "metamath-knife", "metamath-exe"]

[verifiers.metamath-knife]
command = "../metamath-knife/target/release/metamath-knife"
args = ["--verify"]

[verifiers.metamath-exe]
command = "/usr/bin/env"
args = [
  "METAMATH_BIN=../metamath-exe/src/metamath",
  "./.venv/bin/python",
  "./verifier/shims/metamath.py"
]
```

Environment check:

```bash
python -m skfd.cli doctor check
```

---

## Usage

### Dev mode vs. user mode

**User mode (installed via PyPI)**

* Dependencies are installed packages; no `PYTHONPATH` needed.
* `.skfd` can be minimal and extended only if desired.
* Typical usage: `python -m skfd.cli verify <project-name>`.

**Dev mode (multi-repo / local path deps)**

* Repos may live side-by-side; dependencies can be pulled via local path (e.g. `uv` sources).
* You may need `PYTHONPATH` depending on your workspace layout.
* `.skfd` often points to local binaries and shims (multi-verifier runs).

### Initialize a project

**Package mode:** creates `src/` + `pyproject.toml` + `.skfd`

```bash
mkdir my-proofs
cd my-proofs
python -m skfd.cli init-pkg my-proofs
```

**Standalone proof script:** creates `my_proof.py` (no `src/`)

```bash
python -m skfd.cli init-proof my_proof.py
```

### Build & verify a project

```bash
python -m skfd.cli verify <project-name>

### Browse theorem dependency chains (local web)
```bash
python -m skfd.cli serve <project-name> --port 8000
```

Then open http://127.0.0.1:8000/ and search/click assertions to inspect direct and reverse dependencies.
```

---


Run tests:

```bash
pytest
```

If you use `uv`:

```bash
uv run pytest
```

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for development workflow and contribution guidelines.

---

## Documentation

Start here:

* `projects/009-logic_driver.md` — driver design, IR, and the Transient Monolith strategy.
* `examples/` — minimal and larger proof examples.
* `src/skfd/` — core toolchain implementation.

---

## License

See `LICENSE`.
