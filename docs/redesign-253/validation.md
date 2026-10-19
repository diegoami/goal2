# Planning validation and limits

[designed: #253] These checks validate the reviewable planning package. They do not accept a future UI, establish game performance, substitute for visual/manual review or authorize redesign implementation. [validate.py](validate.py) uses only the standard library and read-only Git commands. Its source is independently freezable; `--root` selects the reviewed checkout rather than the helper location.

## Seven Done-when checks

[designed: #253] Run from the checkout root. Each selector corresponds to one issue Done-when paragraph; the final evidence records the output and exact helper hash. The independent reviewer still judges completeness, usability and the evidence's actual meaning.

```text
python3 -I docs/redesign-253/validate.py --check proposal
python3 -I docs/redesign-253/validate.py --check parity
python3 -I docs/redesign-253/validate.py --check journeys
python3 -I docs/redesign-253/validate.py --check current
python3 -I docs/redesign-253/validate.py --check backlog
python3 -I docs/redesign-253/validate.py --check technology
python3 -I docs/redesign-253/validate.py --check scope
python3 -I docs/redesign-253/validate.py --negative-controls
```

| Contract | Structural check and human evidence |
| --- | --- |
| DW1 Clear proposal | A/B/C comparison, recommendation, O01–O07 and operative approval gate;10 valid static SVG/PNG sheets; complete owner index. Human review reads layouts/journeys and compares originals. |
| DW2 Complete parity | Independent234-ID/context oracle, explicitly named12 skills/5 characteristics, source=destination=rendered field sets, valid destinations and owners,64 unique source names/hash traces equal the accepted manual (63 distinct byte hashes). Human review checks omissions/meanings against manual/source. |
| DW3 Original feeling and modern usability |15 surfaces/9 complete journeys, conditional/automatic/player transitions, capability register; layouts and assessment explain national context, density and interaction. Trace checks cannot establish usability. |
| DW4 Current build assessed | Actual captured product source hashes equal3335da83, retained source/resource/artifact reports,10 Qt page captures,3 PTY frames, actual SDL paintedframe3 then Cancel,2 read-only browser captures. Installed Windows pin is explicitly separate. |
| DW5 Linked actionable backlog |7 filed new contracts,9 protected existing ownership areas, dependency/gate checks, unique ownership and task index. Human review checks acceptance scope and live GitHub body equality. |
| DW6 Desktop/technology | Desktop/Python constraints,5 credible approaches, official sources, relative migration/cost and explicit unresolved choices. No benchmark or stack migration is performed. |
| DW7 Decision package before implementation | All changed paths limited to planning docs/index; no production/dependency/original payload; operative approval gate. The owner still must explicitly select/approve a direction. |

## Evidence limits

[confirmed: runtime06/browser03] The Linux tour observes all current desktop pages at actual1x1440×900/900×640, initial native SDL playback and a read-only browser tour. It does not rerun full native/engine acceptance, complete a match, operate the Windows launcher, measure2x/accessibility/performance or claim a user study. The sample captain draft was explicitly confirmed before Watch; cancellation restores that confirmed disposable baseline. No save was written and source/resources remained unchanged. Earlier display/setup failures remain in ignored task-owned paths with immutable hash/excerpt receipts; they are not described as product failures.

[designed: saved-byte controls] Omission controls remove Penalties from one or both inventories, blank a destination, remove an original-screen ledger row, remove the operative gate and give B03 real campaign-data ownership already held by #249. Each must be rejected; finally restores exact original bytes and reruns positive checks. A script cannot prove that every evidenced field was inventoried correctly: the original manual, authored inspection ledger and independent semantic/visual review supply that assurance. Future discovered fields extend the contract rather than being hidden to retain a count.

## Recorded planning results

[confirmed: validation batch01] [Seven positive checks](evidence/validation-01/checks.json) pass; [six meaningful negative controls](evidence/validation-01/negative-controls.json) are rejected and restore exact bytes; the [same frozen helper on the exact base tracked-tree archive](evidence/validation-01/base-absence.json) fails all seven checks because the package is absent. The helper SHA256 is `d10833f7f56ec48f8e0201c5eb143e9241ddcf56fcdaed67aee928e7d36e267f`; [command/exit receipt](evidence/validation-01/command-receipt.json) records invocation details.

[confirmed: static artifact check] [Qt bounds/preview receipt](evidence/layout-bounds-01.json) records hashes for all10 SVG/PNG pairs, valid static SVG and1600×1010 PNG previews, and zero text outside the canvas. This checks canvas bounds, not text overlap or actual desktop geometry; final visual inspection supplies the layout judgment. [Live filed-contract audit](evidence/filed-backlog-01.json) records equality with all seven GitHub issue bodies, excluding an optional repeated title.
