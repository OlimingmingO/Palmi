"""PKE Service — subprocess-based integration with Personal Knowledge Engine.

PKE is a Node.js CLI. We invoke it as a subprocess with PKE_VAULT pointing
to the per-elder vault directory. This isolates each elder's memory completely.

Key design:
- query(): 1s fail-open timeout (never block dialogue)
- capture(): Async via Celery (non-blocking)
- compile(): Daily cron (batch process all active elders)
- init_vault(): Called on elder registration
"""
import os
import subprocess
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


def _pke_env(vault_path: str) -> dict:
    """Build environment variables for PKE subprocess."""
    env = os.environ.copy()
    env["PKE_VAULT"] = vault_path
    # Ensure pke binary is on PATH (inside Docker: /opt/pke/bin)
    pke_bin = "/opt/pke/bin"
    if pke_bin not in env.get("PATH", ""):
        env["PATH"] = f"{pke_bin}:{env.get('PATH', '')}"
    return env


class PKEService:
    """Interface to Personal Knowledge Engine CLI."""

    def __init__(self, vault_root: Optional[str] = None):
        self.vault_root = vault_root or settings.PKE_VAULT_ROOT

    def vault_path(self, elder_id: str) -> str:
        """Get the filesystem path to an elder's vault."""
        return os.path.join(self.vault_root, elder_id)

    def init_vault(self, elder_id: str) -> None:
        """Create vault directory structure for a new elder.

        Called when a new elder is registered (first message).
        Creates raw/ and wiki/ directories and initializes PKE state.
        """
        vault = Path(self.vault_path(elder_id))
        (vault / "raw").mkdir(parents=True, exist_ok=True)
        (vault / "wiki").mkdir(parents=True, exist_ok=True)

        try:
            subprocess.run(
                ["pke", "changed", "--save"],
                env=_pke_env(str(vault)),
                capture_output=True,
                text=True,
                timeout=15,
            )
            logger.info("Initialized PKE vault for elder %s", elder_id)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            # Non-fatal: vault dirs exist, pke init can happen later
            logger.warning("PKE init skipped for %s: %s", elder_id, e)

    async def query(self, elder_id: str, query_text: str) -> str:
        """Semantic search in an elder's knowledge vault.

        Fail-open: returns empty string on timeout/error.
        1s outer timeout ensures dialogue is never blocked.
        """
        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, self._run_use, elder_id, query_text),
                timeout=1.0,  # 1s outer timeout (subprocess has its own)
            )
            return result or ""
        except asyncio.TimeoutError:
            logger.warning("PKE query timeout for elder %s", elder_id)
            return ""
        except Exception as e:
            logger.warning("PKE query error for elder %s: %s", elder_id, e)
            return ""

    def _run_use(self, elder_id: str, query_text: str) -> str:
        """Synchronous PKE use command (run in thread executor)."""
        vault = self.vault_path(elder_id)
        try:
            result = subprocess.run(
                ["pke", "use", query_text],
                env=_pke_env(vault),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.debug("PKE use returned %d: %s", result.returncode, result.stderr)
                return ""
        except subprocess.TimeoutExpired:
            return ""
        except FileNotFoundError:
            logger.warning("pke binary not found on PATH")
            return ""

    def capture(self, elder_id: str, user_msg: str, bot_reply: str) -> None:
        """Write a conversation turn to the elder's vault raw/ directory.

        Called asynchronously via Celery task after each exchange.
        """
        vault = self.vault_path(elder_id)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Write temp markdown file
        content = f"# 对话记录 {ts}\n\n**用户**: {user_msg}\n\n**小伴**: {bot_reply}\n"
        tmp_path = Path(f"/tmp/pke_capture_{elder_id}_{ts}.md")

        try:
            tmp_path.write_text(content, encoding="utf-8")
            result = subprocess.run(
                ["pke", "capture", str(tmp_path), "--write"],
                env=_pke_env(vault),
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode != 0:
                logger.warning("PKE capture failed for %s: %s", elder_id, result.stderr)
            else:
                logger.debug("PKE captured conversation for elder %s", elder_id)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning("PKE capture error for %s: %s", elder_id, e)
        finally:
            tmp_path.unlink(missing_ok=True)

    def compile_daily(self, elder_id: str) -> None:
        """Run daily knowledge compilation for an elder.

        Extracts durable signals from recent conversations and
        generates proposals for wiki updates.
        """
        vault = self.vault_path(elder_id)
        try:
            result = subprocess.run(
                ["pke", "daily"],
                env=_pke_env(vault),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                logger.info("PKE daily compile completed for elder %s", elder_id)
            else:
                logger.warning("PKE compile failed for %s: %s", elder_id, result.stderr)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning("PKE compile error for %s: %s", elder_id, e)


# Module-level singleton
pke_service = PKEService()
