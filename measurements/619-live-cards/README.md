# Current running player cards (#619)

[designed: #619] UI-only projection of accepted T196 immutable records; the
backend's default remains false. The running MatchDay explicitly requests true.
Fresh records precede historical event caches; explicit pending R/C/personal
edits precede current records. Mark targets remain separate authoritative event
state. Original keeper/zone display takes precedence over stale target labels.
Pre-kickoff captain, career and archive cards retain their existing meanings.

Model: inherited Codex GPT-6 family; exact variant unavailable.

The ten packet controls fail on accepted main d56e793b (seven failures, three
missing interfaces) and pass after. A separate actual PyPy/UI fail-before run on
ordinary exported d56 source reaches its first natural stop and fails because
player_records was never requested; ui619-natural-before-v1.log preserves it.
This export is an ordinary temporary source copy, with no Git checkout/worktree.

Existing focused packet/fault/UI controls: 41 pass in83.120s. Existing T196 missing
snapshot fault process still fails before event delivery/publication and leaves
the career unchanged. The UI request control proves the actual MatchDay opts in;
legacy direct packet controllers continue omitting the option by default.

Real UI observations build expected decoder inputs independently from actual
backend records, without using production live_cards helpers. Every S19/S09
player row and encountered S16 card checks current raw source, rendered
energy/fitness/morale, performance stars, readiness/cards, facts and personal
settings; counts/hashes only are public. The existing accepted player_card
original-derived decoder remains the display oracle; no new rating formula.
Natural energy/performance changes relative to kickoff are required.

Passing focused journeys on source0abc45b7:

- injury/captain swaps:355.157s;120record checks, including two actual S16 takers;
- requested pause, all eight team flags, Esc return:392.250s;100record checks;
- own/mark pending across team reply, confirmed swap, reopen/Play once:383.501s;
  220record checks, including original opcode replay of all complete decisions.

The personal case retains exact whole UI/PyPy outcome and published career
comparisons, then separately compares every complete decision/all20records with
original opcodes using the same actual choices and preparation. It does not
relabel original full-image result metadata as the sealed image hash.
The older half-time journey passed at7b97db9f in206.197s with60record checks and
all eight tactic confirmations/full exact comparisons. Its observer's only later
change settles queued geometry after restoring20selected labels; old proof stays
historical and the corrected observer is exercised by the newer three journeys.

No existing assertions, fixture, seed or time limit was removed or weakened.
The earlier actual-swap calibration correctly reports a queued-label layout
failure; the read-only settling diagnostic retains that failure and proves a
bounded LayoutRequest flush yields no problems. The observer now uses the same
bounded settling as FixedPage.fit, with no key/timer/engine advance. No production
layout exemption was added. The initial Qt window-attribute calibration is kept.

Two T167 direct reference calls also need explicit live_players=True, in addition
to match_day_policy: their affected real set-piece/default-taker cases are being
verified. No event field is stripped from an equality comparison.
Broad gate/platform CI, merge and preview remain with main; this implementer runs
focused proofs only. Raw natural records/saves remain private.
