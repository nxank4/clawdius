from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class OpenClawResult:
    stdout: str
    stderr: str
    returncode: int


class OpenClawCLI:
    """Thin wrapper around the `openclaw` Node.js CLI.

    Args:
        executable: CLI binary name/path (default: "openclaw").
        cwd: Working directory for subprocess calls (default: current process cwd).
        env: Extra environment variables merged over current process env.
        timeout_s: Subprocess timeout in seconds.
    """

    def __init__(
        self,
        *,
        executable: str = "openclaw",
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        timeout_s: float = 120.0,
    ) -> None:
        self._executable = executable
        self._cwd = cwd
        self._env = dict(env) if env is not None else {}
        self._timeout_s = timeout_s

    def send_message(self, to: str, text: str) -> OpenClawResult:
        """Send a message via OpenClaw.

        Executes: `openclaw message send --to <to> --message <text>`
        """
        return self._run(
            [
                self._executable,
                "message",
                "send",
                "--to",
                to,
                "--message",
                text,
            ]
        )

    def run_agent(self, task: str) -> OpenClawResult:
        """Run the OpenClaw agent with a single task prompt.

        Executes: `openclaw agent --message <task>`
        """
        return self._run([self._executable, "agent", "--message", task])

    def _run(self, argv: Sequence[str]) -> OpenClawResult:
        merged_env = os.environ.copy()
        merged_env.update(self._env)

        proc = subprocess.run(
            list(argv),
            cwd=self._cwd,
            env=merged_env,
            capture_output=True,
            text=True,
            timeout=self._timeout_s,
            check=False,
        )

        result = OpenClawResult(
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            returncode=proc.returncode,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"openclaw command failed (exit={proc.returncode}): {' '.join(argv)}\n"
                f"stderr:\n{result.stderr}"
            )
        return result
