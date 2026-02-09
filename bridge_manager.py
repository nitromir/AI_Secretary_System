#!/usr/bin/env python3
"""
Bridge Process Manager for CLI-OpenAI Bridge.

Manages the bridge as a subprocess — start, stop, health check.
The bridge wraps claude CLI into an OpenAI-compatible API on a local port.

In Docker mode (DOCKER_CONTAINER=1), the bridge runs on the host machine
and the orchestrator connects to it via host.docker.internal.

Usage:
    from bridge_manager import bridge_manager

    await bridge_manager.start(port=8787, permission_level="chat")
    status = bridge_manager.get_status()
    await bridge_manager.stop()
"""

import asyncio
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import httpx


logger = logging.getLogger(__name__)

# Base directory of the project
BASE_DIR = Path(__file__).parent

# Docker mode: can't spawn bridge subprocess, bridge runs on host
IS_DOCKER = os.environ.get("DOCKER_CONTAINER") == "1"


class BridgeProcessManager:
    """Manages the CLI-OpenAI Bridge process."""

    def __init__(self) -> None:
        self._process: Optional[subprocess.Popen] = None
        self._port: int = 8787
        self._started_at: Optional[float] = None
        self._log_file: Path = BASE_DIR / "logs" / "bridge.log"
        self._bridge_dir: Path = BASE_DIR / "services" / "bridge"
        self._permission_level: str = "chat"
        self._remote_running: bool = False

    @property
    def _bridge_host(self) -> str:
        """Bridge host: host.docker.internal in Docker, 127.0.0.1 locally."""
        if IS_DOCKER:
            return "host.docker.internal"
        return "127.0.0.1"

    @property
    def is_running(self) -> bool:
        """Check if bridge process is alive."""
        if IS_DOCKER:
            return self._remote_running
        if self._process is not None:
            return self._process.poll() is None
        return False

    @property
    def pid(self) -> Optional[int]:
        """Return PID of bridge process."""
        if not IS_DOCKER and self.is_running:
            return self._process.pid  # type: ignore[union-attr]
        return None

    async def start(
        self,
        port: int = 8787,
        permission_level: str = "chat",
    ) -> dict:
        """
        Start the bridge subprocess.

        In Docker mode, checks if bridge is already running on the host.

        Args:
            port: Port to run the bridge on.
            permission_level: Claude permission level (chat, readonly, edit, full).

        Returns:
            Dict with status, message, pid, url.
        """
        self._port = port
        self._permission_level = permission_level

        # Docker mode: bridge runs on host, just check if reachable
        if IS_DOCKER:
            return await self._start_docker_mode(port)

        return await self._start_local_mode(port, permission_level)

    async def _start_docker_mode(self, port: int) -> dict:
        """In Docker, check if bridge is reachable on host."""
        healthy = await self._wait_for_health(timeout=5)
        if healthy:
            self._remote_running = True
            self._started_at = time.time()
            logger.info(f"🌉 Bridge detected on host at {self.get_base_url()}")
            return {
                "status": "ok",
                "message": "Bridge detected on host",
                "url": self.get_base_url(),
            }

        self._remote_running = False
        return {
            "status": "error",
            "error": (
                f"Bridge not reachable at {self.get_base_url()}. "
                "In Docker mode, start the bridge on the host machine first:\n"
                f"  cd services/bridge && python -m uvicorn src.server.main:app "
                f"--host 0.0.0.0 --port {port}"
            ),
        }

    async def _start_local_mode(self, port: int, permission_level: str) -> dict:
        """Start bridge as a local subprocess."""
        if self.is_running:
            return {
                "status": "ok",
                "message": "Bridge already running",
                "pid": self.pid,
                "url": self.get_base_url(),
            }

        # Verify bridge directory exists
        if not self._bridge_dir.exists():
            return {
                "status": "error",
                "error": f"Bridge directory not found: {self._bridge_dir}",
            }

        # Write .env with current settings
        self._write_env(port, permission_level)

        # Ensure log directory exists
        self._log_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Build command — use same Python interpreter
            cmd = [
                sys.executable,
                "-m",
                "uvicorn",
                "src.server.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ]

            # Open log file
            log_fd = open(self._log_file, "a", encoding="utf-8")
            log_fd.write(f"\n{'=' * 60}\n")
            log_fd.write(f"Bridge starting at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_fd.write(f"Port: {port}, Permission: {permission_level}\n")
            log_fd.write(f"{'=' * 60}\n")
            log_fd.flush()

            # Set environment
            env = os.environ.copy()
            env["BRIDGE_HOST"] = "127.0.0.1"
            env["BRIDGE_PORT"] = str(port)
            env["CLAUDE_PERMISSION_LEVEL"] = permission_level
            env["PYTHONUNBUFFERED"] = "1"
            # Disable Gemini and GPT providers
            env["GEMINI_CLI_PATH"] = ""
            env["GPT_CLI_PATH"] = ""

            self._process = subprocess.Popen(
                cmd,
                cwd=str(self._bridge_dir),
                env=env,
                stdout=log_fd,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            self._started_at = time.time()

            logger.info(f"🌉 Bridge process started (PID: {self._process.pid}, port: {port})")

            # Wait for health check
            healthy = await self._wait_for_health(timeout=20)
            if not healthy:
                # Process may have crashed
                if self._process.poll() is not None:
                    return {
                        "status": "error",
                        "error": "Bridge process crashed on startup. Check logs/bridge.log",
                    }
                return {
                    "status": "error",
                    "error": f"Bridge not responding on port {port} after 20s",
                }

            logger.info(f"✅ Bridge is healthy on http://127.0.0.1:{port}")
            return {
                "status": "ok",
                "message": "Bridge started successfully",
                "pid": self._process.pid,
                "url": self.get_base_url(),
            }

        except FileNotFoundError:
            return {
                "status": "error",
                "error": "Python interpreter not found for bridge",
            }
        except Exception as e:
            logger.error(f"❌ Failed to start bridge: {e}")
            return {"status": "error", "error": str(e)}

    async def stop(self) -> dict:
        """Stop the bridge process gracefully."""
        if IS_DOCKER:
            self._remote_running = False
            self._started_at = None
            return {
                "status": "ok",
                "message": "Disconnected from host bridge (stop it on the host)",
            }

        if not self.is_running:
            self._process = None
            self._started_at = None
            return {"status": "ok", "message": "Bridge was not running"}

        pid = self._process.pid  # type: ignore[union-attr]
        logger.info(f"🛑 Stopping bridge (PID: {pid})...")

        try:
            # Send SIGTERM for graceful shutdown
            os.kill(pid, signal.SIGTERM)

            # Wait up to 5 seconds
            for _ in range(50):
                if self._process.poll() is not None:  # type: ignore[union-attr]
                    break
                await asyncio.sleep(0.1)
            else:
                # Force kill if still running
                logger.warning("⚠️ Bridge didn't stop gracefully, sending SIGKILL")
                os.kill(pid, signal.SIGKILL)
                self._process.wait(timeout=3)  # type: ignore[union-attr]

        except ProcessLookupError:
            pass  # Already dead
        except Exception as e:
            logger.error(f"Error stopping bridge: {e}")

        self._process = None
        self._started_at = None
        logger.info("🛑 Bridge stopped")
        return {"status": "ok", "message": "Bridge stopped"}

    def get_status(self) -> dict:
        """Return bridge process status."""
        running = self.is_running
        result = {
            "is_running": running,
            "port": self._port,
            "url": self.get_base_url() if running else None,
            "pid": self.pid,
            "permission_level": self._permission_level,
            "log_file": str(self._log_file),
            "docker_mode": IS_DOCKER,
        }
        if running and self._started_at:
            result["uptime_seconds"] = int(time.time() - self._started_at)
        return result

    def get_base_url(self) -> str:
        """Return the bridge base URL (OpenAI-compatible /v1 prefix)."""
        return f"http://{self._bridge_host}:{self._port}/v1"

    def _write_env(self, port: int, permission_level: str) -> None:
        """Write/update .env file for the bridge."""
        env_path = self._bridge_dir / ".env"
        env_content = (
            f"BRIDGE_HOST=127.0.0.1\n"
            f"BRIDGE_PORT={port}\n"
            f"BRIDGE_DEBUG=false\n"
            f"CLAUDE_PERMISSION_LEVEL={permission_level}\n"
            f"QUEUE_ENABLED=true\n"
            f"HEALTH_CHECK_ON_STARTUP=true\n"
            f"HIDE_UNAVAILABLE_MODELS=true\n"
            f"GEMINI_CLI_PATH=\n"
            f"GPT_CLI_PATH=\n"
        )
        env_path.write_text(env_content)

    async def _wait_for_health(self, timeout: int = 20) -> bool:
        """Wait for bridge /health endpoint to respond."""
        url = f"http://{self._bridge_host}:{self._port}/health"
        start = time.time()

        while time.time() - start < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, timeout=3.0)
                    if resp.status_code == 200:
                        return True
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout):
                pass
            except Exception:
                pass

            # Check if local process died
            if not IS_DOCKER and self._process and self._process.poll() is not None:
                return False

            await asyncio.sleep(0.5)

        return False


# Global singleton
bridge_manager = BridgeProcessManager()
