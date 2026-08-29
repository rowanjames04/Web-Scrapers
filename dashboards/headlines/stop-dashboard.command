#!/bin/bash
# Double-click this in Finder to stop the dashboard server.
#
# Closing the Terminal window that start-dashboard.command opened stops it too.
# This is for when that window is gone, or the server was started some other way.

cd "$(dirname "$0")" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 was not found on this Mac."
  echo
  read -r -p "Press return to close. "
  exit 1
fi

# Ask serve.py itself which port it uses, so the two can't drift apart.
port=$(python3 -c 'import serve; print(serve.PORT)') || exit 1

pids=$(lsof -ti "tcp:$port" -sTCP:LISTEN 2>/dev/null)

if [ -z "$pids" ]; then
  echo "Nothing is listening on port $port - the server is already stopped."
  echo
  read -r -p "Press return to close. "
  exit 0
fi

for pid in $pids; do
  # Port 8000 is popular. Only ever stop our own server, never whatever else
  # happens to be holding the port.
  if ! ps -o command= -p "$pid" | grep -q "serve\.py"; then
    echo "Port $port is held by PID $pid, which is not this dashboard:"
    ps -o command= -p "$pid" | sed 's/^/    /'
    echo "Leaving it alone."
    continue
  fi

  # Ask nicely first, so serve.py gets to close its socket on the way out.
  kill "$pid" 2>/dev/null

  for _ in 1 2 3 4 5 6 7 8 9 10; do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.2
  done

  if kill -0 "$pid" 2>/dev/null; then
    kill -9 "$pid" 2>/dev/null
    echo "Force stopped the server (PID $pid)."
  else
    echo "Stopped the server (PID $pid)."
  fi
done

echo
read -r -p "Press return to close. "
