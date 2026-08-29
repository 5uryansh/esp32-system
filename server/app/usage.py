"""Claude Code quota: runs `claude -p "/usage"` and parses its output."""

import asyncio
import logging
import re
import time

from . import config
from .models import Usage

logger = logging.getLogger(__name__)


class UsageUnavailable(Exception):
    """Raised when the Claude CLI cannot be run or its output cannot be parsed."""


# The CLI prints human prose, e.g.
#   Current session: 15% used · resets Aug 29, 8:40am (UTC)
#   Current week (all models): 27% used · resets Aug 29, 7pm (UTC)
SESSION_RE = re.compile(
    r"Current session:\s*(\d+)%\s*used\s*[·.-]\s*resets\s*(.+)", re.IGNORECASE
)
WEEK_RE = re.compile(
    r"Current week \(all models\):\s*(\d+)%\s*used\s*[·.-]\s*resets\s*(.+)",
    re.IGNORECASE,
)
# Last good reading, kept so a slow or failed poll never blocks the ESP32.
_cached: Usage | None = None
_cached_at: float = 0.0
_lock = asyncio.Lock()


async def _run_cli() -> str:
    """Run the Claude CLI in print mode and return its stdout."""
    argv = [config.CLAUDE_BIN, "-p", "/usage"]
    if config.CLAUDE_USAGE_MODEL:
        argv += ["--model", config.CLAUDE_USAGE_MODEL]

    try:
        process = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as exc:
        logger.error("Could not start %s: %s", config.CLAUDE_BIN, exc)
        raise UsageUnavailable("claude CLI not runnable") from exc

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=config.CLAUDE_USAGE_TIMEOUT
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        logger.error("claude -p /usage timed out after %ss", config.CLAUDE_USAGE_TIMEOUT)
        raise UsageUnavailable("claude CLI timed out") from None

    if process.returncode != 0:
        logger.error(
            "claude -p /usage exited %s: %s",
            process.returncode,
            stderr.decode(errors="replace")[:500],
        )
        raise UsageUnavailable("claude CLI returned an error")

    return stdout.decode(errors="replace")


def parse(output: str) -> Usage:
    """Turn the CLI's prose output into our compact payload."""
    session = SESSION_RE.search(output)
    week = WEEK_RE.search(output)
    if not session or not week:
        logger.error("Unexpected /usage output: %s", output[:500])
        raise UsageUnavailable("could not parse claude CLI output")

    return Usage(
        session_pct=int(session.group(1)),
        session_reset=session.group(2).strip(),
        week_pct=int(week.group(1)),
        week_reset=week.group(2).strip(),
    )


async def get_usage() -> Usage:
    """Return a recent usage reading, refreshing via the CLI when it goes stale.

    Each refresh starts a real Claude Code session, so it is slow and counts
    against the very quota being reported. Readings are therefore reused for
    CLAUDE_USAGE_TTL seconds, and a failed refresh falls back to the last good
    value rather than failing the request.
    """
    global _cached, _cached_at

    async with _lock:
        age = time.monotonic() - _cached_at
        if _cached is None or age >= config.CLAUDE_USAGE_TTL:
            try:
                _cached = parse(await _run_cli())
                _cached_at = time.monotonic()
            except UsageUnavailable:
                if _cached is None:
                    raise
                logger.warning("Usage refresh failed; serving reading from %.0fs ago", age)

        return _cached
