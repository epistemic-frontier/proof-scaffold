$( Step 05 (happy): Modus Ponens works. $)

$c wff -> ( ) $.
$v ph ps $.

ph $f wff ph $.
ps $f wff ps $.

${

  $( Essential hypotheses for modus ponens. $)
  h1 $e wff ph $.
  h2 $e wff ( ph -> ps ) $.

  $( Modus ponens rule: from ph and (ph -> ps) infer ps. $)
  ax-mp $a wff ps $.

  $( A minimal theorem that uses ax-mp. $)
  th_mp $p wff ps $=
    ph ps h1 ax-mp
  $.

$}

