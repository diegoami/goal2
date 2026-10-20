# Static-package checks

[designed: #266 author-reported checks, 2026-10-20] These checks concern documentation and authored illustrations only. They do not certify a native game, original runtime behavior, packaging, accessibility, product approval or a committed plan.

| Check | Author-reported result |
| --- | --- |
| `python3 docs/vision-266/render.py --check` | Nineteen retained SVG/PNG pairs exactly match temporary regeneration. Two sheets are actually 900×640; the others are 1440×900. Roster 20 / XI 11 / captain / 4–4–2, exchanges and 18′/42′/68′ chronology pass. The scenario checks reject cloned profiles and out-of-domain characteristic examples. |
| Bar and roster checks | Nine complete cards, 153 attribute bars. Printed raw text must equal its scenario field; fill pattern/count must match the original-domain formula, not just self-reported metadata. Segment rectangles must have positive width (≥1px), height ≥12px, remain within the canvas, and form ordered nonoverlapping rows. Text is ≥18px. Roster name fill differs from its actual row background; normal full rosters use 24px names. These are bounded SVG checks, not a general rendering/accessibility proof. |
| Match composition | The actual playing field is 1406×758 / (1440×900) = 82.2%. The 1424×776 surround is 85.3%. The checker measures the tagged field rectangle and requires ≥82%; shrinking the field with its surround intact fails. Full commentary/top/side chrome is absent and exactly two recent lines remain. |
| `python3 docs/vision-266/check_examples.py` | Twelve independent SVG mutations, four scratch-renderer mutations and seven scenario mutations are rejected. Cases include missing/zero-area segments, forged printed values/fill counts, characteristic formula drift, a shrunk actual field, black roster names, small bar text, a third recent line, focus chrome, cloned profiles and story contradictions. Clean checks pass after each; source/retained exports are never modified. |
| Visual inspection | Open all nineteen rendered targets, including both actual 900×640 panes. Compare with the original squad/pool, tactics, history, summary and career references. Check type/overlap, five descriptor slots, decision tradeoffs, colors/team legend, records, context, navigation and restore handles. Static images do not prove native geometry, focus, scroll or scaling. |
| `python3 tools/check_links.py` / `git diff --check` | Repository-relative targets exist, JSON parses and whitespace checks pass. External immutable GitHub links are references, not locally validated links. |

[designed: reviewer setup] The earlier independent Claude review could regenerate the illustrations after installing Inkscape, but its full premerge stopped at missing guard dependencies. Each fresh review checkout needs the setup explicitly prescribed by [the repository environment instructions](../environment.md):

```bash
npm ci --prefix tools/harness/opencode-guard --ignore-scripts --no-audit --no-fund
node tools/harness/check-opencode-guard.mjs
python3 docs/vision-266/render.py --check
python3 docs/vision-266/check_examples.py
python3 tools/check_premerge.py --expected-head <full-reviewed-SHA>
```

[designed] Authoring requires Python/Pillow, the installed DejaVu Sans Mono fonts and Inkscape (the retained exports use Inkscape 1.2.2). Prepare these before entering a read-only review. Guard setup is the locked local tooling install above, not permission to alter dependencies or skip checks. The full premerge result and exact SHA belong on the PR; #268 records the existing intermittent cancellation fixture and is not fixed by this package.

[designed: issue Done-when accounting] DW1–DW3 are presented for independent documentation and owner review. For DW4, the owner explicitly requested visual changes on 2026-10-20; the [recorded direction](evidence.md#owner-correction-and-original-screen-study) is incorporated, but final approval of the revised whole vision is not inferred. DW5's plan/backlog reconciliation and commitment follow a selected destination. No script closes #266, authorizes implementation or approves PR #258's plan by validating these illustrations. Clean-head repository checks and independent review remain required before any documentation merge.
