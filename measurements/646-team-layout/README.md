# Complete TEAM tactics layout (#646)

[confirmed: original1771:1981→157D; F036–F038] Draft implementation restores the
shared TEAM header, skill bars, original XI caps/age and3+5tactic grouping, with
current records/order/tactics and authoritative performance-context support.
Source baseline e9dc466ecb6bdd9105d961fd4b3ee0fc9cd4a980 contains accepted640/645.
Upstream697/698 remains a required accepted/vendor dependency before completion.
No copied engine file is modified here.

before-v1-filtered.log:2own controls fail on baseline (header/grouping absent).
The raw private assertion includes a complete original-name roster; it stays in
.cache/layout646-private/before-v1-raw.log and is not published. One test assertion
was corrected before implementation to read FactsTable.values, matching its real
API; missing-header failure occurs earlier and is unchanged.

header-factor-v1.log:6unchanged header/panel testsPASS21.169s, including128countries
and three sizes. layout-focused-v1.log:13own/unchangedT202/641/636PASS6.862s,
including eight tactic inputs, current traits, pending confirmation, one actual
image parse and cursor-only presentation. context-before-v1.log:11failures across
2tests before schema/view context consumption; context-after-v1.log:2PASS1.793s.
Raw flags/both sides/current skills/performance/XI numbers use an independently
assembled original-backed Memory projection, with no career/packet writes.
These authored current-record fixtures are not naturally played proof.

Private offscreen snapshots at1440x900/1800x1125/2110x1213 show pre-match and
prepared live context; fixed_page reports no bounds problems. Final screenshot/
pixel/font controls, nativeWindows and actualworker equality still required.
No defaultfast/hosted/fullmilestone/whole611acceptance claim yet. Earlier passing
logs bind the stated source step; later injury-marker/legend addition needs its
own updated focused run. No owner game, save or installed preview touched.

Source d8f4fcc9: full focused21PASS30.876s on Linux; nativeWindows Qt/CPython3.13
21PASS45.893s with0skips. native-d8f4-v1.json binds nine changed source/test files;
fixtures are byte-verified physical copies in private WindowsTemp, Qt offscreen,
no owner input. A subsequent test extension asserts the combined live panel's
header/bar/XI fonts (24px scaled), all20rows and no clipping at all three sizes;
4own controlsPASS2.867s. The only subsequent UI edit updates the current-value
docstring and names the unchanged row-width tuple. Final native source check is
still required; earlier native receipt remains exact-d8f4 only.
