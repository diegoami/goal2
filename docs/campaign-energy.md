# Campaign energy integration

[designed: owner, 2026-10-16] Campaign work continues alongside the original
watched-engine track. T42 integrates energy for the quick campaign runner;
ordinary standalone friendlies retain their established behavior. The future
watched-result publisher must use original returned state directly, without
invoking this quick-only adapter.

[derived: F018/F007/F027, goal2-archaeology
`0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb`] The vendored `energy.py` models
3651 recovery from ordered draws and CB7D restoration. The rebuild adapter
`campaign_energy.py` connects those operations and source-read 3558/5A8F/9A32
rules to the quick campaign flow. F018 combines proposed static readings with
isolated original-code probes; it is not a seed-exact whole campaign model.

[derived: F018, code/seg_0791_16.asm 998C and 9A32] Start with current energy;
998C has no first-half bonus. The vendored quick engine already spends one
energy per five-minute pitch-slot visit while signed energy exceeds one. Before
the second half, visit the current pitch and add two only for energy 1..30:
zero, 31, 32 and negative encodings remain unchanged. At match end, restore
fitness to signed-positive energy for both squads; this is not a constant-32
refill. [designed: T42] Preserve current form until confidence/shadow integration;
T42 does not claim the complete CB7D form behavior.

[derived: F018/F027, B7FA and 1771:5A8F/5A38/5A03] Recovery selects gradual
3651 when the source result-kind set contains the fixture kind, or the current
side's continent differs from the fixture's second country's continent for a
friendly. The second side compares against itself. Otherwise use 3558 redraw.
The adapter reads result-set membership and age-based bases/caps from the local
image; no extracted original tables are committed. XI and status-set element-3 bench
participants (mask `0x04`, because `214B:0C57` decrements the element number) use flag one; unused bench uses zero.

[derived: F018/F007] Gradual recovery consumes the actual rand(2)/rand(8) or
rand(3)/rand(2) sequence and the healing draw when required; injured zero is not
an automatic refill. Redraw uses its managed/unmanaged branch and preserves the
source's upper-clamp, energy-copy, lower-clamp order. Values and draw counts are
checked by literal reference tests, including age thresholds and signed edges.

[designed: T42] The energy-only transition traverses side A then B, squad slot
order. Confidence, pool and status updates are separate campaign tasks and can
add/interleave draws later. There is no claim of whole post-fixture RNG parity,
calendar-day recovery, or complete watched-engine behavior. Energy changes are
part of the detached match candidate: restore, recover, retain final RNG and
record the fixture identity, then validate/publish the browser state together
with campaign completion/history. Duplicate energy completion is refused.
Reads, Save, Load and preview do not recover; a saved pre-transition session
continues identically to an uninterrupted one. The existing squad view displays
energy from the newly published player records.

[designed: T42] `GameState.match_state.campaign_energy` stores the completed
fixture identity, `quick-energy-v1` marker and recovery draw count. The existing
explicit save format preserves it, without reinterpreting legacy v1/v2 data.
A new pending fixture has a different identity; stale play tokens and duplicate
fixture submissions remain guarded by T41's transaction boundary.

```sh
python3 -m unittest goal2.tests.test_campaign_energy -v
python3 -m unittest goal2.tests.test_campaign_energy.CampaignContinuations -v
```
