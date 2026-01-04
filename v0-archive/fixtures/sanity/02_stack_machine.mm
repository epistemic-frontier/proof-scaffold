$( Step 02 - Stack machine sanity fixture
   This fixture is designed to demonstrate that Metamath proofs
   execute as stack programs.
$)

$c wff ( ) -> |- $.

$v ph ps $.

$( Typing hypotheses $)
wph $f wff ph $.
wps $f wff ps $.

$( Axiom with two variables $)
ax-1 $a |- ( ph -> ( ps -> ph ) ) $.

$( End of fixture. A $p statement will be appended by the companion program. $)
