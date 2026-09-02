"""Build 'Headlines Dashboard.app' in the Applications folder.

The bundle is a thin wrapper, not a copy: its executable runs app.py straight
out of this repo. Edit the dashboard, the scrapers or the app itself and the
change is live on the next launch - or on 'Restart App' from the menu. Only
re-run this installer when you move the repo, or to update the icon or name.

    python3 dashboards/headlines/install-app.py

Pass --uninstall to remove the app again.
"""

import os
import plistlib
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
APP_SOURCE = os.path.join(HERE, "app.py")

APP_NAME = "Headlines Dashboard"
BUNDLE_ID = "com.rowanjames.headlines-dashboard"
# /Applications is group-writable by admin users, so no password is needed.
# On a Mac where it isn't, fall back to the per-user Applications folder, which
# Finder, Spotlight and Launchpad all treat the same way.
SYSTEM_APPS = "/Applications"
USER_APPS = os.path.expanduser("~/Applications")


def install_dir():
    if os.access(SYSTEM_APPS, os.W_OK):
        return SYSTEM_APPS
    return USER_APPS


INSTALL_DIR = install_dir()
BUNDLE = os.path.join(INSTALL_DIR, APP_NAME + ".app")
LOG_FILE = os.path.expanduser("~/Library/Logs/HeadlinesDashboard.log")

# The interpreter is pinned rather than looked up on PATH. A Finder-launched
# app gets a minimal PATH and would otherwise resolve python3 to Apple's build,
# which may not have rumps - and with no Terminal, that fails invisibly.
PYTHON = sys.executable

# The two column colours from the dashboard, so the icon matches the page.
ARS_BLUE = (57, 135, 229)
NEWS_ORANGE = (217, 89, 38)
CARD = (25, 25, 23)
LINE = (138, 136, 127)


