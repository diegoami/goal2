# goal2 browser preview

[designed] This is a standalone, in-memory interface preview with fictional sample values. It does not connect to the game engine and does not simulate or save matches.

From the repository root, start a local static server:

```sh
python3 -m http.server 8000 --directory docs/prototypes/browser-ui
```

Open `http://localhost:8000`. On another computer, replace `localhost` with the serving computer’s LAN address (for example, `http://192.168.1.20:8000`) and allow the connection through its firewall. Both computers must be on a network that can reach the server. Stop the server with Ctrl+C.

Run the state tests with `node --test docs/prototypes/browser-ui/state.test.mjs`. Run the real-browser acceptance check with `PLAYWRIGHT_MODULE=/path/to/playwright node docs/prototypes/browser-ui/acceptance.mjs`; set `SCREENSHOT_DIR=/path/to/output` to also capture desktop and mobile page screenshots.
