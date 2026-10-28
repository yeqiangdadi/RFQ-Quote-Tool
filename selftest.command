#!/bin/bash
cd "$(dirname "$0")" || exit 1

if [ ! -x .venv/bin/python ]; then
  echo "The environment is not installed yet. Run install.command first."
  read -r -p "Press Enter to exit..."
  exit 1
fi

.venv/bin/python -m quote_app.selftest
read -r -p "Press Enter to exit..."
