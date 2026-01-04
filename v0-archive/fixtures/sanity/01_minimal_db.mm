$( Step 01 - Minimal Metamath database fixture
   This fixture introduces the smallest meaningful structure:
   constants, variables, typing hypotheses, and axioms.
$)

$c wff ( ) -> |- $.

$v ph $.

$( Typing hypothesis: ph is a well-formed formula $)
wph $f wff ph $.

$( Trivial axiom: ph -> ph $)
ax-id $a |- ( ph -> ph ) $.

$( End of fixture. A $p theorem will be appended by the companion script. $)
