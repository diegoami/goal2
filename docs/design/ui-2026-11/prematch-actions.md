# Pre-match action contract

[designed: T170r/#745] This is the activation checklist for S15 → S08/S09/S10 →
S15 → S16 over one held Match. The approved Actions lines remain in
[the design](README.md). This audit adds no UI design or save semantics.
Each row includes click equivalents. Closing a child returns to its invoker;
Esc cancels text editing before closing; closing discards an unfinished pick and
never reverses accepted edits.

[confirmed: goal2 `31989d87`; archaeology `fb6d3093`, F010/F031/F030]
The current window edits DesktopModel copies. The worker/seam accepts team tactics,
all-twenty roster pairs, pool exchanges, native R/C positions and late captain selection, but the window
does not yet use that worker. “Supported” below means the held API exists, not that
window activation is delivered. Source references are the named E44F, 4952,
4B61/49B8 and 1981 bodies at that upstream pin; current handlers are linked below.

## Data and transaction rules

[confirmed: T170r, `measurements/T170r/action-audit-v2.json`]
An edited held roster differs from `SeasonSession.state`, which intentionally stays
at its route boundary until resume. A public `Match.records_after()` read returns
the current state/2 without changing full RAM, all sixteen registers, Python state
or replay. The decision exposes twenty player records and eighty pool IDs, but no
pool records or opponent roster. The audit records hashes and metadata only.

[designed: #746/T170s] The worker's `preview` operation supplies detached current
pre-match data: explicit decision identity and canonical hash, separate from round
publication, ledger deltas, and saving. Cards, both elevens, country tactics, pool
records, availability, club position, own overrides and marking targets must come
from this current snapshot. Identity overlays remain keyed by player word. Do not
replace the held Match, read stale DesktopModel records, or publish preview as a
completed round. See [the worker mapping](../../tasks/T170i.md).

[confirmed: T170s/#750 full worker proof and synthetic actual-server control]
Original news snapshots include raw cell bytes. The season-specific framing in
[#751](https://github.com/diegoami/goal2/issues/751) preserves them losslessly
with provenance and ordered deltas before round publication over the pipe.
Preview's JSON state/2 payload remains separate.

[designed: T170r] Send one accepted edit and wait for its next numbered decision
before refreshing authoritative values. A pure invalid request retains the same
decision for repair; transport/backend loss requires explicit reopen, never replay
by the UI. Cursor movement, search, selection and text cancellation stay local.
API field whitelists are not evidence of pre-match semantic support.

[designed: T170x/#768] `goal2.game.prematch_view.PrematchView` supplies the
detached window read model: current squad/pool/opponent records and order,
country defaults, actual marking status/word, setup/pane eligibility and
captain/target domains. Its display-only state reuses the existing card/TEAM
decoders and preserves supplied identity metadata. It carries no career
calendar and cannot replace a native season bootstrap or round publication.
The full window action/mutation flow below still needs its controller wiring.

## Action matrix

[confirmed: goal2 `31989d87`, handlers linked below; original `fb6d3093`]
“Preview” in this table means #746, “personal API” means
[archaeology #719](https://github.com/diegoami/goal2-archaeology/issues/719).
[confirmed: T170u, archaeology `fc6b5294`] The held position/club input arm exists;
T170w adopts native marking from T137/87d92501. T170v adopts own overrides from
archaeology T136/46315dcf; current previews carry their native results. The historical T170r
audit records the older refusals; its assumption-checking probe intentionally
detects drift when run against a later kit. Current R/C proofs live in T170u tests.
The remaining issues and the existing T183 issue are explicit activation prerequisites;
an existing scoped assistant placeholder remains the approved T183 exception.

| Screen/action | Current handler / original route | Held mapping and required data | Refusal, return and remaining work |
|---|---|---|---|
| S08 ↑↓, ←→ | `move`, `show_side`; E44F select cursor/pane | Local selection by word; current sorted squad/pool and card preview | Clamp cursor; original pool permission is authoritative; refresh after edits |
| S08 Enter, two squad picks | `press_move` → `model.swap`; DEA6 outside-match swap | Supported `PrematchSeam.swap(a,b)` / edit-only substitutions; all twenty, including same-block pairs; T134 original sort | Same pick cancels; reject self/unknown/stale batch without consumption; show returned order, not a guessed permutation |
| S08 Enter, squad/pool picks either order | `press_move` → `model.exchange`; E44F/DEA6 | Supported `exchange(out,in)`; current pool IDs plus preview cards/availability | Two pool picks replace the selection; guest refusal/permission must surface; provisional campaign calendar guard is not an original rule |
| S08 Ins recommended twenty | `assistant` says COMING_LATER; original DC7E | Existing [T183/#594](../../tasks/T183.md), upstream T125 wrapper required | Preserve explicit placeholder pending T183; no substitute heuristic or claim of delivery |
| S08 R / Shift+R | `reposition` → `set_position`; original 4952 R cycle | Supported `PrematchSeam.set_position(word, code)` for current squad **or pool** word; code0..13; Shift+R is owner #423 addition | Pure invalid inputs retain the decision; wait for fresh guest order/card. Current window still edits its old model until activation |
| S08 C club position | `club_position` → `club_position`; 4952 copies club field | Supported `PrematchSeam.club_position(word)` sends explicit `"club"`; native C once, not an R target | Preview reads current club value; even already-equal C reaches original4952. Current window awaits activation |
| S08 T | `his_tactics` pushes S09; E44F T calls 4B61 with pane context | Local navigation with current player and original setup/pane eligibility | Return to same card/selection; pre-match `bench=None` currently hides marking incorrectly |
| S08 F2/name Enter | `new_name`/`give_name` → `rename_player`; original F2 name editor | Existing designed identity metadata/GOAL.DAT overlay, keyed by word; not a guest record edit | Preserve printable CP437/length validation; cancel leaves identity unchanged; preview refresh must retain overlay |
| S08 /, text, Backspace, Enter, Esc | `open_search`/`set_query`; owner extras / T177 | Local accent-folded pool-name filter, preview names plus identity overlay | Enter commits query; Esc clears editing/filter before parent close; never send filtered row index as player ID |
| S08 P / Shift+P | `step_position`; owner extras / T177 | Local fourteen-position filter, preview position | Cursor resets within visible result; selected word survives only if still valid |
| S08 Esc | `escape` | Local cancel text editor, otherwise pop to S15 when invoked there | Accepted engine/identity edits persist; no extra answer or kick-off |
| S09 arrows | `choose`, arrow bindings; original own menu | Local row cursor; actual eligible four/five rows | Re-evaluate after position/availability/pane change; never infer original eligibility solely from XI membership |
| S09 Enter on four personal rows | `alter` → `model.own_tactic`; original 4B61 | Supported `PrematchSeam.set_own_tactic(word, element, value)` for elements1..4; exact False/True/None through the original T menu | Fresh preview carries own byte and player-country defaults, including pool; inherit → own false → own true → inherit. Invalid values repair the same decision; window wiring remains required |
| S09 Enter on marking row | `alter` → stopped `bench.step_mark`; original 49B8 | Supported `PrematchSeam.set_marking(word, target)`; exact None/inherit, integer0/protect zone or available opponent slots2..11; current preview supplies status and native marking words | Original offers row for available outfield **bench as well as XI**, in squad pane during setup; pool/keeper controls have four rows. Invalid projected roles/domains repair the same decision. Current pre-match UI has none: fix context predicate and wire the API before activation |
| S09 Esc | Esc binding / screen pop | Local return to S08 card (or S19 during match) | Keep accepted edits; do not convert return into Play |
| S10 ↑↓ | `choose`; original 1981 menu | Local eight-row cursor | Display order maps to bits **5,6,7,1,2,3,4,8**, not row numbers |
| S10 Enter / highlighted click | `change`; current default edits model; stopped path has async `apply` | Supported `set_team_tactic(bit,bool)`; current tactics byte, formation and characteristics from preview/next decision | Use pending/apply pattern; don't optimistically flip twice or accept another mutation while pending; surface pure refusal |
| S10 Esc | Esc binding / screen pop | Local return to S15 when invoked there | No extra edit, no kick-off; refresh S15 from current preview |
| S15 arrows / Enter row | `move_row`/`select_country`/row callbacks | Local selection; actual guest fixture/phase and both sides from preview | Before-phase controls remain reachable; later-phase behavior belongs to next activation leaf |
| S15 own players / own tactics | `players` / `tactics` | Push S08/S10 using same worker/session/decision | Return refreshes both lineup and tactics; never construct a second Match |
| S15 other side players / tactics | read-only country screens | Preview opponent roster, player records, formation and team byte | Read-only; stale boundary projection is insufficient; #746 |
| S15 tournament / statistics | push views | Current route data plus phase-appropriate current match facts | Return to same menu; preview must not invent a completed result or append ledger entries |
| S15 Ins replay automatic | `day.set_replay_auto` | Existing local preference; preserve replay behavior in later in-match activation | Persist setting through existing settings path; no guest player input |
| S15 Y / N watch question | `answer_watch` / `press_play` guard | Only display/answer when actual fixture asks; preserve original watch policy | Unanswered question blocks Play only where asked; don't synthesize unconditional Y/N |
| S15 Play → S16 | `press_play` currently prepares old path | Keep held pre-match decision while S16 chooses; then supported `play(captain=...)` | No edit-only answer for Play, no reconfigure, no second Match; resume only after actual over/exhausted Match |
| S16 ↑↓ / Enter | captain screen select/confirm; original captain stop | Current post-edit XI and cards; selected word through T133/T170p late captain | Invalid/stale captain remains repairable; do not send pre-edit XI index |
| S16 C / no-key timeout | computer choice/timer; original wait | Explicit `None` requests native default; omitted captain preserves configured choice; exact-word choice also supported | Preserve distinctions; only one Play packet; in-match taker/penalty-order Esc undo is outside this pre-match leaf |
| All F1 / mouse | existing help and widget callbacks | Local help; clicks invoke the same action path as keys | Help must work during pending edits; mouse cannot bypass validation or duplicate an answer |

## Evidence and activation boundary

[confirmed: original `fb6d3093`, named `seg_0791_13.c` E44F and
`seg_1771_04.c` 4952/4B61/49B8; audit receipt v2]
The actual original controls reached five own-menu rows for XI outfield and bench
outfield, four for keeper and pool, with setup=1 and in-match-menu=0. Eleven sealed
position/club/own/mark attempts refused without consuming RAM/register/state/replay.
This is an API gap, not evidence that the original lacks these actions. Relaxing
the guard alone would leave pre-match plan jobs undriven. The broader original/port
Prover comparison remains archaeology #709; this audit claims no cross-backend raw
memory equivalence and introduces no mask.

[designed: T170r/T170s] Order the prerequisites as detached preview (#746),
lossless news framing (#751), upstream personal inputs (#719) and their deliberate root adoption, then window activation
with the complete matrix as acceptance cases. Activation must fix marking context,
preserve identity/search/filter/help, and exercise S15→edits→captain→same Match.
In-match/resume and save/load remain separate leaves. T183 keeps its explicit owner
queue position; the assistant exception must be stated in the activation contract.

Current implementations:
[S08](../../../goal2/ui/s08_squad.py),
[S09](../../../goal2/ui/s09_player_tactics.py),
[S10](../../../goal2/ui/s10_team_tactics.py),
[S15](../../../goal2/ui/s15_match_menu.py),
[model](../../../goal2/desktop/model.py),
[worker](../../../goal2/game/season_worker.py),
[seam](../../../goal2/game/prematch_seam.py),
[audit](../../../tools/prematch_action_audit.py),
[receipt](../../../measurements/T170r/action-audit-v2.json).
