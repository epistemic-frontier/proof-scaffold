# Project 013: External Verifier Integration

## Motivation
To increase confidence in the generated proofs, we should validate them with established, industry-standard verification tools:
1.  **Metamath C (metamath-exe)**: The reference implementation. Slower, but the gold standard for correctness.
2.  **Metamath Knife**: A high-performance Rust verifier. Extremely fast.

The `skfd` toolchain already has a `verifier` extension point. We will register these tools into the harness.

## Goals
1.  Register `metamath-knife` and `metamath-exe` as active verifiers in the local `skfd` configuration.
2.  Verify that `skfd doctor` passes for both.
3.  Verify that `skfd verify` invokes them.

## Verification Resources
Binaries provided in user workspace:
*   `metamath-exe`: `/Users/mingli/MetaMath/metamath-exe/src/metamath`
*   `metamath-knife`: `/Users/mingli/MetaMath/verifiers/metamath-knife/target/release/metamath-knife`

## Shim Strategy
*   **Metamath Knife**: Invoke directly (`--verify`).
*   **Metamath C**: Invoke via `src/skfd/verifier/shims/metamath.py`, injecting `METAMATH_BIN` via `env`.

## Plan
1.  Verify binary executability.
2.  Run `skfd verifier add knife ...`.
3.  Run `skfd verifier add metamath ...`.
4.  Run `skfd doctor`.
5.  Run `skfd verify logic` (should take longer now!).
