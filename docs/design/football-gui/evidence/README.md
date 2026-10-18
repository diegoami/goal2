# Planning validation and visual inspection

[designed: #182] These records validate the **original design study and backlog**,
not runtime Qt/SDL behavior, Windows support, engine fidelity or completed #182.
The prototype uses invented player names/values/results. Original screenshots and
resources were viewed privately and are absent from this tree.

## Reproduce the planning checks

```sh
python3 tools/desktop-ui/check-design-plan.py
python3 tools/check_links.py
export PLAYWRIGHT_MODULE=/absolute/path/to/playwright/index.js
export PLAYWRIGHT_BROWSERS_PATH=/absolute/path/to/browser-cache
mkdir -p .cache/tmp
TMPDIR="$PWD/.cache/tmp" node tools/desktop-ui/inspect-design-plan.mjs .cache/new-gui-inspection
```

[designed] Use an output directory that does not exist; the inspector refuses to
overwrite retained evidence. The browser needs an installed Chromium. No dependency
or network fetch is added to the application. Exact-head offline premerge remains
`python3 tools/check_premerge.py --expected-head <full-head>` on a clean checkout.

[derived: `01-baseline.txt`] Before any manifest, mockup or child contract existed,
the semantic command failed on the missing planning deliverables. The completed
command validates the six reserved bounded contracts, dependency cycles, owner
model assignments, ownership/platform/regression topics, three screen assets and
explicit preview/busy/unsupported/empty contexts. It does not test prose wording.

[derived: `04-preview-negative.txt`] A saved-byte mutation bound displayed country
labels to the active country instead of the selected preview. The same browser
check failed at its intended France-versus-Netherlands assertion; the exact
original JS bytes were restored in a `finally` block. The accepted final-study
source hashes remain those in browser03.

[derived: `browser-02/inspection.json`] First rendered inspection passed eleven
interaction/layout checks and produced six screenshots. This batch predates the
explicit bench list and corrected Dutch national stripe; it is retained rather
than overwritten. Initial Playwright loading needed its CommonJS default export;
that local-tool failure produced no accepted browser result.

[derived: `browser-03/inspection.json`] The next batch records the five source
SHA256s, eleven browser checks and six screenshots after those visual corrections.
The checks exercise active country/selected-country roster, preview guards,
invalid-XI refusal, draft return/discard, busy/cancel, unsupported play, empty
result, keyboard navigation/focus, explicit activation and horizontal shell fit.
Screenshots cover1440×900,1050×780,900×700 and720×450 logical viewports. The last
is a reduced logical-space study, **not Windows200% DPI evidence**. Large screens,
preview1050 and reduced layouts were visually inspected for hierarchy and clipping.
The roster has its own scroll region; document scrolling keeps later controls
reachable. Browser full-page capture can show the sticky draft bar over the
currently visible rows; it is not a claim about Qt widget geometry.

[designed] Runtime T74–T79 must separately prove real Qt/SDL events, actual state
encodings/saves, focus/accessibility, practical window sizes and real Windows
100%/200% scaling. The HTML does not implement pool exchange, real save/resume,
all availability edges, original boards or full source-ID semantics. No browser
result satisfies those future Done-when lines.

## Reference image identity without copied bytes

[confirmed: archaeology accepted pin424d5998076da1e4efc399c2715689ddb44d3e1a]
The privately inspected files matched `git show <pin>:<path>` byte-for-byte by
SHA256. These hashes identify references; only newly authored prototype screenshots
above are committed here.

| Private source path | SHA256 |
| --- | --- |
| `static/screens/png/E015-r0007-state0016.png` | `ca9800a4ab92d3b475edd377ebd8f9dd93d9f0d2721f493392959a62541808e7` |
| `static/screens/png/E015-r0007-state0076.png` | `295bd9aaee62a32ffbe1df59bdaaae9079d62e9571d1a3cf30732ae642739938` |
