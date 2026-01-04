$( Step 03 - Mandatory $f hypotheses fixture
   This fixture is used to test that required $f labels can be computed
   for an assertion that mentions multiple variables.
$)

$c wff ( ) -> |- $.

$v ph ps $.

wph $f wff ph $.
wps $f wff ps $.

ax-1 $a |- ( ph -> ( ps -> ph ) ) $.
