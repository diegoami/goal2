# T39 handover: campaign evidence register audit

[derived: T39 audit, 2026-10-16] This handover records the audit of the existing archaeology
handover branch and the resulting implementation map. It does not promote findings or implement
campaign behavior.

## Source pins and confidence

The archaeology source used for this audit is `goal2-archaeology`'s fetched `origin/main` at
`0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb`. The register branch supplied by the owner is
`origin/docs/register-sitting-20261015` at `dfce1c14d73b6491b5ac4411c1683c37b84e5672`. The
finding paths below were read from the pinned archaeology tree; the listed commit is the commit
that last changed each finding file at that pin.

| Finding | Finding-file commit | What supports the register row |
| --- | --- | --- |
| F022 | `8823b2427be49d0f5689a2b672207efc0fd7cfb8` | Listing sites and branch counts from two unhooked Unicorn replays. Proposed; not a general behavioral model. |
| F023 | `7acad2e88def6b0f936a3d13d8ff4440b54810c3` | Listing readings of stage builders, schedules, points sort and deciders; arithmetic count checks against decoded tables. No GOAL.EXE campaign run. Proposed. |
| F024 | `a737716ab5dd106e316aed37e3dbd6b68035cda8` | Listing readings; B11F and D47E separately run in Unicorn on patched/synthetic fixtures. Silent-result goal estimate is modeled from ten half-time lineups. No recorded campaign fixture. Proposed. |
| F025 | `27cd42a131256f10eb7ed47a6af26f0b0536e6dc` | Static searches and isolated edge probes of original bytes in Unicorn. No game run or near-threshold save. Proposed. |
| F026 | `7b0040a17e1c7c5fa1c92bec5b43cebd2e911dbd` | Listing reading plus measured tactic arms from one team pair/start state; no DOSBox-X run. Proposed. |
| F027 | `7992219554d3632e81aceb97ec9777ffecf4c0a6` | Listing reading, isolated Unicorn probes, watched match and seeded replays, plus declared-input quick stand-ins. Counts and their limited samples are named in the rows; no recorded non-friendly quick fixture or fixture-end run. Proposed. |
| F029 | `15f418ae82982929e2b799c3a0ce1c3b83301398` | Listing reading and measured substitution persistence (8/8 at full time, 3/3 next-match reads in one manager/two careers). The replay-snapshot exception is read from code and unverified in a record. Proposed. |

The findings' status remains proposed at the source pin. “Run in Unicorn” means original bytes ran
in that harness with the finding's declared inputs; it does not mean a complete campaign was run.
Measured sample results remain separate from static rules and from rebuild design choices.

## Audit of the existing handover

[derived: comparison with `origin/docs/register-sitting-20261015` and the pinned findings] The
T39 register preserves the sitting and pass-one finding rows while correcting or qualifying these
claims:

- NG-6 now records that the opening stage is stage 2 when the start year is divisible by 4, and
  stage 5 when it is 2 mod 4 (F023/F025); F025's examples are 1992/1996/2000 -> stage 2 and
  1990/1994/1998/2002 -> stage 5. It no longer says every new game begins with friendlies.
- A-MATCH-2/3 no longer turn competitive fixtures into friendlies or use a coin for all drawn
  knockouts. The quick foul gate, watched deciders, silent D47E path and their distinct evidence
  are stated separately.
- A-MATCH-5 leaves home advantage unresolved. F024 locates a host flag but does not establish its
  match effect.
- A-COMP-3/4 preserve the owner's code-based no-coin choices. A-COMP-6 identifies silent D47E
  results. A-COMP-7 retains F017's placement bonus amounts and +200 per `5E3A` call; F023 §4/§7
  confirms kind-3/7 group fixtures use that call and receive +200 each. No numeric conflict is
  shown; F017's “knockout fixture” label does not describe every call site in F023.
- A-COMP-10..14 capture calendar, groups, finals, two-leg play-offs and table ordering as proposed
  static readings. Stage 2 includes both kind-2 qualifiers and kind-1 friendlies.
- A-CPU-1..5 separate original lineup/tactic findings from the existing quick-match selection
  stand-ins and retain the findings' limited run scope.
- BM-6/8/9 distinguish isolated ban/injury probes from unrun fixture-end behavior. BM-7 records
  the rebuild rule: unlimited friendly substitutions and five in every other match, deliberately
  differing from the original's five and two.
