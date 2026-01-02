# Sanity 07 — Multi-Unit Linking (Technical Notes)

This note details the verifier-level behavior for the Step 07 sanity checks covering minimal multi-unit linkage via Metamath includes ($[ ... $]).

## Scope and Goals

- Demonstrate that an exported assertion ($a/$p) from one unit can be referenced by another
- Show that referencing non-exported labels across units must fail
- Illustrate a minimal cycle scenario and why it is invalid
- Align with linter constraints (includes at top level; balanced scopes)

## Fixtures Overview

All files live under fixtures/sanity.

1) 07_two_units_happy.mm

- Includes two units at the top level:
  - 07_unit_mp.mm — defines ax-mp $a wff ps $. (top-level)
  - 07_unit_thm.mm — defines a theorem t_from_units $p wff ps $ inside a local block; the proof uses ax-mp.
- Mandatory $f are declared in the aggregator file (wph/wps). The theorem consumes whatever its referenced $a requires (here: only wps).

2) 07_cycle.mm

- Includes 07_unit_a_cycle.mm and 07_unit_b_cycle.mm. Each unit references the other's theorem label, creating a cycle.
- Verifier behavior: rejection due to unresolved forward dependency; a proper linker must detect the cycle in the unit DAG.

3) 07_non_exported_label_ref.mm

- Includes 07_unit_private.mm, which defines a local helper label.
- The outer file attempts to reference this helper directly; verifiers should reject such non-exported cross-unit references.

## Linter and Shim Considerations

- Includes are placed at the top level to satisfy metamath-knife's structure checks.
- The Metamath shim used here quotes the READ path and runs with cwd set to the repository root; this ensures relative include paths in fixtures resolve consistently with metamath-knife.

## Design Note: Keeping Logic Minimal

To focus on linking mechanics rather than logic, 07_unit_mp.mm provides a minimal axiom without $e. The theorem unit, 07_unit_thm.mm, proves t_from_units using only mandatory $f and the imported axiom label. This keeps the Step 07 signal clear:

- exported labels are usable across units,
- private/internal labels are not,
- cycles are invalid.

Further steps may reintroduce richer dependencies (e.g., $e hypotheses, $d constraints) once the linking shape is understood.
