#!/usr/bin/env bash
# Pass the Python executable belonging to the environment where devplat is installed.
set -euo pipefail
cli_python="${1:-python3}"
"$cli_python" -m pip install --upgrade \
  'git+https://github.com/eseidinger/developer-platform.git@a69ebbc7af6f728bc0fdc0c16c8dd0dcf2a47ce2#subdirectory=platform/cli'
"$cli_python" -c 'from importlib.metadata import version; assert version("developer-platform-cli") == "0.3.0"; print("devplat 0.3.0 installed")'
