#!/bin/zsh
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  echo 'Run setup first: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt'
  read '?Press Enter to close.'
  exit 1
fi
exec .venv/bin/python -m photoclassifier
