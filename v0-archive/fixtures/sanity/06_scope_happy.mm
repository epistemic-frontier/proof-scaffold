$( 06_scope_happy.mm - scoped block is well-formed and non-leaking. $)

$c wff ( ) -> $.
$v ph ps $.

wph $f wff ph $.
wps $f wff ps $.

${
  $( Local hypotheses + local MP axiom + local theorem. $)
  l1 $e wff ph $.
  l2 $e wff ( ph -> ps ) $.
  ax-mp-local $a wff ps $.

  tlocal $p wff ps $=
    wph wps l1 l2 ax-mp-local
  $.
$}

${
  $( Global MP hypotheses + global MP axiom. $)
  g1 $e wff ph $.
  g2 $e wff ( ph -> ps ) $.
  ax-mp $a wff ps $.

  $( Outside the block: prove using the global MP axiom. $)
  th_out $p wff ps $= wph wps g1 g2 ax-mp
  $.
$}
