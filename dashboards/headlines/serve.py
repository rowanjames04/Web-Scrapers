"""Serve the headlines dashboard with working refresh buttons.

dashboard.html is deliberately self-contained and opens straight from disk.
That also means it cannot re-run anything: a page on file:// has no way to
start a Python process. This server is the optional other half. It serves the
same page and exposes one endpoint that runs the scrapers and regenerates the
HTML, which is what the refresh buttons call.

Opened from disk the page still renders in full; the buttons just explain what
to run instead. Nothing here is required to read the dashboard.

Stdlib only:

    python3 dashboards/headlines/serve.py
"""

import http.server
import json
import os
import subprocess
import sys
import threading
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

HTML_FILE = os.path.join(HERE, "dashboard.html")
DASHBOARD = os.path.join(HERE, "dashboard.py")

# Bound to localhost on purpose: this endpoint starts processes, so it has no
# business listening on anything the rest of the network can reach.
HOST = "127.0.0.1"
PORT = 8000

# The only scripts this server will run. A request names a key, never a path.
SOURCES = {
    "ars": ("ArsTechnicaScraper", "ArsTechnicaScraper.py"),
    "news": ("NewsComAuScraper", "NewsComAuScraper.py"),
}

SCRAPE_TIMEOUT = 180

# One refresh at a time. Two scrapers writing the same CSV, or two dashboard
# runs writing the same HTML, would race each other.
refresh_lock = threading.Lock()


def run_script(folder, script):
    """Run one script from inside its own folder, as the scrapers expect."""
    result = subprocess.run(
        [sys.executable, script],
        cwd=os.path.join(REPO, folder),
        capture_output=True,
        text=True,
        timeout=SCRAPE_TIMEOUT,
    )
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def refresh(keys):
    """Scrape the named sources, then rebuild the page. Returns (ok, log)."""
    log = []

    for key in keys:
        folder, script = SOURCES[key]
        ok, output = run_script(folder, script)
        log.append(script + ": " + (output.splitlines() or ["no output"])[-1])
        if not ok:
            return False, "\n".join(log + ["failed, page left unchanged"])

    ok, output = run_script(os.path.dirname(DASHBOARD), os.path.basename(DASHBOARD))
    log.append("dashboard.py: " + (output.splitlines() or ["no output"])[-1])
    return ok, "\n".join(log)


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "HeadlinesDashboard"

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        # Browsers ask for this unprompted; answering quietly keeps the log clean.
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        if path not in ("/", "/dashboard.html"):
            self.send_error(404, "Nothing here but the dashboard")
            return

        if not os.path.exists(HTML_FILE):
            self.send_error(404, "dashboard.html not built yet - run dashboard.py")
            return

        with open(HTML_FILE, "rb") as file:
            body = file.read()

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # The file changes under the browser on every refresh.
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path != "/refresh":
            self.send_error(404, "Nothing here but the dashboard")
            return

        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        wanted = query.get("source", ["all"])[0]
        keys = list(SOURCES) if wanted == "all" else [wanted]

        if any(key not in SOURCES for key in keys):
            self.reply(400, {"ok": False, "log": "Unknown source: " + wanted})
            return

        if not refresh_lock.acquire(blocking=False):
            self.reply(409, {"ok": False, "log": "A refresh is already running"})
            return

        try:
            ok, log = refresh(keys)
        except subprocess.TimeoutExpired:
            ok, log = False, "Timed out after {}s".format(SCRAPE_TIMEOUT)
        finally:
            refresh_lock.release()

        self.reply(200 if ok else 500, {"ok": ok, "log": log})

    def reply(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        sys.stderr.write("  " + fmt % args + "\n")


def main():
    server = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    url = "http://{}:{}/".format(HOST, PORT)

    print("Headlines dashboard on " + url)
    print("Refresh buttons on the page will scrape and rebuild it. Ctrl-C to stop.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
