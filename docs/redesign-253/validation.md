# Planning validation and limits

[designed: #253] These checks validate a reviewable planning package. They do not accept a future UI, establish performance/usability, decide unknown original meanings or authorize implementation. [validate.py](validate.py) uses stdlib plus read-only Git commands and supports `--root /absolute/checkout`, so a main-owned frozen copy can check the reviewed tree. No reviewer harness or shared permission file is changed here.

## Seven Done-when checks

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

| Contract | Structural/semantic trace check and required human judgment |
| --- | --- |
| DW1 Clear proposal | A/B/C recommendation, O01–O12/gate,10 static SVG/PNG pairs, visibly labelled independent scenarios,20 named XI/bench rows beside complete cards in03/10, actual09 scrollbar/jump and valid preview bounds. Human review reads the whole experience and checks visual legibility/overlap. |
| DW2 Complete parity | Independent234-ID/context oracle and12 skills/5 characteristics; source=destination=rendered sets; distinct delivery/reuse;64 source-name/hash traces equal the accepted manual; country TT01–TT08 destinations/traces. Unknowns stay unknown. Human review checks the inventory against original evidence. |
| DW3 Feeling/usability |15 surfaces/9 journeys, automatic/player/conditional transitions,24 capability rows and all10 exact visible-surface mappings. A linked button does not count as a drawn destination. Trace coverage cannot prove task usability. |
| DW4 Actual current build | Source/artifact hashes,10 actual Qt page captures,3 PTY states, real SDL paintedframe3/Cancel and2 read-only Chromium captures; confirmed disposable baseline, no save and separate Windows pin. No new runtime tour is needed for this documentation rework. |
| DW5 Actionable backlog |7 filed new scopes,9 bounded existing owners, explicit unowned G01–G05/O08–O12 and B02/B05 prerequisites. An existing issue ID is insufficient: an independent field-scope oracle rejects delivery assigned to an excluding contract. Human review checks real source/persistence and scope semantics. |
| DW6 Desktop/technology | Desktop/Python constraints,5 official-source approaches, migration/cost judgments and unresolved choices. No benchmark, migration or prototype is performed. |
| DW7 Decision first/scope | Only task docs, proposed task index and the specifically authorized scope/registry lesson in `docs/model-trials.md`. No broader docs wildcard, production/harness/dependency/original payload allowance. Operative owner approval remains required. |

## Rework checks by class

[designed: R1] `GAP_FIELDS` independently names affected original fields for five excluded capability classes: new watched modes/flags, rearrangement, generated news, durable goal/summary capture/replay, and complete country-profile/rank/record projections. Their primary delivery is explicitly unowned, while existing issues may appear only as bounded conditional reuse. False gap resolution or a capability-register assignment to an excluding issue fails. This is a planning-completeness check; full implementation parity still requires actual supported outcomes or an explicit owner exception, neither granted here.

[designed: R2–R5] The drawing checks inspect20 actual SVG name elements and their XI/bench sections, all12 skills/5 characteristics, a real09 scrollbar/Bench jump, setup without an active career highlight, friendly lineup membership/formation consistency and all10 surface mappings. TT setup/scout locations and country screenshot traces are independently required. Visual review remains necessary: canvas bounds alone do not catch inner-panel overlap. [Illustration contexts](illustrations.json) deliberately separate the friendly, knockout, pool-preview and group examples.

[confirmed: R3 fail-before check] A new formation-versus-named-roles assertion first rejected the Belgium5–4–1 heading: its11 names actually imply4–4–2. [Before-fix receipt](evidence/validation-03/formation-before-fix.json) retains that failure; the corrected static heading passes. This is an illustration correction, not a football-rule or runtime change.

[designed: controls] Twenty saved-byte controls exercise actual old scope assignments and missing information: skill allocation, coordinated skill omission, blank destination, missing original image, removed operative gate, duplicate bounded issue ownership, six excluded field owners, false gap resolution, register overreach, linked-versus-drawn profile, formation disagreement, missing twentieth bench name, absent scrollbar, missing TT setup/scout destination and country TT trace. Every mutation must fail its intended semantic check before finally restoring exact bytes and rerunning positives. No Git reset/restore is used.

## Evidence limits and immutable trials

[confirmed: runtime06/browser03] The Linux evidence observes all desktop pages at actual1x1440×900/900×640, initial real SDL playback and a read-only browser tour. It does not complete a match, operate Windows, establish2x/accessibility/performance or constitute a user study. The disposable captain draft was explicitly confirmed before Watch; Cancel restores that confirmed baseline. No save was written; source/resources remained unchanged. Original failed setup outputs remain in ignored owned paths with hash/excerpt receipts and are not product failures.

[confirmed: historical trials] [validation-01](evidence/validation-01/), [validation-02](evidence/validation-02.json), [filed contracts01](evidence/filed-backlog-01.json) and bounds01–03 are preserved earlier trials. Their older helpers passed structural checks but missed the R1 contract-scope class. They are not the current ownership/visual acceptance oracle. The current [bounds04 receipt](evidence/layout-bounds-04.json) binds all10 final SVG/PNG hashes and zero out-of-canvas text; final human review checks composition. New validation/contract-sync receipts use new paths instead of overwriting earlier evidence. Main separately owns the R6 reviewer-access correction and independent acceptance.

## Recorded rework results

[confirmed: batch03] [Seven individual selectors](evidence/validation-03/selectors.json) pass. [Twenty controls](evidence/validation-03/negative-controls.json) reject their intended defects and restore exact bytes, then positive checks pass. [Baseline controls](evidence/validation-03/baseline-controls.json) show four strengthened design/scope checks fail on the exact prior R1 tracked tree, while all seven checks fail on the initial base's absent package. The [batch receipt](evidence/validation-03/receipt.json) binds the tested helper SHA256 `b4fa05ed0f80c2e0595a1a8d10b8ab61e428b33dd3821d95c4892b5a2b5e5c71`.

[confirmed: contract sync02] [All seven live new issue bodies](evidence/filed-backlog-02.json) match local contracts after the R1–R5 changes, excluding an optional repeated title. Only new issues260–263 were updated; existing independent contracts were not edited. These are dated evidence, not a task-status dashboard or implementation authorization.

[confirmed: repository batch03] [Repository checks](evidence/validation-03/repository-checks.json) pass: links/JSON,16-file provenance and whitespace. These checks retain the explicit docs-only scope and focused process lesson; application/harness/runtime dependencies remain unchanged.
