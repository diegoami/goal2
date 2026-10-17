# Original competitive matches

[confirmed: archaeology PR255, `424d5998076da1e4efc399c2715689ddb44d3e1a`, E034]
[designed: owner #73/T51] `goal2.game.competitive_match.prepare_competitive` and
`run_competitive_match` accept the original builder kinds other than friendly1.
Kind4 is refused even though the original decider predicate includes it: the
accepted builder kind set does not. Both sides receive an explicit substitution
budget `(5,5)`, overriding the original competitive default2. No vendor file changes.

[designed: T51] `prepare_watched` and `run_watched_match` keep their public
friendly-only contracts. Both paths share private preparation and driving, with
the same source endpoints/index, manager, calendar/year/class/next-free, captain,
squad, build and input guards. The normal decision policy is original play-on.
`reference_seed`, `delay_byte`, `record_draws` and competitive
`quick_at_half_time` are explicit diagnostics; there are no live controls here.

[designed: T51/T64] `CompetitivePublication(owner)` uses the same `begin(fixture)` /
`complete(token, outcome)` / `cancel()` shape as friendly `WatchedPublication`.
It captures a private source-ordered candidate and completes once, after the
original end event and successful result/player-update tail. Publication binds
fixture kind and budget5/5 separately from the input-image hash. A historical
kit1 friendly result cannot satisfy a competitive job, even on the same image.
Complete returned Memory, all player/country records and both original RNG words
propagate once; no Python quick tail is applied over them. CPU prefix/suffix
results retain their separate, strictly checked quick RNG ledger. A suffix can
advance the live primary seed beyond the retained original primary seed.

[designed: T51] The application keeps session version3. Historical kit1 and current
kit2 friendly envelopes/history retain schema1 and their exact meanings.
Competitive results use schema2 and the actual current kit2 engine identity;
this is a result-profile change, not a new engine or original snapshot format.
Every managed competitive history row contains a strict `resolution` object:
`kind`, `winner`, `regulation`, `extra_time` (score or null), and `penalties`
(score or null). The row's `score` contains normal goals, including ET when played.
Resolution persists without World and after later `last_match` replacement.
Latest raw result, matching World/history, stage scores and original winner must
agree. Missing/malformed resolution, unknown identities, wrong fixture kinds,
stale/duplicate outcomes and partial completion reject before publication.

[confirmed: PR255/E034] Result score excludes converted penalty kicks; the
original final board includes them. A nondecider can retain winner2/draw. A drawn
decider needs ET and, if still tied, a shoot-out. Incident ET flags come from the
original result, not from inferred display periods. Returned player consequence
bytes are checked against the post-tail Memory. Desktop results name the teams,
regulation/ET/penalty scores and winner and identify original results after real
publication and save/reload; quick result labels retain their meaning.

[designed: T51 acceptance] Reproduce with:

```sh
python3 -m unittest goal2.tests.test_campaign_competitive_match -v
python3 -m unittest goal2.tests.test_campaign_competitive_publication goal2.tests.test_campaign_competitive_save -v
python3 -m unittest goal2.tests.test_watched_runtime -v
python3 tools/prove_campaign_competitive.py --baseline
# After all readers finish, run saved-byte controls sequentially:
python3 tools/prove_campaign_competitive.py
python3 tools/prove_watched_identity.py
QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/competitive.py
```

[confirmed: bounded T51a owner5 inputs; designed: T51 comparisons] Adapter cases
reuse the reference menu, year0/base2028/stage2/class0, original captain pick and
default delay, exact play-on/quick-halftime policies and explicit5/5. The independent
accepted E034 guest hooks check event stamps and whole-stream order; a separately
exported accepted package checks full results/events/Memory and both seeds. The
managed-sideB case is executed independently rather than assigned sideA's outcome.
No seed or fixture search is performed.

[designed: T51 integration] Country4's actual rebuild-generated1990 opening queue
runs both original friendlies, then its actual pending qualifier. The1992 queue
has only one opening friendly. These are original executions on explicitly
adapted application inputs, not an original new-game replay. New competition
builders, route-level news/sacking, live workers, renderer and controls remain
outside this interface. Friendly unlimited-substitution UI policy is separate
from the accepted original friendly default5.

[confirmed: accepted original setup observations and T51 tests; designed: T51]
A next quick friendly uses a private input copy after a validated retained
competitive profile and an actual pending kind1 row. The adapter verifies the
complete input Memory equals the existing state's serialization before changing
only three original setup mode bytes to friendly values: DS9A3D=0,8319=45,7C36=0.
It retains the original kickoff side, source records, both seeds and saved Memory.
Both quick constructors use that copy. Unknown identities, arbitrary templates,
unsupported retained modes, nonfriendly pending rows and legacy extra-time
templates retain their strict refusals. This is new-friendly setup, with no
competitive quick-engine implementation or original Memory rewriting.
