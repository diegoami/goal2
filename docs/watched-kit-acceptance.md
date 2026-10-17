# Original-match kit acceptance

[designed: T62; owner #130/#148] This is the optional engine/runtime handoff.
The application adapter, publication, process bridge and desktop watched controls
remain T63–T66. Ordinary quick play does not import or require Unicorn.

## Source and resources

[confirmed: archaeology PR251, merge `3656a2d26e0f57a410d648edeaa6cd9eb7d1f607`]
All ten files in `goal2/engine/original_match/` are byte copies of
`runtime/original_match/` at that commit, including its README. PROVENANCE.md has
one row per file; tools/watched-kit-hashes.json records all ten full SHA-256 values.
`tools/watched_evidence.py` compares the file set, hashes AND exact source bytes,
and verifies that the source is an ancestor of archaeology origin/main.
No local change to a vendored file is permitted; fixes go upstream.

[confirmed: accepted assets.py/E033 entry_probe.py and E011-r0001 run record at the same pin]
Resources are supplied to ignored `.cache/`, checked by full SHA-256, never git:

| Resource | Release asset | SHA-256 |
| --- | --- | --- |
| Kit reference menu | E006 / e0afff6751747233-e006-1000-r0001.sav | e0afff6751747233f6ab8b9ba73dab0790b7509f15257ed7ae24f528b935657d |
| Upstream entry probe menu | E006 / 3789d8490d2b42d8-e006-2100-r0005.sav | 3789d8490d2b42d8a589fec2afeb51de0ace4b4c5d1e5e24ff232321874dd106 |
| Independent strict reference | E011 / d68e48c734a742a6-E011-r0001-watchstart.sav | d68e48c734a742a63e707a8c451b9011ef03b452ebd91f239d86f875464e07a9 |

[designed] Install the optional tested dependency with `python3 -m pip install '.[watched]'`
(Unicorn2.1.4); desktop plus runtime is `'.[desktop,watched]'`.
This is local dependency setup, not a distribution package. The ordinary app/quick
path needs neither Unicorn nor watched resources. Full runtime acceptance needs
both and refuses missing inputs; it does not silently skip original runs.
The upstream README documents the exact package API and build coverage.

## Reproduce verification

[designed] Commands run from the goal2 checkout, with the archaeology checkout
available to tools/check_provenance.py (`GOAL2_ARCHAEOLOGY` can override its path).
Verification exports exact accepted upstream sources to an ignored cache,
without altering that checkout or installing a second production caller.
Outputs in `.cache/watched-*` have unique names and include per-case diagnostics.

```sh
python3 -m unittest goal2.tests.test_watched_runtime -v
python3 -m goal2.engine.original_match.check --cache .cache --family
python3 tools/check_watched_records.py --seeds 10
python3 tools/check_watched_upstream.py --suite tests
python3 tools/check_watched_upstream.py --suite stamps
# Run each save case separately (0,1,2,3,4,5,6), keeping individual commands short:
python3 tools/check_watched_upstream.py --suite saves --case 0
python3 tools/check_watched_upstream.py --suite entry
python3 tools/check_watched_upstream.py --suite example
# Run each mutation batch separately (1,2,3):
python3 tools/check_watched_upstream.py --suite mutations --batch 1
python3 tools/prove_watched_acceptance.py
python3 tools/prove_watched_records.py
python3 tools/check_provenance.py
```

[derived: accepted E032 compare.py/record_schema.py and E033 entry/stamps probes]
The strict checker first repeats the original E032 runner on its actual hash-verified
E011 watchstart input. The accepted recursive schema and comparator check all ten
unique seeds: completion/error/strays, real start identity and declared inputs,
score, ticks, draw count/digest, all eleven statistics rows and commentary template
counts. A different menu image is never mislabeled as that watchstart.

It separately checks the kit's menu-entry equivalence against those measured
outcomes, with the explicit captain-boundary seed override and delay byte0.
Independent guest-write hooks compare event minutes, scores and cross-kind order.
A second original execution reuses E033 Entry on the SAME menu image and declared
fixture; its existing guest continues through original B7FA using route_fixture's
recorded far-call frame. All3061 player records, all129 country records and both
final RNG words must match the kit's returned memory. The checker fails rather
than omit a field. Only digests/diagnostics are persisted, never original images.

[derived: E033 notes §2] E006-r0001 and r0005 share initial player/country arrays,
but their calendars and secondary RNG state differ. Comparing final seeds across
those different initial states is invalid. The additional state comparison uses
r0001 for BOTH executions; upstream's entry evidence retains its original r0005.

## Handoff coverage and limits

[derived: accepted E033 notes, package and upstream review regressions]
T60's supported entry is run_match0791:F1F6 with fixture far pointer and return
000E:6F1D; entrySP3EC0/BP3EDE and captain-wait CC7B/CC2E are recorded upstream.
The route fixture index plus engine year reseed the primary RNG before setup's
256 draws. Identical entry inputs repeat; two different incoming primary seeds
reach the same captain boundary. Kit reference inputs are Denmark7 versus19,
fixture21, original image XI/tactics/captain/default play-on decisions. The ten
reference runs override the seed explicitly at the captain boundary. They do
not prove arbitrary fixtures, countries or campaign-year transfer (T63).

T61 reuses the accepted package, existing screens and original post-match tail;
no local match algorithm or second application caller is added. R1 meaningful
code/data/relocation build mutations, R2 full-time save through the player-update
tail, R3 write-time commentary stamps, quick-result scratch-score exclusion and
cross-kind take-back order remain explicit acceptance checks. Original boards,
summary responses, substitutions/refusals and normal completion use the upstream
hooks, tests and worked example.

[confirmed: merged README] Friendlies only (kind1), one human side. Competitive
fixtures, extra time and shoot-outs are refused. Substitutions follow original
stoppages; interactive editing and owner substitution-budget integration are
outside T62. A full_time event precedes the post-match player update. Consumers
must wait for completion/result and carry full returned memory; never add quick
Python player updates over original effects.

[confirmed: merged README build guard] Mutable player/country/seed inputs are
permitted; immutable engine code and measured read-only data are protected.
The old goal2 clock stand-in at DS:0E6C overlaps the original foot table: adapters
must preserve the template's immutable bytes. T62's adapted-record guard test
changes players/tactics/seed while retaining those bytes. T63 owns broader mapping.

## Recorded acceptance run

[confirmed: T62 execution, full diagnostic hashes and per-case outcomes in
[evidence/T62-watched-kit.json](evidence/T62-watched-kit.json)] Nine runtime tests,
445 goal2 tests (no skips),24 accepted upstream tests, all four kit check steps,
10 strict original records and their independent kit/state/event comparisons pass.
All17 event stamp/order scenarios and all7 upstream save scenarios pass. The seven
save scenarios cover17 public kinds; a focused seed70 take-back regression saves
at an actual `goal_disallowed` event and completes coverage of all18 kinds. Its
uninterrupted and resumed runs match the complete event stream, full result and
entire returned memory. The entry probe reproduces the reference match, ten seeds
and repeated captain boundary; the interactive example completes. All20 accepted
upstream mutations and4 goal2 acceptance-tool mutations are killed. Three further
black-box controls reject omitted player updates and falsified seed/draw output; timeouts do
not count as killed. Two retained Qt flows and all six browser scenarios pass.

[designed: T62] The report retains the initial acceptance counts/log hashes and
adds the disallowed-goal control and corrected coverage union. Unchanged upstream
engine, strict-record, desktop and browser checks carry forward from the full
review; the added runtime regression, full Python suite and acceptance mutations
are rerun for this correction.

[derived: this mapped evidence and accepted source] T60/T61 handoff obligations
are satisfied for the stated friendly fixture/pair/family and entry/calling scope.
No unexplained difference remains in those inputs. Broader goal2 campaign-year,
fixture identity, managed-side and field transfer belong to T63; once-only result
publication/save compatibility belong to T64. Those remaining tasks are not waived
or claimed by package acceptance. Timing in the report is measured on this shared
machine and supplies no deadline guarantee.

## Watched state adapter

[designed: T63] `goal2.game.watched_match.prepare_watched(state, template, fixture)`
creates a private accepted-kit image. `run_watched_match` completes it synchronously
with default `Match.answer()` decisions and returns the original result, ordered
completed diagnostic events, entire Memory component, both RNG words and engine
year. It never publishes state or adds Python player updates. T64 owns publication;
T65 must stream events directly from the kit in its worker rather than replaying
this completed transcript. A refused decision or an identical repeat without intervening guest progress fails clearly.

[derived: accepted F025 §2–3 at `3656a2d26e0f57a410d648edeaa6cd9eb7d1f607`]
The original engine year is a counter of two-year gates, starting at zero for both
opening calendars. For campaign metadata it is
`(2 * (cycle - 1) + int(stage >= 5) - int(start_year % 4 == 2)) & 65535`.
This follows the recorded traces `(2,0)..(4,0),(5,1)..(8,1),(2,2)` for a stage-2
start and `(5,0)..(8,0),(2,1)..(4,1),(5,2)` for a stage-5 start.
A standalone image retains its own engine-year word. The original setup reseeds
from `fixture index * (engine year + 1)` modulo 65536 before its setup draws;
`reference_seed` is an explicit captain-boundary diagnostic override only.

[designed: T63; derived: T41a source identities] Callers supply an explicit
accepted-kit `Fixture(first, second, index, kind=1)`. Campaign endpoints, current
stage and `original:<index>` identity must match the pending row. Unsupported
competitive fixtures and legacy rows without a source index are refused.
The adapter retains the entire country/player arrays, reorders all twenty squad
words with the selected eleven first, and passes the actual captain separately.
The old `+2F` captain placeholder and immutable `DS:0E6C` foot-table bytes are
preserved from memory. The original updates the computer side and both teams'
players; the full returned memory carries those changes through its final tail.

[designed: T63] Reproduce with
`python3 -m unittest goal2.tests.test_watched_adapter -v`.
The ten explicit E032 seeds use Denmark7/19, source fixture21, engine year0,
delay byte0 and default play-on decisions; they match the accepted strict T62
score/ticks/draw-digest records and independent direct kit runs for full results,
events and memory. Additional natural-seed/year/index, changed-squad/captain/tactics,
side-B and invalid-input cases protect broader transfer. Original bytes remain in
ignored caches using the resource hashes above.

[confirmed: F023 §1–2/F025 §2–3 and1771:038C at the accepted pin]
The original game-record `+0x28` is the next **free** fixture number. Its0x4B48-byte
allocation holds regular rows1..2400, aggregate rows2401..2408 and sentinel2409.
The adapter refuses aggregates/sentinel/next-free indexes. With a complete saved
source world it stages the exact `max(source IDs)+1` count (stage2 opening769,
stage5 opening2001), checking canonical contiguous IDs in the current source
class (1..1360 for stages2–4;1361..2400 for5–8). Legacy inputs without that full
schedule retain the template's bound and cannot silently expand it. Campaign
indexes and next-free bounds must fit the current source class even for legacy
inputs; the class-1 legacy reseed control explicitly supplies count2001/fixture1362.

[derived: the same source fields] Campaign images also transfer source base year
to `+0x3A`, stage to `+0x3C` and class to `+0x40`; the independent year counter
remains at `+0x38`. A stage2 template's base2028/count769 must not leak into a new
1990 stage5 campaign. Other opaque memory is preserved; no full original new-game
replay is claimed for the rebuild's designed fresh state.

[designed: T63 actual-caller regression] Two fresh campaigns made by the desktop's
`start_opening_campaign` using the retained E010-r0008 template and country4
match direct original declared-image runs for complete results/events/memory:
1990 uses fixture1378 (4 versus1), counter0/base1990/stage5/class1/next-free2001;
1992 uses fixture3 (25 versus4), counter0/base1992/stage2/class0/next-free769.
Both use default play-on answers and natural setup reseeding. The old adapter
rejected1378 against the inherited769 bound; an omitted count transfer must fail
the new field assertions before original execution. These cases extend, rather
than replace, the ten strict reference controls above.

## Watched publication and session saves

[designed: T64] `goal2.game.watched_publication.WatchedPublication` accepts an
owner with `state`, `template_bytes` and `view(candidate)`. `begin(Fixture(...))`
returns a private job and one-use token; only `complete(token, WatchedOutcome)`
validates the completed original result and its declared input-image hash,
builds all fields and history, validates
the owner's view, and swaps the active state. Cancellation, stale management
changes, invalid fixture identities, unsupported kinds and failures before the
swap leave the active state intact. A failed completion consumes its token.
A `full_time` event is not a completed outcome: the adapter must exhaust the
original events and successfully call `result()` after the original player tail.
Worker and desktop integration remain T65/T66; this interface introduces no
mid-match session save feature.

[derived: accepted E033/T63; designed: T64] Publication retains the entire returned
Memory, every country/player record, all twenty returned managed squad words,
both returned RNG words and the full kit result. Selected eleven and captain
remain management choices. Returned tactics are known engine fields. No quick
Python energy, confidence, form, pool or eligibility tail runs over these bytes.
T48's existing source-ordered CPU prefix/suffix still publishes atomically with
the managed result. The live primary seed can therefore advance for those silent
suffix results; the retained watched envelope always records both exact original
returned seeds and Memory. This is separate from between-fixture player effects.

[designed: T64] Watched envelopes and history use engine identity
`original-match:3656a2d26e0f57a410d648edeaa6cd9eb7d1f607:1` and result schema1.
Session saves containing watched results use version3. Legacy friendly version1
and campaign version2 retain their quick result/history meanings and continue to
load; new quick-only sessions retain those versions. A quick result following a
watched result keeps version3 and both engine meanings; its prior watched history
and returned Memory/RNG remain validated. A watched world row records
the incoming seed, original fixture/year setup reseed and returned primary and
secondary seeds explicitly. It never presents the setup reseed as an affine
continuation of T48's quick draw ledger. Unknown engine identities, incompatible
result schemas and malformed watched continuation data are rejected before an
active state can be replaced. Original `Match.save()` blobs are unrelated to this
session schema.

[designed: T64] Focused acceptance commands:
`python3 -m unittest goal2.tests.test_watched_publication -v` and
`python3 -m unittest goal2.tests.test_watched_save -v`. They cover all ten strict
T63 seeds, actual fresh1990/1992 campaigns, returned state, once-only completion,
failed publication, legacy saves, malformed watched saves and deterministic
next-fixture continuation after save/reload. The actual1990 queue supplies a
second friendly; the actual1992 queue supplies competitive kind2 next, so that
case preserves the same explicit unsupported-fixture refusal after reload.

[confirmed: T64 execution at code commit0e9938fb4457dcf332090065b395c87076c960f4]
The focused publication/save commands pass6/5 tests, and the complete Python
suite passes473 tests with no skips. All12 publication/save mutation controls,
all6 browser scenarios and both retained Qt flows pass. Commands, durations,
log digests, baseline failures and scope are recorded in
[evidence/T64-watched-publication.json](evidence/T64-watched-publication.json).
