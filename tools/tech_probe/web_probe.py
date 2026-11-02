"""[designed: T158] The web candidate: one local page (web/), served by this Python, shown in a window.

    python tools/tech_probe/web_probe.py [--shell browser|webview|none] [--port 0] [--quit-after S]

--shell browser   the player's own browser as an app window: Edge on Windows (`msedge --app=URL`, always there on
                  Windows 10/11), Chrome/Chromium elsewhere (T158_CHROME names the binary); a private profile in a
                  temporary folder, closed with the probe
--shell webview   a desktop shell around the page: pywebview (Edge WebView2 on Windows, Qt WebEngine or GTK WebKit
                  on Linux); T158_EXTRA_PATH may name a folder pywebview was installed into (pip --target)
--shell none      only the server; open the printed URL yourself

The server is the standard library's (http.server) on 127.0.0.1, with a random token in the URL, as goal2/web
does. It serves the page, the design's own stylesheet and font (docs/design/ui-2026-11/mockups/), the screens'
data (screens.py) and POST /ready, which the page sends after its first frame: the probe prints `READY <s>` (the
time since the probe started) on stdout, and quits --quit-after seconds later. Throwaway.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

START = time.perf_counter()
sys.path.insert(0, str(Path(__file__).resolve().parent))
if os.environ.get("T158_EXTRA_PATH"):
    sys.path.insert(0, os.environ["T158_EXTRA_PATH"])
import common  # noqa: E402
import screens  # noqa: E402

WEB = common.PROBE / "web"
MOCKUPS = common.DESIGN / "mockups"
FILES = {"/app.js": (WEB / "app.js", "text/javascript"), "/style.css": (MOCKUPS / "style.css", "text/css"),
         "/fonts/PxPlus_IBM_VGA_8x16.ttf": (common.FONT, "font/ttf")}
TOKEN = secrets.token_urlsafe(12)
ready = threading.Event()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, body, kind):
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == f"/{TOKEN}/":
            return self._send((WEB / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/data.json":
            return self._send(json.dumps(screens.data(), ensure_ascii=False).encode(), "application/json")
        if path in FILES:
            file, kind = FILES[path]
            return self._send(file.read_bytes(), kind)
        self.send_error(404)

    def do_POST(self):
        if self.path == "/ready" and not ready.is_set():
            ready.set()
            print(f"READY {time.perf_counter() - START:.4f}", flush=True)
        self._send(b"ok", "text/plain")


def chrome():
    if common.WINDOWS:
        for base in (os.environ.get("PROGRAMFILES(X86)", ""), os.environ.get("PROGRAMFILES", "")):
            edge = Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            if edge.is_file():
                return str(edge)
    found = os.environ.get("T158_CHROME") or shutil.which("google-chrome") or shutil.which("chromium")
    if not found:
        raise SystemExit("no browser: set T158_CHROME to a Chrome or Chromium binary")
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shell", choices=("browser", "webview", "none"), default="browser")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--quit-after", type=float)
    parser.add_argument("--headless", action="store_true", help="browser shell without a window (Linux measurements)")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/{TOKEN}/"
    print(f"URL {url}", flush=True)
    if args.quit_after is not None:
        def stop():
            ready.wait(120)
            time.sleep(args.quit_after)
            os._exit(0)  # the browser's private profile is a temporary folder; the shell closes with us
        threading.Thread(target=stop, daemon=True).start()
    if args.shell == "webview":
        import webview
        webview.create_window("GOAL2 prototype (web)", url, width=1440, height=900, background_color="#000000")
        webview.start()
        return
    if args.shell == "browser":
        profile = tempfile.mkdtemp(prefix="t158-browser-")
        command = [chrome(), f"--app={url}", f"--user-data-dir={profile}", "--window-size=1440,900",
                   "--no-first-run", "--no-default-browser-check"]
        if args.headless:
            command += ["--headless", "--no-sandbox", url]
        browser = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            browser.wait()
        finally:
            shutil.rmtree(profile, ignore_errors=True)
        return
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
