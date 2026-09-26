"""Run every validation check and record what it found (`V4`).

    python tools/record_validation.py

The comparisons against astropy cannot run in a packaged build, because astropy
is a development dependency and is not shipped. So they are run here, with
astropy installed, and the numbers are written to ``cosmos/data/validation.json``
for the app to show. ``tests/test_validation.py`` compares the file with a fresh
run on every change, so what ships cannot quietly go stale.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cosmos import validation  # noqa: E402


def main() -> int:
    if not validation.astropy_available():
        print("astropy is not installed; install the development requirements first.")
        return 1

    results = validation.run_all()
    width = max(len(r.check.id) for r in results)
    failed = 0
    for result in results:
        check = result.check
        verdict = "ok" if result.passed else "FAILED"
        if not result.passed:
            failed += 1
        print(f"{check.id:{width}}  {check.format(result.worst):>14}  "
              f"of {check.format(check.tolerance):>12}  {result.headroom:6.1%}  {verdict}")

    record = validation.write_record()
    print(f"\n{len(results)} checks, {failed} failing; recorded {validation.RECORD} "
          f"as measured {record['measured']}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
