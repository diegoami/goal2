# Optional 22-player squads

[designed: owner2026-11-18, #777; T231; owner, 2026-11-27, #862/T240]
An ordinary squad remains twenty. The optional 22 capacity begins with the same
twenty and two empty additional places. All selected players are intended to be
match-day eligible: eleven starters plus eleven substitutes.

[designed: owner, 2026-11-27, #862/T240] Twenty-four places are withdrawn: 22 is
the largest. A career saved with 24 places loads as 22 — empty extra places are
dropped first, then the last filled ones, and those players return to the pool
they were recruited from — so no save is refused. The one exception is a receipt
a 22-place squad cannot host: if that career's last watched match saved a
24-place selected-bench receipt, that receipt is dropped (its summary and F4
for that one match are no longer available) rather than refusing the career;
its records, results and RNG are untouched.
The complete feature requires the native extended-bench input capability and
the screen/worker wiring; the state/save layer alone does not activate it.

The original assistant still chooses its original recommended twenty. Its
additional selection uses actual original-strength scores for remaining
players: exclude current keepers and unavailable players, take the strongest
candidate among the least represented additional defence/midfield/attack
groups, and keep pool order for equal scores. The two places use different
groups when candidates allow. A vacant place remains only if no eligible
outfield player is left.
This is a designed addition, not an original larger-squad rule or a displayed
overall rating.

`GameState.squad_capacity` and nullable `extra_squad` words retain this metadata
separately from the native20/80 country/pool arrays. `extended_squad.resized`
creates a private candidate; `squad_slots` includes vacancies and
`visible_pool` excludes selected extras. Shrinking returns dropped selections
to that visible pool. Validation requires correct capacity/slot count, exact
integer IDs, unique selected membership and current made-pool ownership.

Session-save version5 is used only for the optional larger-squad group:
`extended_squad: {capacity:22, players:[word|null,word|null]}`. It preserves
empty places, selections and any identities, and a document that still says
capacity 24 is read as 22 with the rule above. Versions1..4 remain readable, and an
ordinary twenty-player save keeps its previous version/encoding. Version5
requires its exact group; malformed/unknown fields or invalid membership reject.
The original DOS binary layout is not widened or used to store these extras.

```sh
python -m unittest goal2.tests.test_extended_squad_t231 goal2.tests.test_session_save -v
```

[designed: T233; T240] The desktop model can explicitly resize 20/22, fill a vacant
extra place, project every filled selected member and hide those members from
pool search/filter results. These are copied canonical GameState operations;
no live engine memory is written. A selected extra exchanged with an XI member
preserves full selection and captain repair, even when outside recruitment is
closed. Recruiting an outside player into an extra place retains the existing
availability/window policy. Physical country/pool arrays remain20/80, and
save/reload retains nullable places. Visible size controls and match activation
require the later accepted native/UI consumer delivery.
