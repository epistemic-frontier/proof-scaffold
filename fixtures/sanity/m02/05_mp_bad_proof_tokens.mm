$( Step 05 (failure): Hypotheses are provided in the wrong order. $)

$c wff -> ( ) $.
$v ph ps $.

ph $f wff ph $.
ps $f wff ps $.

h1 $e wff ph $.
h2 $e wff ( ph -> ps ) $.

ax-mp $a wff ps $.

$( Wrong proof: h2 and h1 are swapped. Order matters in the stack machine. $)
th_mp $p wff ps $=
  ph ps h2 h1 ax-mp
$.
