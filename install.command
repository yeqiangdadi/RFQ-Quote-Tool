#!/bin/bash
# First-time setup (needs internet, about 1-2 GB)
cd "$(dirname "$0")" || exit 1

PY=""
for candidate in python3.12 python3.13 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then PY="$candidate"; break; fi
done

if [ -z "$PY" ]; then
  echo "python3 not found. Install Python 3.10-3.13 from https://www.python.org/downloads/"
  read -r -p "Press Enter to exit..."
  exit 1
fi

echo "Using $($PY --version) to create .venv ..."
"$PY" -m venv .venv || { echo "Failed to create virtual environment"; read -r -p "Press Enter to exit..."; exit 1; }

echo "Installing dependencies (about 1-2 GB, keep the network on)..."
.venv/bin/python -m pip install --upgrade pip -q
.venv/bin/python -m pip install -r requirements.txt || {
  echo "PyPI is slow or blocked, retrying with a mirror..."
  .venv/bin/python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple || {
    echo "Dependency installation failed. Check the network and retry."
    read -r -p "Press Enter to exit..."
    exit 1
  }
}

echo "Done. Double-click start.command next time."
read -r -p "Press Enter to exit..."
