"""Cross-platform subprocess utilities."""

import asyncio
import shutil
import sys
from pathlib import Path
from typing import Sequence


# Sandbox directory for running CLI tools in isolation
SANDBOX_DIR = Path.home() / ".cli-openai-bridge" / "sandbox"


def get_sandbox_dir() -> Path:
    """Get or create sandbox directory for CLI tool execution."""
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    return SANDBOX_DIR


def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform == "win32"


def needs_shell(cmd_path: str) -> bool:
    """Check if command needs shell execution (Windows .cmd/.bat files)."""
    if not is_windows():
        return False
    lower_path = cmd_path.lower()
    return lower_path.endswith(".cmd") or lower_path.endswith(".bat")


def resolve_command(cmd: str) -> str:
    """Resolve command to full path if possible."""
    return shutil.which(cmd) or cmd


async def create_subprocess(
    cmd: Sequence[str],
    use_sandbox: bool = True,
    **kwargs,
) -> asyncio.subprocess.Process:
    """
    Create subprocess with cross-platform compatibility.

    On Windows, .cmd/.bat files are executed through shell.

    Args:
        cmd: Command and arguments as sequence
        use_sandbox: Run in sandbox directory to isolate from codebase (default True)
        **kwargs: Additional args for create_subprocess_exec/shell

    Returns:
        Process object
    """
    cmd_list = list(cmd)
    executable = cmd_list[0]

    # Resolve to full path to check extension
    resolved = resolve_command(executable)

    # Set working directory to sandbox if not specified and sandbox is enabled
    if use_sandbox and "cwd" not in kwargs:
        kwargs["cwd"] = str(get_sandbox_dir())

    if needs_shell(resolved):
        # On Windows, run .cmd/.bat through shell
        # Join command for shell execution
        shell_cmd = " ".join(f'"{arg}"' if " " in arg else arg for arg in cmd_list)
        return await asyncio.create_subprocess_shell(
            shell_cmd,
            **kwargs,
        )
    else:
        return await asyncio.create_subprocess_exec(
            *cmd_list,
            **kwargs,
        )
