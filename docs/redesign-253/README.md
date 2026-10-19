# GOAL2 whole-game redesign: owner decision package #253

[designed: owner request #253] **Recommend A: Country desk** — an installable desktop game that makes the country's next challenge the center of play. A persistent country/competition context leads to complete Team decisions, preparation, a tense match and a meaningful return to the campaign. A comparison-first player workspace keeps all original attributes close to selection; a continuous Match centre connects preparation, supported live decisions, statistics and the next fixture.

[designed: #253] **This is a proposal, not implementation approval.** The owner must explicitly select a direction, technology/window assumptions and first milestone before redesign implementation or any new child starts. Filing issues, documentation review and merging this package do not grant approval. No toolkit, backend-language or architecture migration is authorized. Existing independently authorized work retains its own scope. The operative [approval gate](decisions.md#approval-gate) and [O01–O07 decisions](decisions.md#decisions-for-the-owner) record that boundary.

![Proposed Country desk: context, next match and readiness](layouts/02-country-desk.png)

[designed: static planning artifact] The ten annotated layouts illustrate a coherent direction; names, values and events are illustrative and are not current UI captures. Each has an [original-screen comparison and explanation](layouts.md). Complete cards preserve exact sourced values/native scales; unverified meanings and unrecorded values remain explicit. A 900×640 variant shows how relevant decision fields remain reachable.

| Read / decide | Reviewable artifact |
| --- | --- |
| Why the original feels like managing a country; what the current game makes difficult | [Experience and current-build assessment](assessment.md) — desktop, terminal, browser and live SDL observations distinguished from code audit |
| See the whole proposed game | [Ten annotated screens and interaction direction](layouts.md); [screen hierarchy and nine complete journeys](journeys.md) |
| Check no original information was silently removed | [234-field/state parity contract](information-parity.md), [management](parity/management.md), [campaign](parity/campaign.md), [match](parity/match.md); [all64 visually inspected images](evidence/screens-inspected.tsv) |
| Compare credible directions and choose | [A Country desk / B Broadcast career / C Modern command room](decisions.md), with A recommended and deliberate departures explained |
| Choose a desktop technology policy | [Python/backend and five frontend approaches](technology.md) — recommend retaining Python, Widgets and the accepted SDL boundary for the first delivery, subject to a bounded native proof; Qt Quick is the strongest migration alternative |
| Review what would be built, in what order | [Prioritized milestones and acceptance tasks](backlog.md), [seven filed child contracts](backlog.json), [existing capability ownership](capabilities.tsv), [task index](../tasks/README.md#whole-game-redesign-decision-package-253) |
| Audit claims, sources and checks | [Reading/source ledger](evidence/reading.md), [runtime report](evidence/runtime-06/report.json), [browser report](evidence/browser-03/report.json), [validation and limitations](validation.md) |

[designed: first coherent slice] After approval: native feasibility → new/load with safe identity/save handling → Country desk and complete Team/pool comparison → confirmed supported friendly → Quick with existing halftime choice or Watch with current view-only pitch → explained result → next fixture → Save/Resume. Missing roles, country/history data, watched interventions and retained summaries reuse #248–#251; full parity also needs later actual assistant/identity and local-manager capabilities after B06/B07 audits. A placeholder or contract alone is not full parity.

[confirmed: evidence pins] The accepted illustrated manual is PR247 at `ebdd6879d469a574f6d4b446f59b33a6be3ffd81`. Current product source is audited at `3335da830d289cc869f989b73816926c54360ff1`; runtime checkout `aab447ae15c6208b6f4295b2a8a845c2942f88e9` changes documentation only. All63 game PNGs plus the separate DOS shell were visually inspected. Authentic images are referenced from the existing manual; no original software/data/savestate is added. Original observations, printed hints, unresolved meanings, current runtime facts and proposed choices stay distinct throughout.
