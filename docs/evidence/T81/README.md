# T81 pitch coordinate and observation contract

[designed: T81] This is an evidence-tool contract for downstream T82/T83, not a
production API. Original resources stay ignored. Reproduce using Python 3.12+
with the watched dependency, the verified E006 reference and GOAL.DAT in `.cache`:

```bash
python3 tools/probe_watched_pitch.py --verify
python3 -m unittest goal2.tests.test_pitch_observation -v
python3 tools/check_provenance.py
python3 tools/check_links.py
```

[designed] The probe writes a new text/hash-only `runtime-<time_ns>.json` on each
successful invocation, refuses an existing `--output`, and executes exactly the
predeclared friendly cases fixture `(7,19,21)`, managed country7, seeds
`0x0101`/`0x1234`, default answers, `delay_byte=0`, `record_draws=True`, each with
`ticks=False` and `ticks=True`. No input search, quick result or runtime skip is
accepted. `source` records full hashes of the static files at kit
`424d5998076da1e4efc399c2715689ddb44d3e1a`, and verifies every vendored kit file
against that same pin. `inputs` records both original resource hashes.

[confirmed: F013; kit424d599] Movement/display calls execute even in the
unsampled baseline. The probe never patches guest code, disables drawing,
changes answers or reconstructs a canonical event. [designed] Exact comparisons
remove only diagnostic `tick` events and compare all remaining event fields,
the complete result, returned complete Memory component and the main/secondary
RNG words (`DS:7B62`, `DS:8336`). Hashes in reports summarize comparisons of full
objects/bytes in memory; equal hash assertions do not replace exact comparisons.

## Coordinates and constants

[confirmed: F013; kit424d599; `named/seg_0791_07.c:465-480,904-931`]
Players and ball are drawn at background-buffer offset
`0x90E + signed8(x)*160 + signed8(y)*2`. The casts apply independently to both
bytes. [derived] For a fixed screen orientation, the horizontal coordinate is
`y` (longitudinal) and the vertical coordinate is `x` (transverse), with positive
values right/down. `project_xy(x,y)=[y,x]` gives offsets in original text cells;
`draw_offset` preserves byte addressing. The origin `0x90E=14*160+39*2` is the
original text-buffer center cell. These constants describe addressing, not a
pixel aspect ratio or physical metres. A rebuild chooses pixel scale and screen
translation explicitly. Never rotate merely because a halftime event arrived.

[confirmed: kit424d599; `runtime/original_match/match.py:419-436`]
`Match.pitch()` exposes unsigned x and signed y, including the ball. [derived]
Normalize x in the non-vendored observer only: byte values128..255 become
-128..-1. Preserve every signed position; do not clamp it into the field.

[confirmed: kit424d599; `code/seg_0791_05.asm:535-598`]
The original `0791:2DCA` predicate accepts `abs(x)<=8, abs(y)<=37` and `0791:2E00`
accepts `abs(x)<=9, abs(y)<=39`, inclusively. [confirmed: same pin;
`named/seg_0791_07.c:352-449`] `move_ball` uses the wider predicate before storing
a candidate position, draws, then uses the narrower predicate to choose a
restart when outside. Its goal-mouth branch uses `abs(x)<2`; otherwise it tests
`abs(y)<38` to distinguish touchline and end restarts, with attack direction
selecting the end. [derived] These establish the playing-grid predicate and
longitudinal goal-mouth/end semantics. They are not universal bounds on player
records, initialization, removed records or even all ball lifecycle states.
Observed extrema in a finite run cannot establish field bounds.

[confirmed: same pin; `named/seg_0791_09.c:4-49`]
Original background loading uses packed screens at `DS:6192`, `DS:613E` and
`DS:5796`; it does not construct all field markings from the play predicate.
[designed] Original artwork boundaries, goal-net depth and goal-post cell
placement remain an upstream evidence gate. No original screen bytes or glyphs
are retained here. A T83 renderer may depict the evidenced playing grid and
`abs(x)<2` mouth as an explicitly designed schematic, but cannot claim exact
original field art/net geometry from the observed extrema. If T83 requires
original artwork fidelity, that requirement is blocked pending upstream evidence.

## Identity, lifecycle and halves

