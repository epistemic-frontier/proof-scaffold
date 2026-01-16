
from skfd.core.lir import Axiom, ConstDecl
from skfd.core.origin import OriginRecord, OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.core.unit import ProofUnitIR
from skfd.linker.api import LinkerV1


def test_source_map_basic_mapping() -> None:
    ot = OriginTable()
    interner = SymbolInterner()
    
    # 1. Setup Interner & Origins
    # Origin 1: File A, Line 10 (Const definition)
    orig_1 = ot.intern(OriginRecord(module_id="mod", file="a.py", line=10))
    # Origin 2: File A, Line 20 (Axiom definition)
    orig_2 = ot.intern(OriginRecord(module_id="mod", file="a.py", line=20))
    
    c_wff = interner.intern(
        origin_module_id="mod", local_name="wff", kind="Const", origin_ref=orig_1
    )
    l_ax = interner.intern(
        origin_module_id="mod", local_name="ax1", kind="Label", origin_ref=orig_2
    )
    
    # 2. Construct Unit
    unit = ProofUnitIR(
        unit_id="test_unit",
        origin_ref=orig_1,
        origin_module_id="mod",
        lir_stmts=[
            ConstDecl(1, orig_1, [c_wff]),
            # Axiom at origin 2
            Axiom(2, orig_2, l_ax, c_wff, [])
        ],
        exports=[l_ax]
    )
    
    # 3. Link
    res = LinkerV1.link(units=[unit], origin_table=ot, interner=interner)
    
    # 4. Verify Content
    # Expected output roughly:
    # $c wff $.  <-- Line 1
    # ax1 $a wff $. <-- Line 2 or 3 depending on preamble/vars
    
    mm_lines = res.mm_text.splitlines()
    assert "$c wff $." in mm_lines[0]
    
    # 5. Verify Map
    # We expect SourceMapEntry for the Axiom.
    # ConstDecl is in header, currently emit_mm handles header.
    # Does emit_mm map header?
    # Inspect emit_mm: 
    #   const_names = ...
    #   if const_names: out.append(...) -> No map entry added for header currently!
    #   Body Frames -> Axiom -> maps start_line.
    
    # So we expect a map entry for the Axiom.
    # Find line index of axiom.
    ax_line_idx = -1
    for i, line in enumerate(mm_lines):
        if "ax1 $a" in line:
            ax_line_idx = i
            break
            
    assert ax_line_idx != -1
    ax_line_num = ax_line_idx + 1  # 1-based
    
    # Check entries
    entries = res.source_map.entries
    # Filter for Axiom's origin
    matches = [e for e in entries if e.origin == orig_2]
    
    assert len(matches) > 0, "Axiom origin not found in source map"
    # The map entry should point to the line where axiom starts
    assert matches[0].line == ax_line_num
    
    # Verify JSON serialization
    json_data = res.source_map.to_json()
    assert isinstance(json_data, list)
    assert json_data[0]["origin_ref"] == orig_2
