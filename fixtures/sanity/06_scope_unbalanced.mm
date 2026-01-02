$( 06_scope_unbalanced.mm — missing closing $} must cause parse failure. $)

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
  $( Intentionally missing $} here. $)
