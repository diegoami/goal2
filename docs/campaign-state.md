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
stage, kind and home/away country IDs. The model validates ID uniqueness,
country ranges, stage/year pairing, ordering and a contiguous stage path. The
completion ledger is an exact prefix of that queue. Only friendly kind 1 can
be completed here; competitive fixtures stop with an explicit unsupported
result-handler error. Empty or exhausted queues do not imply a finished stage:
calendar advancement reports that the next builder is unavailable.

[designed: T40] Friendly session saves keep their version-1 schema and meaning.
Campaign saves use strict version 2 metadata, including both seeds, the source
year, current cycle/year/stage, ordered fixtures and completion ledger. A
malformed or unknown version-2 field is rejected before a candidate can replace
an active session. Terminal and browser friendly paths reject campaign saves
until campaign controls are implemented.
