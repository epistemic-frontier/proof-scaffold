from skfd.builder import MMBuilder
from skfd.core.errors import MMDSLError
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner


def _mk_builder() -> MMBuilder:
    return MMBuilder(interner=SymbolInterner(), origin_table=OriginTable(), module_id="t")


def test_builder_c_empty_raises() -> None:
    mm = _mk_builder()
    try:
        mm.c()
    except MMDSLError:
        return
    raise AssertionError("expected MMDSLError")


def test_builder_v_empty_raises() -> None:
    mm = _mk_builder()
    try:
        mm.v()
    except MMDSLError:
        return
    raise AssertionError("expected MMDSLError")


def test_builder_undeclared_token_raises() -> None:
    mm = _mk_builder()
    mm.c("wff")
    try:
        mm.a("ax1", "wff", "X")
    except MMDSLError:
        return
    raise AssertionError("expected MMDSLError")


def test_builder_unknown_proof_label_raises() -> None:
    mm = _mk_builder()
    mm.c("wff").v("v0").f("w_v0", "wff", "v0").a("ax", "wff", "v0")
    try:
        mm.p("th1", "wff", "v0", ["ax", "missing"])
    except MMDSLError:
        return
    raise AssertionError("expected MMDSLError")


def test_builder_import_symbols_duplicate_raises() -> None:
    mm = _mk_builder()
    mm.import_symbols(ax=123)
    try:
        mm.import_symbols(ax=456)
    except MMDSLError:
        return
    raise AssertionError("expected MMDSLError")


def test_builder_import_symbols_conflict_local_decl_raises() -> None:
    mm = _mk_builder()
    mm.c("t0")
    try:
        mm.import_symbols(t0=123)
    except MMDSLError:
        return
    raise AssertionError("expected MMDSLError")


def test_builder_export_unknown_symbol_raises() -> None:
    mm = _mk_builder()
    try:
        mm.export("missing")
    except MMDSLError:
        return
    raise AssertionError("expected MMDSLError")


def test_builder_export_imported_symbol() -> None:
    mm = _mk_builder()
    mm.import_symbols(ax=123).export("ax")
    unit = mm.to_proof_unit("u")
    assert 123 in unit.exports


def test_builder_d_requires_two_vars() -> None:
    mm = _mk_builder()
    try:
        mm.d("A")
    except MMDSLError:
        return
    raise AssertionError("expected MMDSLError")


def test_builder_d_requires_declared_vars() -> None:
    mm = _mk_builder()
    mm.c("wff").v("A")
    try:
        mm.d("A", "B")
    except MMDSLError:
        return
    raise AssertionError("expected MMDSLError")


def test_builder_unbalanced_scope_pop_raises() -> None:
    mm = _mk_builder()
    try:
        mm._pop_scope()
    except MMDSLError:
        return
    raise AssertionError("expected MMDSLError")


def test_builder_proof_symbol_id_step() -> None:
    mm = _mk_builder()
    mm.c("wff").v("v0").f("w_v0", "wff", "v0").a("ax", "wff", "v0")
    mm.p("th1", "wff", "v0", [999])
    out = mm.render()
    assert "ID<999>" in out
