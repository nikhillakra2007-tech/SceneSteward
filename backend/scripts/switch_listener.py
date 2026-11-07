"""Hold the Switch agent SSE connection and record validated inbound events.

Usage:  python scripts/switch_listener.py [--connection-id UUID] [--max-retries N]

Requires SWITCH_ADAPTER=http, SWITCH_BASE_URL, SWITCH_AGENT_ID, SWITCH_API_KEY.
Every event is validated, deduplicated and correlated to a project; nothing here
can modify consent records — by design and by test.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.integrations.switch.listener import SwitchEventListener


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--connection-id", default=None)
    parser.add_argument("--max-retries", type=int, default=None)
    parser.add_argument("--mode", choices=["poll", "sse"], default="poll",
                        help="poll = contract-stable long-poll (default); sse = compatibility stream")
    args = parser.parse_args()

    s = get_settings()
    if s.switch_adapter != "http":
        print("SWITCH_ADAPTER is not 'http'; refusing to start a live listener.", file=sys.stderr)
        return 2

    listener = SwitchEventListener(get_session_factory,
                                   connection_id=args.connection_id,
                                   max_retries=args.max_retries)
    print(f"Switch listener starting mode={args.mode}; connection_id={listener.connection_id}", flush=True)
    if args.mode == "sse":
        listener.run_forever()
    else:
        listener.run_poll_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
