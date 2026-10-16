# Campaign halftime substitutions

[designed: T47; owner BM-7] Campaign quick friendlies pause after the first half.
Choose an outgoing starter and available bench player, then **Substitute**.
Repeat as needed; friendly substitutions are unlimited, but a player who goes
off cannot return in this match. **Continue second half** is a once-only action.
The shared policy caps other fixture kinds at five substitutions; competitive
match execution remains unavailable.

[derived: F027/F029, proposed archaeology findings at
`0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb`] Managed substitution swaps the
country squad words, calls the vendored C5DC rebind/used-player marker/sort,
and does not copy the outgoing position byte onto the incoming player. The
current managed XI and country words persist after an actual substitution.
[designed] A substituted captain is replaced by the incoming player, retaining
the full player ID. Existing ordered player-condition/eligibility updates consume
the used-bench marker once at full time. No original watched timing, replay or
whole-game setup fidelity is claimed. The selected halftime changes precede the
existing second-half energy bonus, an explicit rebuild interaction boundary.

[designed] One local worker retains one live QuickMatch across both halves:
RNG, pitch, scorer shadow, computer changes and counters are never restarted.
The UI receives a JSON preview and keeps only a draft substitution plan; the
worker independently validates it before continuing. Full-time candidate
publication uses the existing state-identity/snapshot check and ledger path.
A duplicate or stale continuation is refused. Failure, cancellation or window
close discards the private match and keeps the active game and previous save.
No Python object serialization or HTTP layer is used.

[designed] Saving while a match is pending is explicitly unavailable, including
at halftime. The Save control is disabled, the reason is displayed, and the
model refuses a direct save before writing anything. Finish or cancel first.
Previous full-time saves remain resumable. Standalone friendlies keep the
uninterrupted quick path. A no-change campaign continuation matches the complete
pre-T47 uninterrupted state, including RNG, records and history.

[designed: regression evidence] Two SHA-256 literals in
`goal2/tests/test_campaign_substitutions.py` hash the explicit JSON session saves
produced by base commit65ab461, country4, captain61/tactics165, the verified
E010-r0008 template and first two scheduled friendlies. They protect the complete
no-substitution continuation independently of the new split wrapper. Original
resource bytes remain local and ignored.

```sh
python3 -m unittest goal2.tests.test_campaign_substitutions -v
python3 tools/desktop-ui/prove-halftime.py
QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/acceptance.py --scenario campaign-halftime --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT
```
