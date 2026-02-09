from collections.abc import Mapping

from skfd.authoring.emit import emit_axioms
from skfd.authoring.formula import Wff
from skfd.builder_v2 import MMBuilderV2
from skfd.core.lir import Axiom, FloatingHyp
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.names import NameResolver


class _Provider:
    def __init__(self, interner: SymbolInterner, axioms: Mapping[str, Wff]) -> None:
        self.interner = interner
        self._axioms = dict(axioms)

    def compile_axioms(self) -> Mapping[str, Wff]:
        return dict(self._axioms)


def test_emit_axioms_v2_uses_symbol_ids_and_auto_f() -> None:
    interner = SymbolInterner()
    mm = MMBuilderV2(
        interner=interner,
        origin_table=OriginTable(),
        names=NameResolver(),
        unit_id="u",
        origin_module_id="m",
    )
    wff = mm.sym.const("wff")
    ph = mm.sym.var("φ")

    provider = _Provider(interner, {"ax-1": Wff("wff", (ph,))})
    emit_axioms(mm, provider, typecode=wff)
    unit = mm.finish()

    assert any(isinstance(s, FloatingHyp) for s in unit.lir_stmts)
    assert any(isinstance(s, Axiom) for s in unit.lir_stmts)

