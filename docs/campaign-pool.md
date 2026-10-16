# Campaign national pool

[derived: F007/F011, archaeology `0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb`]
One manager has twenty country squad words plus eighty generated reserve records,
not eighty including the squad. Initial reserve IDs are2561..2640. Names come
from the corresponding original GOAL.DAT entries at runtime. No original names,
records, tables or assets enter git.

[designed: T45] `game.campaign_pool.view` returns squad/reserve rows with search,
position filtering, ability, energy, confidence and eligibility. Sort reserves
by actual position+6 and then ID; a read does not sort persistent slots or consume
RNG. `position_group` uses the existing image's 0D4E line mapping (quick-engine
`POS_LINE`), with readable rebuild labels. No fourteen-role label table is invented.
`exchange(state, outgoing, incoming)` swaps exactly one full16-bit ID each way,
updates the twenty country words and replaces an outgoing starter/captain with
the incoming available player. All validation occurs on a candidate first.
Player bytes, seeds, counters and history are untouched by an exchange.

[designed] `CampaignState.reserve_ids` records the eighty slots explicitly.
The sole-manager universe is its original country twenty plus2561..2640;
uniqueness, disjointness, same-country records and country-word agreement are
validated on exchange and campaign save/load. Existing v2 canonical campaign
saves missing this field infer only reserve membership, without recreating bytes.
Noncanonical old rosters without membership are refused rather than guessing.
Standalone v1 saves retain their previous meaning. Future retirement/recreation
must deliberately adapt this fixed-universe invariant at T57.

[assumed: Q008; archaeology issue254] Until the exchange-window reading arrives,
permit exchanges only before a pending managed kind1 friendly. Refuse exhausted
queues and unsupported phases. Consecutive completed/pending managed friendlies
whose second-country continent differs from the managed country's constitute a
provisional ongoing tour and close exchanges. This uses the source5A38 country
comparison, not an invented side-A/side-B venue interpretation. It can over/under
restrict tour edges; it is not original exchange-window fidelity. Replace this
bounded policy with accepted Q008 evidence when available.

[derived: F018/F019/F027, `0791:BA4E` at the pin above] For each stored reserve
word, recover using3651 flag0 when5A8F selects gradual recovery, otherwise3558;
then subtract `rand(4)` and add a second `rand(4)` in one signed/clipped confidence
change, then applyB27F when kind is nonzero. The quick campaign caller visits this
eighty-word prefix before B7FA's current squads. It uses no match-result confidence
term for reserves and consumes no original watched-result state. Current scorer
shadows do not overlap reserve membership.

[derived: focused first managed fixture, country4/1] Same-continent redraw uses
160 reserve recovery draws and160 reserve confidence draws, followed by60 current
energy and36 current bench-confidence draws:416 main-LCG steps after play. Injury
healing in gradual recovery can add draws;416 is not a universal fixture count.
This integration does not claim full original fixture-tail or campaign parity.

[designed: T45/T68] The portable API has no Qt/HTTP dependency. T71 supplies the
desktop controls; existing browser screens gain no pool UI in T45.

```sh
python3 -m unittest goal2.tests.test_campaign_pool -v
python3 -m unittest goal2.tests.test_campaign_pool_flow -v
python3 tools/prove_campaign_pool.py
```
