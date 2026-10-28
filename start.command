#!/bin/bash
# Start the RFQ Quote Tool; the browser opens automatically.
cd "$(dirname "$0")" || exit 1

if [ ! -x .venv/bin/python ]; then
  echo "Runtime not found, running install.command ..."
  bash "./install.command"
fi

if [ ! -x .venv/bin/python ]; then
  echo ".venv missing. Please run install.command first."
  read -r -p "Press Enter to exit..."
  exit 1
fi

exec .venv/bin/python -m quote_app.server
