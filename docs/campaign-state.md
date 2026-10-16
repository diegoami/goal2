# Campaign state

[designed: T40] `goal2.game.campaign.start_campaign` constructs a one-manager
campaign from a parsed `GoalDat`, an explicit local engine-template savestate,
managed country, source start year and two seed words. The template supplies
the memory layout and opaque engine tables. The factory rebuilds all player
records, country squads/ranks/default tactics, and manager records from
GOAL.DAT and the source-backed new-game adapter. It resets the match clock and
result, team choices, counters, country status bytes, and player fitness by
replacing those records. The existing new-game player generator keeps its
established fixed managed-pool seed. Requested seeds are stored as campaign
starting seeds and initialize the live game RNG words; `GameState` RNG words
then advance with play while campaign metadata retains the initial seeds.
Bytes outside the recognized fresh-game
fields are retained as opaque template layout data.

[confirmed: T39 handover, F023/F025 at archaeology pin
`0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb`] Start years divisible by four
open at campaign ordinal year 1/stage 2. Years 2 mod 4 open at ordinal year
3/stage 5. Other year residues are rejected because the source register does
not establish them. Campaign ordinal years map stage 2 to year 1, stages 3–4
to year 2, stages 5–6 to year 3, and stages 7–8 to year 4; the source start
year remains a separate value.

[designed: T40] A caller supplies the ordered fixture records until later
tasks add calendar builders. Each record has a stable ID, cycle, ordinal year,
stage, kind and two ordered country IDs; the retained home/away field names are storage labels only. The model validates ID uniqueness,
country ranges, stage/year pairing, ordering and a contiguous stage path. The
completion ledger is an exact prefix of that queue. Only friendly kind 1 can
be completed here; competitive fixtures stop with an explicit unsupported
result-handler error. Empty or exhausted queues do not imply a finished stage:
calendar advancement reports that the next builder is unavailable.

[designed: T40] Friendly session saves keep their version-1 schema and meaning.
Campaign saves use strict version 2 metadata, including both seeds, the source
year, current cycle/year/stage, ordered fixtures and completion ledger. A
malformed or unknown version-2 field is rejected before a candidate can replace
an active session. Terminal friendly paths still reject campaign saves.
[designed: T41] Browser controls accept campaign saves and validate the complete
continuation before replacing the current session.

[derived: F023, goal2-archaeology 0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb]
goal2.game.campaign_schedule.build_opening_campaign reads the stage-2 or
stage-5 initial rank order from GOAL.DAT and the slot, schedule, friendly,
threshold and fixture-number tables from the supplied local template. It
returns the 32 drawn groups and source-ordered opening fixture rows, keeping
the original side A/B endpoint order, source group byte, draw-group context,
round, continent, kind and fixture number. The static reconstruction follows
the listing; it does not claim original-runtime corroboration. The draw uses
an explicit seed and reports the post-draw seed. start_opening_campaign
projects only the selected country's rows into a T40 campaign and starts its
live primary RNG at that post-draw seed. Other countries' rows remain metadata;
the projection does not complete CPU fixtures or simulate results.

[designed: T41a] The T40 schema retains its existing home_country and
away_country storage keys for version-2 compatibility. In opening metadata
and campaign projections these fields carry the first and second ordered
endpoints only; Fixture.side_a and Fixture.side_b expose that order without
asserting which endpoint plays at home. Friendly kind 1 remains completable;
the stage-2 or stage-5 qualifying kind remains a barrier until a competitive
result handler is implemented.

[designed: T41] Browser New campaign accepts country, an even source start year
and both explicit 16-bit seeds. Play includes a one-use token and the exact next
fixture identity. Both scheduled endpoints replace the template pair in the
shared preview/runner resolver. A detached candidate receives engine changes,
the completion ID and a retained score row; only a validated browser response
publishes it. Refresh, preview, team confirmation, Save and Load do not complete
fixtures. The manager remains fixed; New campaign can choose a different country.
The browser displays source A/B order, stage, kind, named next opponent, retained
scores and the unsupported qualifier boundary. Other-country results remain
pending T48. Simulation uses the existing assumed full-friendly runner, with
no claim of original full-match fidelity.

[designed: T41] Version-2 campaign metadata adds optional `results` rows containing
`fixture_id`, ordered country IDs and score. Old T40 saves without score history
remain readable. New history must reference unique completed fixtures in queue
order and match their scheduled endpoints. Saves retain this history and resume
at the pending fixture without simulating another match.
