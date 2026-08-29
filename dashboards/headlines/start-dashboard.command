#!/bin/bash
# Double-click this in Finder to start the server and open the dashboard.
#
# Finder runs a .command file in a new Terminal window with the working
# directory set to your home folder, so the first job is to find our own.
# Closing that window, or pressing Ctrl-C in it, stops the server.

cd "$(dirname "$0")" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 was not found on this Mac."
  echo "Install Python 3, then double-click this again."
  echo
  read -r -p "Press return to close. "
  exit 1
fi

python3 serve.py --open
status=$?

# On a clean Ctrl-C the window can just close. On a failure, hold it open so
# the error is readable instead of vanishing with the window.
if [ "$status" -ne 0 ]; then
  echo
  read -r -p "Server exited with an error. Press return to close. "
fi

exit "$status"
