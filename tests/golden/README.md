# Golden tests

This directory is reserved for **fixed input → fixed output** tests.

In later milestones we will commit small IR inputs (or generators) and assert:

- emitted `.mm` is byte-identical across runs,
- relocation snapshots are deterministic,
- diagnostics strings are deterministic.

M0.2 only establishes the directory boundary and conventions.

