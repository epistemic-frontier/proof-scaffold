$( Step 05 (failure): Missing an essential hypothesis. $)

$c wff -> ( ) $.
$v ph ps $.

ph $f wff ph $.
ps $f wff ps $.

h1 $e wff ph $.
h2 $e wff ( ph -> ps ) $.

ax-mp $a wff ps $.

$( Wrong proof: provides only h1, but ax-mp needs both h1 and h2. $)
th_mp $p wff ps $=
  ph ps h1 ax-mp
$.
