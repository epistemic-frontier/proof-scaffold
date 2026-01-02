$( M0.2 Step 07 — non-exported label reference should fail early. $)

$c wff ( ) -> $.
$v ph ps $.

wph $f wff ph $.
wps $f wff ps $.

${
  $[ 07_unit_private.mm $]
$}

$( Attempt to use a private/internal label from another unit — invalid. $)
use_private $p wff ps $=
  priv_helper
$.
