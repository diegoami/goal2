# Optional22/24-player squads

[designed: owner2026-11-18, #777; T231]
An ordinary squad remains twenty. The optional22/24 capacities begin with the
same twenty and2/4empty additional places. All selected players are intended
to be match-day eligible: eleven starters plus eleven/thirteen substitutes.
The complete feature requires the native extended-bench input capability and
the screen/worker wiring; the state/save layer alone does not activate it.

The original assistant still chooses its original recommended twenty. Its
additional selection uses actual original-strength scores for remaining
players: exclude current keepers and unavailable players, take the strongest
candidate among the least represented additional defence/midfield/attack
groups, and keep pool order for equal scores. When candidates exist, three
extra selections cover all three groups; four yield2/1/1. Two use different
groups. A vacant place remains only if no eligible outfield player is left.
This is a designed addition, not an original larger-squad rule or a displayed
overall rating.

`GameState.squad_capacity` and nullable `extra_squad` words retain this metadata
separately from the native20/80 country/pool arrays. `extended_squad.resized`
creates a private candidate; `squad_slots` includes vacancies and
`visible_pool` excludes selected extras. Shrinking returns dropped selections
to that visible pool. Validation requires correct capacity/slot count, exact
integer IDs, unique selected membership and current made-pool ownership.

Session-save version5 is used only for the optional larger-squad group:
`extended_squad: {capacity:22|24, players:[word|null,...]}`. It preserves empty
places, selections and any identities. Versions1..4 remain readable, and an
ordinary twenty-player save keeps its previous version/encoding. Version5
requires its exact group; malformed/unknown fields or invalid membership reject.
The original DOS binary layout is not widened or used to store these extras.

```sh
python -m unittest goal2.tests.test_extended_squad_t231 goal2.tests.test_session_save -v
```

[designed: T233] The desktop model can explicitly resize20/22/24, fill a vacant
extra place, project every filled selected member and hide those members from
pool search/filter results. These are copied canonical GameState operations;
no live engine memory is written. A selected extra exchanged with an XI member
preserves full selection and captain repair, even when outside recruitment is
closed. Recruiting an outside player into an extra place retains the existing
availability/window policy. Physical country/pool arrays remain20/80, and
save/reload retains nullable places. Visible size controls and match activation
require the later accepted native/UI consumer delivery.
