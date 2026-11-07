"""Agent Client Protocol (ACP) Client for Google Antigravity.

Implements JSON-RPC 2.0 communication over stdio according to the Agent Client Protocol standard:
  * Handshake:    method 'initialize' -> protocolVersion 1, capability discovery
  * Session:      method 'session/new' -> sessionId, workspace binding
  * Prompt:       method 'session/prompt' -> session/update notifications, stopReason
  * Lifecycle:    Process supervision, graceful shutdown, health states
"""
from __future__ import annotations

import json
import logging
import subprocess
import threading
from enum import Enum
from pathlib import Path
from typing import Any

from app.integrations.antigravity.config import AntigravityConfig, get_antigravity_config

logger = logging.getLogger("scenesteward.antigravity.acp_client")


class ACPState(str, Enum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    CONFIGURED = "CONFIGURED"
    STARTING = "STARTING"
    INITIALIZING = "INITIALIZING"
    CONNECTED = "CONNECTED"
    READY = "READY"
    BUSY = "BUSY"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


class AntigravityACPClient:
    """Manages the official Google Antigravity ACP subprocess and JSON-RPC lifecycle."""

    def __init__(self, config: AntigravityConfig | None = None) -> None:
        self.config = config or get_antigravity_config()
        self._state = ACPState.CONFIGURED if self.config.enabled else ACPState.NOT_CONFIGURED
        self._proc: subprocess.Popen | None = None
        self._req_counter = 0
        self._lock = threading.Lock()
        self._pending_requests: dict[int, dict[str, Any]] = {}
        self._active_session_id: str | None = None
        self._session_cwd: str | None = None
        self._active_prompt_chunks: list[str] = []
        self._agent_info: dict[str, Any] = {}
        self._agent_capabilities: dict[str, Any] = {}
        self._auth_methods: list[dict[str, Any]] = []
        self._authenticated = False
        self._auth_result: dict[str, Any] = {}
        self._last_error: str | None = None
        self._stdout_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None

    @property
    def state(self) -> ACPState:
        return self._state

    @property
    def session_id(self) -> str | None:
        return self._active_session_id

    @property
    def agent_info(self) -> dict[str, Any]:
        return self._agent_info

    @property
    def auth_methods(self) -> list[dict[str, Any]]:
        return list(self._auth_methods)

    @property
    def authenticated(self) -> bool:
        return self._authenticated

    @property
    def auth_result(self) -> dict[str, Any]:
        return dict(self._auth_result)

    def start(self) -> bool:
        """Launches the ACP binary and performs the 'initialize' handshake."""
        if not self.config.enabled:
            self._state = ACPState.NOT_CONFIGURED
            return False

        exe = Path(self.config.executable_path)
        if not exe.exists():
            self._last_error = f"Antigravity executable not found at: {exe}"
            logger.error(self._last_error)
            self._state = ACPState.ERROR
            return False

        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                logger.info("Antigravity ACP process is already running")
                return True

            self._state = ACPState.STARTING
            logger.info("Spawning Antigravity ACP binary: %s", exe)
            try:
                self._proc = subprocess.Popen(
                    [str(exe)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )
            except Exception as e:
                self._last_error = f"Failed to spawn ACP binary: {e}"
                logger.exception(self._last_error)
                self._state = ACPState.ERROR
                return False

            self._stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
            self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
            self._stdout_thread.start()
            self._stderr_thread.start()

        self._state = ACPState.INITIALIZING
        init_req = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": 1,
                "clientCapabilities": {
                    "fs": {"readTextFile": True, "writeTextFile": False},
                    "terminal": False,
                },
                "clientInfo": {
                    "name": "scenesteward-switch-bridge",
                    "title": "SceneSteward Switch Collaboration Bridge",
                    "version": "1.0.0",
                },
            },
        }

        try:
            resp = self._send_request(init_req, timeout=self.config.startup_timeout_seconds)
            res = resp.get("result", {})
            self._agent_info = res.get("agentInfo", {})
            self._agent_capabilities = res.get("agentCapabilities", {})
            self._auth_methods = list(res.get("authMethods") or [])
            self._authenticated = False
            self._auth_result = {}
            self._state = ACPState.CONNECTED
            logger.info(
                "Antigravity ACP initialized: %s v%s (protocolVersion=%s)",
                self._agent_info.get("name"),
                self._agent_info.get("version"),
                res.get("protocolVersion"),
            )
            return True
        except Exception as e:  # noqa: BLE001
            self._last_error = f"ACP initialize failed: {e}"
            logger.error(self._last_error)
            self._state = ACPState.ERROR
            self.stop()
            return False

    def authenticate(self, method_id: str | None = None,
                     timeout: float | None = None) -> dict[str, Any]:
        """Official ACP authentication step.

        Must run after 'initialize' and before 'session/new'. The ACP binary owns
        the Google OAuth flow: when a refresh token is present it refreshes the
        access token silently; when it is not, it starts an interactive login that
        cannot complete inside a headless subprocess. That case is surfaced as an
        explicit "requires interactive sign-in" error instead of hanging.
        """
        if self._authenticated:
            return dict(self._auth_result)

        if self._state not in (ACPState.CONNECTED, ACPState.READY, ACPState.BUSY) and not self.start():
            raise RuntimeError(f"Cannot authenticate in state {self._state}: {self._last_error}")

        chosen = method_id or self.config.auth_method
        available = [str(m.get("id") or m.get("methodId")) for m in self._auth_methods]
        if available and chosen not in available:
            raise RuntimeError(
                f"ACP auth method '{chosen}' is not offered by the agent (available: {available})"
            )

        req = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "authenticate",
            "params": {"methodId": chosen},
        }
        try:
            resp = self._send_request(req, timeout=timeout or self.config.auth_timeout_seconds)
        except TimeoutError as exc:
            self._last_error = (
                "Antigravity authentication timed out; the Google sign-in is interactive. "
                "Run the ACP binary with an interactive terminal to complete login once."
            )
            logger.error(self._last_error)
            self._state = ACPState.ERROR
            raise RuntimeError(self._last_error) from exc
        except Exception as exc:
            self._last_error = f"ACP authenticate failed: {exc}"
            logger.error(self._last_error)
            self._state = ACPState.ERROR
            raise

        self._auth_result = dict(resp.get("result") or {})
        self._authenticated = True
        if self._state != ACPState.BUSY:
            self._state = ACPState.READY if self._active_session_id else ACPState.CONNECTED
        tier = (self._auth_result.get("_meta") or {}).get("tier") or self._auth_result.get("tier")
        logger.info("Antigravity authentication succeeded via '%s' (tier=%s)", chosen, tier)
        return dict(self._auth_result)

    def create_session(self, cwd: str | None = None) -> str:
        """Establishes an active ACP session using 'session/new'."""
        if self._state not in (ACPState.CONNECTED, ACPState.READY) and not self.start():
            raise RuntimeError(f"Cannot create session in state {self._state}: {self._last_error}")

        # session/new is only valid after a successful authenticate call.
        if not self._authenticated:
            self.authenticate()

        workspace_dir = cwd or self.config.workspace_root or str(Path.cwd())
        req = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "session/new",
            "params": {
                "cwd": workspace_dir,
                "mcpServers": [],
            },
        }

        try:
            resp = self._send_request(req, timeout=self.config.startup_timeout_seconds)
            sess_id = resp.get("result", {}).get("sessionId")
            if not sess_id:
                raise RuntimeError(f"No sessionId in ACP response: {resp}")
            self._active_session_id = sess_id
            self._session_cwd = workspace_dir
            self._state = ACPState.READY
            logger.info("Antigravity ACP session established: %s", sess_id)
            return sess_id
        except Exception as e:
            self._last_error = f"ACP session/new failed: {e}"
            logger.error(self._last_error)
            self._state = ACPState.ERROR
            raise

    def prompt(self, prompt_text: str, timeout: float | None = None) -> str:
        """Sends a user prompt to the active session and waits for completion."""
        if self._active_session_id is None:
            self.create_session()

        effective_timeout = timeout or self.config.request_timeout_seconds
        req_id = self._next_id()
        req = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "session/prompt",
            "params": {
                "sessionId": self._active_session_id,
                "prompt": [
                    {
                        "type": "text",
                        "text": prompt_text,
                    }
                ],
            },
        }

        with self._lock:
            self._active_prompt_chunks = []
            self._state = ACPState.BUSY

        try:
            resp = self._send_request(req, timeout=effective_timeout)
            with self._lock:
                full_text = "".join(self._active_prompt_chunks).strip()
                self._state = ACPState.READY
            if not full_text:
                full_text = str(resp.get("result", {}).get("stopReason", "end_turn"))
            return full_text
        except Exception as e:
            self._last_error = f"ACP session/prompt failed: {e}"
            logger.error(self._last_error)
            self._state = ACPState.READY
            raise

    def stop(self) -> None:
        """Terminates the ACP child process and closes streams."""
        with self._lock:
            proc = self._proc
            self._proc = None
            self._active_session_id = None
            self._session_cwd = None
            self._authenticated = False
            self._auth_result = {}
            self._state = ACPState.DISCONNECTED

        if proc is not None:
            logger.info("Shutting down Antigravity ACP process...")
            try:
                proc.terminate()
                proc.wait(timeout=2.0)
            except Exception:  # noqa: BLE001
                try:
                    proc.kill()
                except Exception:  # noqa: BLE001, S110
                    pass

    def _next_id(self) -> int:
        with self._lock:
            self._req_counter += 1
            return self._req_counter

    def _send_request(self, req: dict[str, Any], timeout: float) -> dict[str, Any]:
        req_id = req["id"]
        ev = threading.Event()
        entry = {"event": ev, "response": None}
        with self._lock:
            self._pending_requests[req_id] = entry

        raw = json.dumps(req) + "\n"
        try:
            if not self._proc or not self._proc.stdin:
                raise RuntimeError("ACP process is not running or stdin is closed")
            self._proc.stdin.write(raw)
            self._proc.stdin.flush()
        except Exception as e:
            with self._lock:
                self._pending_requests.pop(req_id, None)
            raise RuntimeError(f"Failed to write to ACP stdin: {e}") from e

        if not ev.wait(timeout=timeout):
            with self._lock:
                self._pending_requests.pop(req_id, None)
            raise TimeoutError(f"ACP request {req_id} timed out after {timeout:.1f}s")

        res = entry.get("response") or {}
        if "error" in res:
            err = res["error"]
            raise RuntimeError(f"ACP RPC Error ({err.get('code')}): {err.get('message')}")
        return res

    def _read_stdout(self) -> None:
        proc = self._proc
        if not proc or not proc.stdout:
            return

        for line in iter(proc.stdout.readline, ""):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                msg = json.loads(line_str)
            except json.JSONDecodeError:
                continue

            req_id = msg.get("id")
            method = msg.get("method")

            # Agent -> client request (not a response): must be answered or the
            # agent blocks waiting for us.
            if method and req_id is not None and "result" not in msg and "error" not in msg:
                self._handle_agent_request(msg)
                continue

            # Request response matching
            if req_id is not None and req_id in self._pending_requests:
                with self._lock:
                    entry = self._pending_requests.pop(req_id, None)
                if entry:
                    entry["response"] = msg
                    entry["event"].set()
                continue

            # Notification stream handling
            if method == "session/update":
                update = msg.get("params", {}).get("update", {})
                update_type = update.get("sessionUpdate")
                if update_type == "agent_message_chunk":
                    chunk_text = update.get("content", {}).get("text", "")
                    with self._lock:
                        self._active_prompt_chunks.append(chunk_text)

    def _write_json(self, payload: dict[str, Any]) -> None:
        proc = self._proc
        if proc is None or proc.stdin is None:
            return
        try:
            proc.stdin.write(json.dumps(payload) + "\n")
            proc.stdin.flush()
        except Exception:
            logger.debug("failed writing to ACP stdin", exc_info=True)

    def _handle_agent_request(self, msg: dict[str, Any]) -> None:
        """Answer ACP requests the agent makes of its client.

        The assessor is read-only by policy: file reads are confined to the
        session workspace and tool/permission requests are declined unless an
        operator explicitly enables auto-approval.
        """
        req_id = msg.get("id")
        method = msg.get("method")
        params = msg.get("params") or {}
        try:
            if method == "session/request_permission":
                result = self._permission_response(params)
            elif method == "fs/read_text_file":
                result = {"content": self._read_workspace_file(params)}
            elif method == "fs/write_text_file":
                raise RuntimeError("write access is not granted to the Antigravity assessor")
            else:
                raise RuntimeError(f"unsupported client method: {method}")
        except Exception as exc:  # noqa: BLE001
            self._write_json({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": str(exc)},
            })
            return

        self._write_json({"jsonrpc": "2.0", "id": req_id, "result": result})

    def _permission_response(self, params: dict[str, Any]) -> dict[str, Any]:
        options = params.get("options") or []
        desired = {"allow_once", "allow_always"} if self.config.auto_approve_tools else {"reject_once", "reject_always"}
        for option in options:
            if str(option.get("kind")) in desired:
                return {"outcome": {"outcome": "selected", "optionId": option.get("optionId")}}
        return {"outcome": {"outcome": "cancelled"}}

    def _read_workspace_file(self, params: dict[str, Any]) -> str:
        raw_path = params.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            raise RuntimeError("fs/read_text_file requires a path")
        root = Path(self._session_cwd or self.config.workspace_root or Path.cwd()).resolve()
        target = Path(raw_path)
        if not target.is_absolute():
            target = root / target
        target = target.resolve()
        if root != target and root not in target.parents:
            raise RuntimeError(f"path is outside the session workspace: {target}")
        text = target.read_text(encoding="utf-8", errors="replace")
        line = params.get("line")
        limit = params.get("limit")
        if isinstance(line, int) or isinstance(limit, int):
            lines = text.splitlines(keepends=True)
            start = max((line or 1) - 1, 0)
            end = start + limit if isinstance(limit, int) else len(lines)
            text = "".join(lines[start:end])
        return text

    def _read_stderr(self) -> None:
        proc = self._proc
        if not proc or not proc.stderr:
            return

        for line in iter(proc.stderr.readline, ""):
            l = line.strip()
            if not l:
                continue
            # Redact common tokens or sensitive substrings if any
            if "token" in l.lower() and "=" in l:
                l = "[REDACTED CREDENTIAL LINE]"
            if "error" in l.lower() or "exception" in l.lower():
                logger.warning("[Antigravity STDERR] %s", l[:160])
            elif "starting" in l.lower() or "onboard" in l.lower():
                logger.info("[Antigravity STDERR] %s", l[:160])