- GA-1/5/6 replace “no sacking” with F025's proposed no-end and sacking readings while leaving
  threshold and confidence relationships unresolved. GA-4 is retained as an archaeology note,
  not a remaster rule; the owner corrected it to Y shows a replay / N skips.
- Owner observations remain observations. The owner clarified the contexts for GA-7 in issue #73;
  the former prompt-timeout row was removed when the owner decided original prompt behavior is not
  a remaster rule.

The stale Live claims were checked against the current tree and `PROVENANCE.md`, which vendors
only `quick_engine.py`, `savestate.py` and `players.py`. Energy spending is inside the vendored
quick engine, but recovery and post-match condition integration are absent. The current CPU
selection is a stand-in in `goal2/ai/cpu.py`; the original B11F behavior is not integrated.
There are no campaign calendar, confidence, morale, competition, ageing or retirement adapters in
this repository. Existing preview, friendly, session-save, and browser team-management features
remain described only where their files implement them.

### Upstream model entrypoints available to integrate

[derived: source tree inspection at archaeology pin `0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb`]
The following Python modules exist upstream at `runtime/model/`; they are not present in this
repository's `goal2/` tree or provenance manifest. Their inputs are byte records, tables, flags,
ordered draw results or state fields supplied by callers. They are source material to adapt or
deliberately vendor with provenance, not drop-in campaign adapters.

| Upstream module | Entry points at the pin | Integration boundary |
| --- | --- | --- |
| `runtime/model/condition.py` | `strength(word, record, foot_table, foot_index)`, `with_condition(record, energy, form)`, `sweep(...)`; match probability helpers | Imports sibling `keeping` and `quick_engine`; models match condition/attempts, not campaign recovery. |
| `runtime/model/energy.py` | `quick_tick(record, minute)`, `watched_step(record, counter, enabled)`, `restore(record, match_form)`, `form_delta(record, delta)`, `injure(record)`, `recover(record, flag, draws, caps)` | Takes complete 20-byte player records; `recover` consumes caller-ordered RNG draws and cap table. It does not simulate preceding RNG consumers or fixtures. |
| `runtime/model/confidence.py` | `country_rating(continent, continent_rank, world_rank)`, `match_form(...)`, `result_delta(own_rating, opponent_rating, scores, winner, side, special_kind)`, `participant_values(before, delta, role, draws=None)` | Caller preserves operation order, participant roles and draw transcript; it does not model all event morale or friendly arrangement. |
| `runtime/model/morale.py` | `event_clamp(before, delta, persist)`, `injure(before)`, `send_off(before)`, `scorer(before, morale_delta)`, `team_reaction(before, morale_delta)`, `team_panel_morale(morales)` | Caller supplies original event order and panel inputs; aggregate behavior includes the source's unsigned arithmetic. |
| `runtime/model/ageing.py` | `compute_ability(age, peak, rating)`, `retirement_flag(record)`, `aged_record(record)`, `ageing_value(...)`, `year_end_bytes(...)`, `derived_skills(...)` | Year-end processing needs class/profile tables and seed. `recreate_constraints` is re-exported from sibling `recreate.py`. |
| `runtime/model/recreate.py` | `recreate(old, rating, w)`, `managed_replacement(...)`, `new_game_squad(...)`, `managed_pool(...)`, `recreate_contract(...)`, plus RNG/rating helpers | Imports sibling `ageing`; recreation consumes and returns caller-owned RNG state. Inputs include original records, ratings, country records and other-player constraints. |

The pinned `runtime/model/draws.py` provides draw helpers, not a full fixture calendar or
competition lifecycle. No complete importable Python model for F023's builders or F024's silent
competitive result exists at this pin; those remain static evidence plus limited synthetic probes.

## Implementation map and unresolved seams

[designed: owner campaign backlog, 2026-10-15, refined against the evidence above] Implement the
campaign in the following order, while keeping each rule behind a replaceable adapter:

