# SKFD: Multi-Verifier Support (Status: Implemented)

## 1. Motivation
The ProofScaffold toolchain should be agnostic to the underlying Metamath verifier. Different users may prefer different verifiers (Metamath C, mmverify.py, metamath-knife) based on performance or availability.

We need a standard way to:
1.  **Register** multiple verifiers.
2.  **Select** the active verifier for a project or globally.
3.  **Manage** this configuration via `skfd`.

## 2. Configuration: `.skfd`

We will introduce a TOML-based configuration file `.skfd`.

### Schema

```toml
# List of verifiers to run by default.
# All verifiers listed here will be executed in order.
active = ["mmverify", "metamath-c"]

[verifiers.mmverify]
command = "python3"
args = ["verifier/mmverify.py"]

[verifiers.metamath-c]
command = "metamath"
```

## 3. CLI: `skfd verifier`

### 3.1 `skfd verifier list`
Show all configured verifiers.
```text
* mmverify   -> python3 verifier/mmverify.py
* metamath-c -> metamath
```

### 3.2 `skfd verifier add <name> <command> [args...]`
1. Register a new verifier in configuration.
2. **Automatically append** `<name>` to the `active` list.
3. Save configuration.

### 3.3 `skfd verifier remove <name>`
1. Remove `<name>` from configuration.
2. Remove `<name>` from `active` list.
3. Save configuration.

### 3.4 Execution Logic
When `skfd doctor` or `skfd build` (verify step) runs:
1. Load config.
2. Iterate through all names in `active` list.
3. Run each verifier.
4. **Fail** if *any* verifier fails.


## 5. Roadmap
1.  **Phase 1**: Define Config & CLI (M0.3)
2.  **Phase 2**: Refactor `verifier` module to support command lists.
3.  **Phase 3**: Implement `skfd verifier` CRUD.