def check_requirements():
    problems = []

    if not os.path.exists(APP_SOURCE):
        problems.append("app.py is missing from " + HERE)

    try:
        subprocess.run(
            [PYTHON, "-c", "import rumps"], check=True, capture_output=True, timeout=60
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        problems.append(
            "rumps is not installed for " + PYTHON + "\n"
            "    Install it with: " + PYTHON + " -m pip install rumps"
        )

    return problems


def draw_icon(size):
    """Two columns on a dark card - the dashboard's layout, in miniature."""
    from PIL import Image, ImageDraw

    scale = size / 1024.0
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def box(x0, y0, x1, y1, radius, fill):
        draw.rounded_rectangle(
            [x0 * scale, y0 * scale, x1 * scale, y1 * scale],
            radius=max(1, radius * scale),
            fill=fill,
        )

    box(64, 64, 960, 960, 180, CARD)

    # Left column, Ars blue. Right column, news.com.au orange.
    for left, colour in ((160, ARS_BLUE), (544, NEWS_ORANGE)):
        box(left, 200, left + 320, 232, 16, colour)
        for row in range(4):
            top = 296 + row * 108
            width = 320 if row % 2 == 0 else 232
            box(left, top, left + width, top + 56, 14, LINE)

    return image


def write_icon(resources):
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print("  Pillow not installed, skipping the icon (the app still works)")
        return None

    iconset = tempfile.mkdtemp(suffix=".iconset")
    try:
        for size in (16, 32, 128, 256, 512):
            draw_icon(size).save(os.path.join(iconset, "icon_{0}x{0}.png".format(size)))
            draw_icon(size * 2).save(
                os.path.join(iconset, "icon_{0}x{0}@2x.png".format(size))
            )

        icns = os.path.join(resources, "icon.icns")
        subprocess.run(
            ["iconutil", "-c", "icns", iconset, "-o", icns],
            check=True,
            capture_output=True,
        )
        return "icon.icns"
    except (subprocess.CalledProcessError, OSError) as error:
        print("  Could not build the icon, carrying on without one: " + str(error))
        return None
    finally:
        shutil.rmtree(iconset, ignore_errors=True)


def existing_bundle_is_ours():
    """Only ever replace a bundle this installer wrote."""
    plist = os.path.join(BUNDLE, "Contents", "Info.plist")
    if not os.path.exists(plist):
        return False

    try:
        with open(plist, "rb") as file:
            return plistlib.load(file).get("CFBundleIdentifier") == BUNDLE_ID
    except (plistlib.InvalidFileException, OSError):
        return False


def build():
    contents = os.path.join(BUNDLE, "Contents")
    macos = os.path.join(contents, "MacOS")
    resources = os.path.join(contents, "Resources")

    for folder in (macos, resources):
        os.makedirs(folder, exist_ok=True)

    icon = write_icon(resources)

    info = {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleVersion": "1.0",
        "CFBundleShortVersionString": "1.0",
        "CFBundlePackageType": "APPL",
        "CFBundleExecutable": "run",
        # No Dock icon and no Terminal window: it lives in the menu bar.
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
    }
    if icon:
        info["CFBundleIconFile"] = icon

    with open(os.path.join(contents, "Info.plist"), "wb") as file:
        plistlib.dump(info, file)

    # A wrapper, not a copy - app.py is run from the repo so edits are live.
    # Output goes to a log because a bundle has no Terminal to print to, and an
    # app that fails silently is one you cannot debug.
    launcher = os.path.join(macos, "run")
    with open(launcher, "w") as file:
        file.write(
            "#!/bin/bash\n"
            "# Generated by install-app.py. Runs the app from the repo checkout,\n"
            "# so editing the source updates this app - no reinstall needed.\n"
            "log={log}\n"
            "mkdir -p \"$(dirname \"$log\")\"\n"
            "echo \"--- launched $(date) ---\" >> \"$log\"\n"
            "exec {python} -u {app} >> \"$log\" 2>&1\n".format(
                log=shell_quote(LOG_FILE),
                python=shell_quote(PYTHON),
                app=shell_quote(APP_SOURCE),
            )
        )
    os.chmod(launcher, 0o755)

    register()


LSREGISTER = (
    "/System/Library/Frameworks/CoreServices.framework/Frameworks"
    "/LaunchServices.framework/Support/lsregister"
)


def register():
    """Tell LaunchServices the bundle exists.

    Without this a freshly built bundle is unknown to the system: `open` and
    Spotlight quietly do nothing, and Finder shows a stale icon. Rebuilding an
    existing bundle needs it too, so the new icon and plist take effect.
    """
    subprocess.run(["touch", BUNDLE], capture_output=True)

    if os.path.exists(LSREGISTER):
        subprocess.run([LSREGISTER, "-f", BUNDLE], capture_output=True, timeout=60)


def shell_quote(value):
    return "'" + value.replace("'", "'\\''") + "'"


def uninstall():
    if not os.path.exists(BUNDLE):
        print("Nothing installed at " + BUNDLE)
        return 0

    if not existing_bundle_is_ours():
        print("There is something else at " + BUNDLE)
        print("It was not created by this installer, so it has been left alone.")
        return 1

    shutil.rmtree(BUNDLE)
    print("Removed " + BUNDLE)
    return 0


def main():
    if "--uninstall" in sys.argv[1:]:
        return uninstall()

    problems = check_requirements()
    if problems:
        print("Can't install yet:\n")
        for problem in problems:
            print("  - " + problem)
        return 1

    if os.path.exists(BUNDLE) and not existing_bundle_is_ours():
        print("There is already something at " + BUNDLE)
        print("It was not created by this installer, so it has been left alone.")
        print("Move it aside, or change APP_NAME in this script, and try again.")
        return 1

    updating = os.path.exists(BUNDLE)
    os.makedirs(INSTALL_DIR, exist_ok=True)
    build()

    print(("Updated " if updating else "Installed ") + BUNDLE)
    print("  Python:  " + PYTHON)
    print("  Runs:    " + APP_SOURCE)
    print("  Log:     " + LOG_FILE)
    print()
    print("Open it from the Applications folder or Spotlight. It appears in the")
    print("menu bar rather than the Dock, and quitting it stops the server.")
    print()
    print("The app runs the repo's own files, so edits are live on the next")
    print("launch, or straight away with 'Restart App' in its menu.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
