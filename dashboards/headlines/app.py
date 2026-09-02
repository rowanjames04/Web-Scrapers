"""Menu bar app for the headlines dashboard.

Same server serve.py runs, but living inside a menu bar app instead of a
Terminal window: it starts when the app launches and stops when you quit it.
The menu opens the dashboard and refreshes either feed on demand.

The server code itself is imported from serve.py rather than copied, so the
endpoint, the source keys and the one-refresh-at-a-time lock stay in one place.

    python3 dashboards/headlines/app.py

install-app.py wraps this into an app bundle for the Applications folder.
"""

import http.server
import os
import socket
import subprocess
import sys
import threading
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))

# Launched from an app bundle the working directory is arbitrary, so make sure
# serve.py is importable by path rather than by luck.
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import rumps

import serve

URL = "http://{}:{}/".format(serve.HOST, serve.PORT)

# Chrome's app mode gives a standalone window with no tabs or address bar, which
# is much closer to "an app" than a tab in whatever browser happens to be open.
# Without Chrome this falls back to the default browser.
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def open_dashboard_window():
    """Show the dashboard. Logged, because there is no Terminal to watch."""
    try:
        if os.path.exists(CHROME):
            print("opening window: chrome --app")
            subprocess.Popen(
                [CHROME, "--app=" + URL],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        else:
            print("opening window: default browser")
            webbrowser.open(URL)
    except OSError as error:
        print("could not open a window: " + str(error))


def already_serving():
    """True when something already holds the port - usually a second launch."""
    with socket.socket() as probe:
        probe.settimeout(0.5)
        return probe.connect_ex((serve.HOST, serve.PORT)) == 0

# Menu bar glyph. Swap for a template image if you want something monochrome.
IDLE_TITLE = "📰"
BUSY_TITLE = "⏳"


class HeadlinesApp(rumps.App):
    def __init__(self):
        super().__init__("Headlines Dashboard", title=IDLE_TITLE, quit_button=None)

        self.status_item = rumps.MenuItem("Starting…")
        self.menu = [
            rumps.MenuItem("Open Dashboard", callback=self.open_dashboard),
            None,
            rumps.MenuItem("Refresh Both Feeds", callback=self.refresh_all),
            rumps.MenuItem("Refresh Ars Technica", callback=self.refresh_ars),
            rumps.MenuItem("Refresh news.com.au", callback=self.refresh_news),
            None,
            self.status_item,
            None,
            # The bundle runs this file straight from the repo, so a restart is
            # all it takes to pick up code you just edited.
            rumps.MenuItem("Restart App", callback=self.restart_app),
            rumps.MenuItem("Quit", callback=self.quit_app),
        ]

        self.server = None
        self.busy = False

        # Worker threads never touch the menu directly. They leave a message
        # here and a timer on the main thread picks it up, because AppKit is
        # not safe to drive from a background thread.
        self.lock = threading.Lock()
        self.message = "Starting…"

        self.start_server()
        rumps.Timer(self.tick, 0.4).start()

        # Launching an app and seeing nothing happen is not much of an app, so
        # show the dashboard straight away. A restart skips this, otherwise it
        # would pile up a new window every time.
        if "--no-open" not in sys.argv[1:]:
            open_dashboard_window()

    # ---------------------------------------------------------------- server

    def start_server(self):
        if not os.path.exists(serve.HTML_FILE):
            self.say("Building the page…")
            threading.Thread(target=self.build_page, daemon=True).start()

        try:
            self.server = http.server.ThreadingHTTPServer(
                (serve.HOST, serve.PORT), serve.Handler
            )
        except OSError:
            # Something already holds the port - most likely serve.py or the
            # start-dashboard launcher. Use it rather than fighting over it.
            self.say("Using the server already on port {}".format(serve.PORT))
            return

        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.say("Serving on port {}".format(serve.PORT))

    def build_page(self):
        ok, _, _ = serve.run_script(
            os.path.dirname(serve.DASHBOARD), os.path.basename(serve.DASHBOARD)
        )
        self.say("Ready" if ok else "Could not build the page - run the scrapers")

    # ----------------------------------------------------------------- menu

    def open_dashboard(self, _):
        open_dashboard_window()

    def refresh_all(self, _):
        self.refresh(list(serve.SOURCES), "both feeds")

    def refresh_ars(self, _):
        self.refresh(["ars"], "Ars Technica")

    def refresh_news(self, _):
        self.refresh(["news"], "news.com.au")

    def refresh(self, keys, label):
        if self.busy:
            self.say("Already refreshing…")
            return

        self.busy = True
        self.title = BUSY_TITLE
        self.say("Refreshing {}…".format(label))
        threading.Thread(target=self.run_refresh, args=(keys, label), daemon=True).start()

    def run_refresh(self, keys, label):
        """Scrape and rebuild off the main thread so the menu stays responsive."""
        try:
            ok, log = serve.refresh(keys)
            last = (log.splitlines() or ["done"])[-1]
            self.say("Updated {}".format(label) if ok else last)
        except Exception as error:  # a dead network shouldn't take the app with it
            self.say("Refresh failed: {}".format(error))
        finally:
            self.busy = False

    def stop_server(self):
        if not self.server:
            return
        # Stop accepting, then release the port so a restart can rebind it.
        self.server.shutdown()
        self.server.server_close()
        self.server = None

    def restart_app(self, _):
        """Relaunch in place, which is how edited code gets picked up."""
        if self.busy:
            self.say("Busy refreshing - try again in a moment")
            return

        self.stop_server()
        os.execv(
            sys.executable, [sys.executable, os.path.abspath(__file__), "--no-open"]
        )

    def quit_app(self, _):
        self.stop_server()
        rumps.quit_application()

    # ---------------------------------------------------------------- plumbing

    def say(self, message):
        with self.lock:
            self.message = message

    def tick(self, _):
        """Main-thread heartbeat: pull whatever the workers left and show it."""
        with self.lock:
            message = self.message

        if self.status_item.title != message:
            self.status_item.title = message

        wanted = BUSY_TITLE if self.busy else IDLE_TITLE
        if self.title != wanted:
            self.title = wanted


def main():
    # A second launch shouldn't add a second menu bar icon that quietly does
    # nothing. Show the dashboard from the instance already running and stop.
    if already_serving():
        open_dashboard_window()
        return

    HeadlinesApp().run()


if __name__ == "__main__":
    main()