| Area | Replacement seam | Evidence boundary and dispatch constraint |
| --- | --- | --- |
| Calendar and fresh start (T40) | `CampaignState`, ordered fixture records and save/load integrated with `goal2/game/state.py` and `session_save.py` | F023 is a static builder reading. Stage 2 interleaves 384 kind-2 fixtures with 384 kind-1 friendlies. T41 can resolve friendlies only and must stop clearly at an unsupported competitive fixture. Qualification cannot be advanced as a friendly. |
| Condition and availability (T42–T44) | Energy/recovery, confidence/morale and injury/ban adapters around existing match results and selection | F018–F020 and F027 are proposed; isolated probes do not prove fixture-end processing. BM-4 confidence kinds, ban service at fixture end, and BM-9's mapping from competition kinds to injury rules remain unresolved. |
| Competitions (T48–T54) | Other-country result, standings, qualification, decider and finals adapters | F023 is not an executable model. F024's D47E is a static reading plus synthetic Unicorn probes; use it as a documented seam, not as the quick engine. Resolve task dependencies so T50 does not require competitive play before the task that supplies that resolver. |
| Lifecycle (T55–T58) | Ranking, stage-boundary ageing, retirement/recreation, sacking and next-cycle transitions | F016/F017/F025 are evidence, not local modules. F017 reports 800/600/400/200 placement bonuses and +200 per `5E3A`; F023 §§4/7 confirms +200 on kind-3/7 group calls, with no numeric conflict shown. Verify the full ranking update chain; reconcile GA-6's signed sum with BM-3 confidence before implementing sacking. |

[derived: finding F023 §§2, 9 at the pin above, proposed and read from the listing] The
calendar synopsis below is a static builder reading; counts were checked arithmetically against
decoded tables. The fixture list has a play order, not dates. Kind-1 friendlies and competition
kinds share the same ordered fixture records.

| Stage | Campaign year | Competition fixture kinds and counts | Friendlies |
| --- | --- | --- | --- |
| 2 | 1 | kind 2: 384 (12 rounds × 4 continents × 8 groups) | 384 |
| 3 | 2 | kind 3: 48 | 528 |
| 4 | 2 | kind 101 × 8, 102 × 4, 103 × 4 | none |
| 5 | 3 | kind 5: 384 | 256 |
| 6 | 3 | kind 6: 16 | none |
| 7 | 4 | kind 7: 48 | 320 |
| 8 | 4 | kind 8 × 8, 200 × 4, 201 × 2, 202, 203 | none |

Stage 2 is the immediate dependency risk: the 384 kind-2 qualifiers cannot be sent through the
friendly runner. The downstream schedule must either supply a competitive resolver before it
needs to advance past those records or clearly hold there; changing a competitive result to a
friendly would corrupt fixture kind, result handling and later tables.

Open rules that must remain explicit until the named seam resolves them:

- Q020: verify the full ranking update chain and its effect on ratings (T55). F017 reports
  800/600/400/200 placement bonuses and +200 per `5E3A`; F023 §§4/7 confirms `5E3A` is also used
  for kind-3/7 group fixtures with +200 each. No numeric disagreement is identified, though
  F017's “knockout fixture” wording does not describe every call site.
- Q028 and F023/F024 host references: home advantage and host-flag effect (T51/T52).
- Q030–Q032: actual fixture lists, draw behavior and silent results against recorded campaign
  fixtures (T40/T48/T50). The start-stage predicate is statically read: start years divisible by
  4 begin at stage 2; years 2 mod 4 begin at stage 5.
- Q031 and F023 §8: exact ordering when all three table keys tie; the source says no further key,
  but does not establish stable ordering (T49).
- Q033, F027 and BM-4/BM-8/BM-9: ban and injury processing at fixture ends, load/new-game behavior
  and fixture-kind mapping (T42–T44).
- F023 §6: stage-6 playoff home-side interpretation; F027: events during added time and extra-time
  clock; F027: managed stoppage timing (T47/T51).
- F024/F026: formation choice, personal marking override, tactic offset signs and heuristic
  absence of squad-transfer routines (T45/T46).
- F025 and GA-5/6: sacking threshold edge, group exemption and the relationship between the
  confidence sum and BM-3 (T58).
- F029: replay-snapshot exception under a same-iteration substitution and pending goal remains
  unverified; it is not needed to claim the measured next-match persistence (later match evidence).

[designed: owner decision, issue #73, 2026-10-15] Rebuild substitutions stay unlimited in friendlies
and five otherwise. Rebuild table and playoff ties follow the code without adding a coin. These
choices apply to the rebuild; they do not change the original-game evidence.
