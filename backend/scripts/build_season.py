#!/usr/bin/env python3
"""
Tiny orchestration runner:
1) build weekly payouts
2) export season json
"""

import subprocess
import sys

SCRIPTS = [
    "backend/scripts/build_weekly_payouts.py",
    "backend/scripts/export_season_json.py",
]

def run(cmd: list[str]) -> None:
    print(f"\n==> {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

def main() -> int:
    py = sys.executable  # uses the same python you ran this with
    for script in SCRIPTS:
        run([py, script])
    print("\n✅ Done: payouts rebuilt + season JSON exported")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())