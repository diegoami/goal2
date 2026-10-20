# Static-package checks

[confirmed: #266 author checks, 2026-10-20] These checks concern documentation and authored illustrations only. They do not certify a native game, original runtime behavior, packaging, accessibility, product approval or a committed plan.

| Check | Observed result |
| --- | --- |
| `python3 docs/vision-266/render.py --check` | Fourteen retained SVG/PNG pairs exactly match temporary regeneration. The900×640 sheet has that actual pixel/viewBox size; other sheets are1440×900. Illustrative roster20/XI11/captain, pool exchange, halftime substitution, scorer eligibility and18′/42′/68′ score chronology pass. Measured text stays within each SVG canvas. Complete-card sheets retain the twelve skill and five characteristic labels. |
| Scenario negative controls | Duplicate squad identity, wrong halftime score, bench player as scorer, changed scorer minute and a five-defender XI labelled4–4–2 each fail the scenario assertions. Saved in-memory values are restored in a `finally` block; clean validation passes afterward. This is story-consistency proof, not an engine/fidelity test. |
| Visual review | All fourteen sheets were inspected as rendered images, including full-size Team/pool/small-window/conditional/direction sheets. Checked names/score chronology, complete card categories, seven distinct Team columns, pool/roster scrollbar cues, confirmation/return routes and target labels. Static images do not prove native geometry/focus. |
| `python3 tools/check_links.py` | Repository-relative Markdown targets exist and JSON parses. External immutable GitHub links are references, not locally validated links. |
| `git diff --check` | No whitespace errors. |
| `node tools/harness/check-opencode-guard.mjs` | Exact local guard dependencies verified after the repository-prescribed explicit setup. No harness/product dependencies or locked files changed. |

[designed: issue Done-when accounting] DW1–DW3 are presented for independent documentation and owner review in the vision, walkthrough and evidence ledger. DW4 requires an explicit owner decision; DW5 requires the later plan/backlog reconciliation and owner commitment after that decision. They remain separate human gates. No script can record those decisions, close #266 as complete, authorize implementation, or approve PR258's plan by validating these static documents. Clean-head repository premerge verification and an owner-selected independent reviewer remain required before any documentation merge.
