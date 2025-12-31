$( Step 00 — Environment sanity fixture
   This file defines the smallest Metamath database that can be
   successfully verified after appending a trivial $p proof.
$)

$c wff ( ) -> |- $.

$v ph $.

$( Typing hypothesis: ph is a well-formed formula $)
wph $f wff ph $.

$( Trivial axiom: ph -> ph $)
ax-id $a |- ( ph -> ph ) $.

$( End of fixture. A $p theorem will be appended by the companion script. $)
