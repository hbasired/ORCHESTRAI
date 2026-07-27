#!/usr/bin/env python3
"""scripts/load-context.py — emit the project context bundle.

Thin wrapper around .claude/hooks/lib/context_loader.py so that humans and
agents can run this without the hook plumbing being registered.

Usage:
  python scripts/load-context.py --mode=session-start
  python scripts/load-context.py --mode=task-start --stage=02
  python scripts/load-context.py --mode=task-close --stage=02
"""
from __future__ import annotations

import sys
from pathlib import Path

HOOK_LIB = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "lib"
sys.path.insert(0, str(HOOK_LIB))

from context_loader import main as _main  # noqa: E402

if __name__ == "__main__":
    sys.exit(_main())