[confirmed: F018/F028; kit424d599; `named/seg_0791_08.c:810-868`,
`named/seg_0791_02.c:718-724,896-940`]
Record+6 is the global pitch slot1..22, record+0xD is the current player word.
`pitch_slot_side` returns1 for slots1..11 and0 for12..22; `A260` indexes fixture
countries using that value and binds the current squad word. Thus low slots are
fixture second/team1, high slots fixture first/team0. Local slot labels are1..11
on each side (`s`, or `s-11`). Every sampled identity is checked against original
raw record bytes and that side's *current* squad word. [designed] The projection
retains both global slot and player word and calls its number a slot label.
Persistent shirt numbers are unresolved and must not be promised. A substitution
may rebind a slot; renderers must use each frame's player word.

[confirmed: F018; kit424d599; `named/seg_0791_08.c:840-868`,
`named/seg_0791_07.c:465-480,904-931`]
Initialization writes `DS:0644` as the packed position. Drawing suppresses an
exact packed `DS:0640` position. [derived] The observer carries a `hidden` boolean
for that exact sentinel on both players and ball, leaving coordinates and the raw state byte intact.
`state` is not used as a universal active/off-field predicate. [designed] No
unproven meaning is attached to other state values. Synthetic edge tests cover
initialization `(-9,0)`, sentinel `(11,0)` and non-sentinel `(11,1)` without
misrepresenting these as an observed injury/substitution in the two fixed cases.

[confirmed: kit424d599; `code/seg_0791_05.asm:2BE5-2C26`,
`named/seg_0791_08.c:252-295,445-446`]
Attack direction selects the signed-byte table `DS:7920[team XOR flag]`, where
`flag = signed8(DS:8319) < unsigned16(DS:831B)`; the clock starts with threshold45,
remaining91 and counts remaining down. [derived] This flag is an original attack
selector, not a reliable wall-clock halftime indicator. It changes at the
sampled boundary where remaining reaches45, while a queued halftime decision
may be exposed later. Preserve fixed coordinates, carry the actual selector and
mark reset/half discontinuities so T83 does not interpolate across them.

## Observation boundaries and downstream gates

[confirmed: F013; kit424d599; `runtime/original_match/match.py:319-337,769-779`]
The kit flushes writes and emits a tick when stopped at original `0791:970C`,
after the preceding movement/display sweep, before the next clock execution.
Multiple queued canonical events may refer to that one stopped state. [designed]
Only tick reads are presentation frames; `event_minute` is the stop's event stamp,
not a reconstructed timestamp for each earlier commentary item. Reported
`transitions` at halftime decisions are explicitly diagnostic stopped states,
never historical event poses. Approximately37 ticks per original minute is engine
clock structure, not wall-clock animation fps.

[designed] T82's observation contract is resolved: signed x/y, fixed orientation,
exact raw word identity/current side/local slot, exact sentinel suppression,
raw state preservation, original attack selector, completed-tick boundary and
strict outcome/RNG parity. Transport budgets, sequencing, acknowledgement and
publication remain T82 work. T83's slot labels and sampled placement are resolved;
its pixel scale, schematic field styling and pacing are rebuild design choices.
Exact original artwork/net geometry and persistent shirt numbering are blocked
upstream evidence requirements if demanded. Other lifecycle state semantics are
unresolved; neither task may silently guess them or discard out-of-predicate
positions. Competitive Watch is outside this evidence.

## Tests and receipts

[designed] `test_pitch_observation` checks asymmetric signed-axis expectations,
slot/team identity at both range edges, sentinel/init and inclusive predicate
edges, retained full-case summaries, exact half transition neighbors and all
complete fidelity comparisons. Its saved-byte controls replace the tool's axis
mapping, team mapping and sampled canonical outcome in turn. A subprocess must
fail the intended assertion (not ERROR/import/timeout), then the tool's exact
saved bytes are restored in `finally`. Each invocation retains separate logs
and source-before/mutated/restored hashes under `controls-<time_ns>/`.

[confirmed: T81 `identity-diagnostic-01.log` at this kit pin] The rejected first
full collection reached all4279 ticks for seed0x0101, then failed the ordinal
squad-binding assertion at `end`/minute93: pitch slot3 still held player364,
while the final squad's third word was374 (364 moved to fourth). This is a
postmatch stopped state, not a failed tick frame. [derived] Pitch bindings must
not be projected against postmatch squads after teardown. The observer retains
the last completed tick as its final frame and records terminal event minute
separately; `end`/`full_time` are not sampled frames. Only halftime decisions
are diagnostic pose reads. All completed ticks retain strict raw word/current squad ordinal,
team and signed-coordinate assertions; no runtime tick is omitted.

