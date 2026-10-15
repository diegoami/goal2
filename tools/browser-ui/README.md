# Live browser management and acceptance

[designed: T35, T36] `acceptance.mjs` drives a real Chromium browser against the
Python server. The `management` scenario checks a non-Denmark country,
lineup/captain/eight tactics confirmation, the confirmed preview, reload, draft
cancellation, rejected invalid states, keyboard focus and mobile layout. The
`countries` scenario checks country switching, Python-sourced roster fields,
matchup and layout. Both read local fixture paths only; the repository must not
contain original savestate or GOAL.DAT bytes.

```sh
PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs \
  node tools/browser-ui/acceptance.mjs --scenario management
```

The default smoke uses `.cache/e010-r0001-halftime.sav` and `.cache/GOAL.DAT`.
Use `--savestate`, `--goaldat`, or `--url` to point at another local fixture or
already-running server. Set `SCREENSHOT_DIR` to an existing directory to save
390px and 1280px captures.

For the live flow, start `python3 -m goal2.web .cache/<savestate>.sav
.cache/GOAL.DAT` from the repository root and open the printed localhost URL.
Edit the lineup, captain and tactics on the Squad page; **Confirm team** updates
the Python-owned in-memory session, and **Cancel draft** restores its confirmed
choices. Reload reads the same session while the server remains running. The
matchup card resolves names and managed side without simulating a match or
writing a save.
