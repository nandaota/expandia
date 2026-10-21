#!/bin/bash
set -e
cd "$(dirname "$0")"
for candidate in python3.12 python3.11 python3.10 python3.9 python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(0 if (3,9)<=sys.version_info[:2]<=(3,12) else 1)' >/dev/null 2>&1; then
    "$candidate" iniciar.py
    exit $?
  fi
done
echo "Não foi encontrado Python 3.9 a 3.12. Peça ao Codex para instalar Python 3.12 do site oficial e executar iniciar.py."
exit 1
