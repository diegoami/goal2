# T170c1 consume the actual owned Match

[designed: T170c1/#655] `watched_match.consume_match` consumes the caller's
already configured ordinary Match and returns deeply detached canonical events.
The existing `_drive_match` retains its signature, validations, constructor and
unchanged after-tail `WatchedOutcome` assembly. Its tick setting now passes via
the existing constructor. No engine, worker, schema, campaign or desktop file
changes; no setup, prefix, tail, publication or result projection in the consumer.
Model: inherited Codex GPT-6 family; exact variant unavailable.

The consumer's event/answer loop is byte-identical to its original body at
main e942b2e5. Its callers configure tick/prompt/substitution-control capability
before consumption; it never reads or changes private Match options. Policies,
canonical event order, pitch sequence/watermarks, observer deep copies, pause/drop
handling, explicit False cancellation, enum-only opportunities, prompt handling,
refusal guards and exactly-once edit reports retain their existing behavior.
A tail=False Match completes only its configured match; the route owner resumes
its actual continuation explicitly. No automatic XI or pre-match policy is added.

## Focused controls

`before-v1.log`: all five new consumer controls error before extraction because
consume_match does not exist. `focused-v1.log`: five controls pass after extraction.
These tests deny construction/setup/outcome/projection paths while consuming the
same object, forbid private option access, test observer/event detachment/order,
report-once, False cancellation, opportunities/prompts, pitch numbering and all
existing refusal/invalid-answer guards. The legacy wrapper test requires ticks
in its constructor and leaves outcome construction with the wrapper.

`legacy-focused-v1.log`:21 unchanged cancellation/opportunity/default-decision
and refusal controls PASS,0skips,1.900s. No old test, seed, fixture or limit changed.

## Actual PyPy held route

`owned-v2.log`: six tests PASS,0skips,159.742s on source531f56aa. The actual control
uses hash-checked published E006 bytes, whose original initial XI is already valid.
There are no host XI, fixture or calendar edits. Two plain accepted play_round
calls reach ordinary held Matches; one is consumed through the helper, the other
through direct accepted events()/answer() with the same declared default empty
answers. Unicorn import is positively denied in verified PyPy3.11.

Complete results,1270 ordered canonical events, every physical memory byte, both
pre-tail RNG words, actual return frame and ALL16 registers agree. Parent guest
memory/ALL16/pending ownership stay unchanged before explicit resume. Both arms
then resume the actual continuation, transfer ALL16 at actual000E:6F1D, and agree
on complete post-route state, ordered records, fixture/news effects and key queue.
This is a within-backend wrapper comparison, not an independent original season.

The failed `owned-calibration-v1.log` is retained: a NEW harness assertion incorrectly
required the whole parent record to remain unchanged during the held Match.
[confirmed: reviewed0f9f route.py250–254 and _RoundContinuation.advance] The route
intentionally watches the held Match's RNG and appends its observations to that
record. Main clarified the contract at274dea66. V2 preserves the original prefix,
requires ONLY documented ('rng',...,where='match') additions, and compares the
entire198316-entry suffix exactly between arms. Parent guest memory/ALL16 remain
strict; no normalization, dropped trace entry or production engine fix is used.

## Unchanged actual journeys and source identity

`friendly-v1.log`: unchanged full T151 friendly/bench/pause PASS,1test,0skips,
146.990s, score2:1. Every original result/event/memory/seed/state-immutability
assertion is retained, including the established original/port comparison boundary.

`actual636-v1.log`: unchanged actual Window/PyPy substitution accept journey PASS,
1test,0skips,324.631s. BOTH live_players and substitution_control are True. The
natural request, timed opportunity, Esc acceptance, immediate legal swap, refusal,
tactics and play path retains all full result/events/memory/seeds/career equality
and exactly-once publication assertions. Qt uses offscreen Linux; this receipt
makes no new native Windows/package claim. Original records, owner data and raw
captures stay private in the ignored cache; only hashes/counts/declared key choices
and public-safe source receipts are committed.

Those two journeys ran at624b7681. `source-freeze-v1.json` records their source
inputs. After they ended, main274dea66 was normally merged and only the NEW held
proof's unsupported record assertion changed. All previous application, engine,
UI, old test, fixture and runtime inputs remain byte-identical. `acceptance-v1.json`
binds the final code, current proof and historical receipts with this explicit
T189 identity; it never relabels old receipt SHAs. Main owns the default gate/CI/merge.

Repeat focused controls (full held match is explicitly slow):

```sh
source .cache/cloud.env
GOAL2_SLOW=1 .cache/venv/bin/python -B -m unittest goal2.tests.test_owned_match_driver_t170c1 -v
GOAL2_SLOW=1 .cache/venv/bin/python -B -m unittest goal2.tests.test_port_route_t151.PortRoute.test_a_watched_friendly_with_bench_answers_and_a_pause -v
GOAL2_SLOW=1 .cache/venv/bin/python -B -m unittest goal2.tests.test_substitution_actual_636.ActualRequestJourney.test_natural_request_opportunity_escape_immediate_swap_refusal_tactics_and_play -v
```

Actual cases declare their existing optional private input/dependency requirements;
no skip counts as proof. All retained local required cases ran with zero skips.
Use durable jobs and shared heavy slots for long repeats. Do not run a full suite
or duplicate active jobs. A configured route profile/worker transport and T170's
full-season/ageing/Core/UI acceptance remain separate; T170c1 does not activate them.
