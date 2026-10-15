# Live browser acceptance

[designed: T35] `acceptance.mjs` drives a real Chromium browser against the
Python server and checks country switching, Python-sourced roster fields,
template matchup, server choice after reload, browser errors and desktop/mobile
layout. It reads local fixture paths only; the repository must not contain
original savestate or GOAL.DAT bytes.

```sh
PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs \
  node tools/browser-ui/acceptance.mjs --scenario countries
```

The default smoke uses `.cache/e010-r0001-halftime.sav` and `.cache/GOAL.DAT`.
Use `--savestate`, `--goaldat`, or `--url` to point at another local fixture or
already-running server. Set `SCREENSHOT_DIR` to an existing directory to save
390px and 1280px captures.
