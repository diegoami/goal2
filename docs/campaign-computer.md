# Campaign computer preparation

[derived: F007/F024/F027, archaeology `0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb`]
Player ability is byte+4; age is+1. Correction#145 removes the old age sort
from the documented top-ability stand-in and corrects synthetic fixtures that
repeated the wrong layout. This changes quick-match outcomes; it is not a
mechanical fix or an original lineup-fidelity claim.

[designed: T46] `game.computer.prepare` reads the opponent's current twenty
country words, validates distinct valid same-country players, filters current
availability and chooses eleven by descending ability then ascending full ID.
The remaining nine retain their relative stored order. It returns immutable
ID tuples and the current stored tactics byte without changing players, country
records, management choices or either RNG. Preparing the human side is refused.
Campaign preview and runner call this same function with the opponent resolved
from the exact scheduled A/B pair. Standalone friendlies keep their setup policy,
with the corrected ability field in their existing selector.

[derived: proposed F024] The original uses B11F's stored-eleven corrections,
then34E7 personal tactics andBD83 country setup. These are not supplied here as
a reusable complete setup model. [designed] Top ability ignoring formation stays
an explicit stand-in; no original best-eleven claim is made. Existing vendored
in-match tactics changes stay covered by T22. At each rebuild fixture start,
the CPU reads its current authoritative country+2D byte; match-local automatic
tactics and squad rearrangements are not published back into country records.
Player condition/scorer effects still publish through the existing quick tail.
A saved continuation preserves the same subsequent setup policy. Original
fixture-start defaults/host/relative-strength additions and personal bits remain
replacement seams, not silently implemented by this task.

[derived: T41a/F023; designed: T46] Source A/B order is preserved for both
managed sides. No home-side interpretation, unknown host field or home-advantage
multiplier is invented. Human XI/captain/tactics remain untouched by CPU setup.
Malformed inputs fail before preview/play publication. Tests inspect actual
kickoff pitch IDs and tactics, and compare complete real two-match continuations
before/after save, separately from synthetic setup probes.

```sh
python3 -m unittest goal2.tests.test_campaign_cpu -v
python3 -m unittest goal2.tests.test_cpu goal2.tests.test_cpu_tactics_change goal2.tests.test_full_match -v
python3 tools/prove_campaign_cpu.py
```
