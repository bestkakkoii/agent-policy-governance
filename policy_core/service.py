"""Optional authenticated loopback RPC; embedded operation remains the default."""
from __future__ import annotations

import http.server
import secrets
import socket
import threading
from pathlib import Path
from typing import Any

from .common import canonical, decode_json, policy_error, require, write_json
from .runtime import policy_runtime


def dispatch(runtime: policy_runtime, request: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(request, dict), "request_shape", "RPC must be an object")
    operation = request.get("op")
    project = Path(request.get("project", "."))
    if operation == "context":
        return runtime.context(project, request["session"], request.get("task", ""),
                               fresh=request.get("fresh", False), begin=request.get("begin", False), full=request.get("full", False))
    if operation == "finish":
        return runtime.finish(project, request["session"])
    if operation == "gate":
        return runtime.gate(project, request["tool"], request.get("arguments", {}))
    if operation == "explain":
        return runtime.explain(request["rule_ids"], request.get("snapshot_id"))
    if operation == "hook":
        return runtime.hook(request["adapter"], request["event"])
    if operation == "health":
        return {"ok": True, "protocol": "apg_local_rpc.v1", "network_scope": "loopback_only"}
    raise policy_error("operation_unknown", "RPC operation is not available", operation=operation)


class local_server(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, runtime: policy_runtime, port: int = 0) -> None:
        self.runtime = runtime
        self.token = secrets.token_urlsafe(32)
        self.slots = threading.BoundedSemaphore(8)
        # Loopback-only transport is local IPC, not an Internet protocol selection.
        super().__init__(("127.0.0.1", port), local_handler)


class local_handler(http.server.BaseHTTPRequestHandler):
    server: local_server
    protocol_version = "HTTP/1.1"
    timeout = 5

    def log_message(self, format: str, *args: Any) -> None:
        # Never log raw prompts or bearer credentials. Structured faults are returned to the caller.
        return

    def send_record(self, status: int, record: dict[str, Any]) -> None:
        body = canonical(record)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def do_POST(self) -> None:
        if self.path != "/rpc":
            self.send_record(404, {"ok": False, "error": "not_found"})
            return
        expected_host = f"127.0.0.1:{self.server.server_address[1]}"
        if self.headers.get("Origin") is not None or self.headers.get("Host") != expected_host:
            self.send_record(403, {"ok": False, "error": "origin_or_host_rejected"})
            return
        authorization = self.headers.get("Authorization", "")
        if not secrets.compare_digest(authorization, "Bearer " + self.server.token):
            self.send_record(401, {"ok": False, "error": "authentication_required"})
            return
        if not self.server.slots.acquire(blocking=False):
            self.send_record(429, {"ok": False, "error": "concurrency_limit"})
            return
        try:
            require(self.headers.get_content_type() == "application/json", "content_type", "Expected application/json")
            require(self.headers.get("Transfer-Encoding") is None, "transfer_encoding", "Chunked local requests are not accepted")
            length = int(self.headers.get("Content-Length", "-1"))
            require(0 <= length <= 262144, "body_limit", "RPC body must be bounded")
            self.connection.settimeout(5)
            raw = self.rfile.read(length)
            require(len(raw) == length, "incomplete_body", "RPC request ended before Content-Length")
            result = dispatch(self.server.runtime, decode_json(raw))
            self.send_record(200, result)
        except (policy_error, ValueError, KeyError, TypeError, OSError) as error:
            record = error.record() if isinstance(error, policy_error) else {"ok": False, "error": type(error).__name__, "message": str(error)}
            self.send_record(400, record)
        finally:
            self.server.slots.release()

    def do_GET(self) -> None:
        self.send_record(405, {"ok": False, "error": "post_required"})


def serve(runtime: policy_runtime, port: int = 0) -> None:
    require(0 <= port <= 65535, "port_range", "Invalid TCP port")
    with local_server(runtime, port) as server:
        endpoint = {"url": f"http://127.0.0.1:{server.server_address[1]}/rpc", "token": server.token,
                    "protocol": "apg_local_rpc.v1", "pid": __import__("os").getpid()}
        target = runtime.store.home / "service_endpoint.json"
        require(not target.exists(), "service_receipt_exists", "Another service or stale endpoint receipt exists; verify its PID before replacing it")
        write_json(target, endpoint, private=True)
        print(canonical({"ok": True, "url": endpoint["url"], "credentials": str(target)}).decode(), flush=True)
        try:
            server.serve_forever(poll_interval=0.25)
        finally:
            target.unlink(missing_ok=True)


def execute_hybrid(runtime: policy_runtime, request: dict[str, Any]) -> dict[str, Any]:
    """Reuse an explicitly running local service; otherwise execute the identical core.

    Never auto-start a resident process. A failed service is reported and audited;
    context retries force a restoration because delivery may have been ambiguous.
    """
    import urllib.parse
    import urllib.request
    from .common import read_json
    endpoint_path = runtime.store.home / "service_endpoint.json"
    if not endpoint_path.exists():
        return dispatch(runtime, request)
    try:
        endpoint = read_json(endpoint_path)
        parsed = urllib.parse.urlsplit(endpoint["url"])
        require(parsed.scheme == "http" and parsed.hostname == "127.0.0.1" and parsed.port is not None
                and parsed.path == "/rpc" and not parsed.username and not parsed.query and not parsed.fragment,
                "unsafe_local_endpoint", "Local RPC receipt must refer only to numeric loopback /rpc")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        payload = urllib.request.Request(endpoint["url"], data=canonical(request), method="POST",
                                         headers={"Content-Type": "application/json", "Authorization": "Bearer " + endpoint["token"]})
        with opener.open(payload, timeout=5) as response:
            body = response.read(2 * 1024 * 1024 + 1)
        require(len(body) <= 2 * 1024 * 1024, "local_response_size", "Local RPC response exceeds limit")
        value = decode_json(body)
        require(isinstance(value, dict), "local_response_shape", "Local RPC response is not an object")
        return value
    except (OSError, ValueError, KeyError, TypeError, policy_error) as error:
        # Mutation-bearing authority operations are never exposed through this RPC.
        with runtime.store.transaction() as connection:
            runtime.store.audit(connection, "local_service_fallback", {"error_type": type(error).__name__, "reason": str(error)})
        print(canonical({"stage": "local_service", "recovered": "embedded", "reason": str(error)}).decode(), file=__import__("sys").stderr)
        request = dict(request)
        if request.get("op") == "context":
            request["fresh"] = True
        if request.get("op") == "hook":
            # Native SessionStart restoration is safe; PreToolUse still gets the gate.
            event = request.get("event", {})
            if event.get("hook_event_name") in {"SessionStart", "UserPromptSubmit"}:
                return runtime.hook(request["adapter"], {**event, "_apg_restore": True})
        return dispatch(runtime, request)
