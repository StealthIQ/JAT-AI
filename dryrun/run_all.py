"""
Run all dry run tests.
Usage: python -m dryrun.run_all
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dryrun.test_full_workflow import main as workflow_main
from dryrun.test_auto_mode import main as auto_main
from dryrun.test_jdocs import main as jdocs_main


async def run_all():
    print()
    await workflow_main()
    print()
    await auto_main()
    print()
    await jdocs_main()
    print()
    print("*" * 50)
    print("ALL DRY RUN SUITES PASSED")
    print("*" * 50)


if __name__ == "__main__":
    asyncio.run(run_all())