[designed] Trustworthy marker placement/visibility has no unresolved gate for
the two evidenced friendly cases: signed fixed axes, current word/team/slot,
original draw sentinel and completed-tick boundaries are concrete. Unresolved
original decorative field/net artwork constrains exact original reproduction,
not a labelled rebuild-designed modern field. Other raw state semantics are
preserved rather than guessed; no state-based culling is authorized. Slot
numbering remains explicit, and per-frame identity rebinds invalidate any
interpolation that would blend different players through a slot.

[designed] Reset classification beyond the proved half-selector transition and
identity rebinds is not inferred from coordinate jumps or raw state numbers.
T82 can transport exact stopped snapshots without such a classification. T83
can show discrete observed samples; interpolation across other restart/reset
sequences requires additional original evidence and must stay disabled where
that evidence is absent. This limits smoothing, not trustworthy marker placement
or the simple animated field requested by the owner.

## Complete runtime measurements

[confirmed: T81 `runtime-02.json`, F013, kit424d599] Each sampled run and its
unsampled baseline completed with exactly equal canonical events, complete
result, full Memory and both seeds. No tick or runtime case was skipped.

| Seed | Ticks | Changed poses | Player position changes | Ball changes | Outside in-play observations | Slot rebinds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0x0101 | 4279 | 4277 | 68534 | 2624 | 70 | 4 |
| 0x1234 | 4146 | 4144 | 66010 | 2599 | 101 | 3 |

[confirmed: same report/pin] Neither case observed a player or ball outside the
wider movement predicate. Player extrema were x[-9,8], y[-37,37] in both cases.
Ball extrema were x[-8,8], y[-38,37] and x[-9,8], y[-38,38], respectively. Both
cases observed raw player state values0,1,2,5,6,7,8,9,11,13. Neither case observed
a sentinel-hidden player; exact suppression is established by the static draw
condition and synthetic edge/control tests, not an invented runtime injury.

[confirmed: same report/pin] Adjacent half-selector samples were sequences
2116→2117 and2021→2022, respectively. Both went from minute45/subtick0,
remaining46/threshold45/flag1 to minute46/subtick36, remaining45/threshold45/flag0;
attack signs for fixture teams0/1 changed [1,-1]→[-1,1]. First/last sampled
minutes were0/93 and0/91. Full player/ball coordinates, identity words, raw state,
Memory digest and both RNG words of the transition neighbors are retained in
`transitions`; separate halftime event/decision diagnostics are labelled as such.

[designed] `runtime-01.log` and `identity-diagnostic-01.log` are rejected initial
end-frame attempts, not incomplete cases counted as acceptance. `runtime-02`
records the complete first observer version. `runtime-03` adds explicit ball
sentinel visibility and pins that exact observer hash. The final focused suite
checks the latter hash and cases. Earlier focused receipts exclude the report
class explicitly and do not stand in for the complete suite.

[designed] `premerge-attempt-01.log` retains a refused mistyped full SHA.
`premerge-4346f3d.log` retains a run whose child checks passed but whose final
clean-tree check correctly refused a concurrent documentation edit. Neither is
a passing exact-head receipt. Final clean-head validation is recorded separately;
the main session repeats it at the independently reviewed head before merging.

[confirmed: T81 `runtime-03.json`, F013, kit424d599] The final observer repeats
all four complete cases with the same measurements above and exact outcome
comparisons. It explicitly reports zero sentinel-hidden balls in these cases.
The observer SHA-256 is
`cb9b4845ed6d8de06c3f01335313eee858154a6a882651ca074d0f5f684b11f9`.

[designed] `focused-final-01.log` preserves an incorrect test expectation that
conflated all16 provenance-managed engine files with the10 original-match kit
files. The report test now compares the verified count to the pinned kit
manifest's exact file set, retaining the source-pin and observer-hash assertions.
`focused-final-02.log` passes all8 tests with zero skips, including all6 saved-byte
controls and exact source restoration. `provenance-final-01.log` and
`links-final-01.log` pass. `source-and-validation.json` records complete source,
resource, report and receipt identities; original bytes remain ignored.

[designed: T150] `runtime-04.json` is the same probe (`tools/probe_watched_pitch.py --verify`) on the re-vendored
kit `b519d999` (41 files): both cases pass with the same ticks, pose and ball changes as `runtime-03.json`; the
complete-result digests differ only because the kit labels its results `kit: "4"` (runtime-03: `"2"`).
