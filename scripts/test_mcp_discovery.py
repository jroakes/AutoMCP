#!/usr/bin/env python3
"""test_mcp_discovery.py
Quick end-to-end smoke-test for an AutoMCP FastMCP server.

The script:
  1. Opens the Server-Sent Events stream (`<base>/sse`) and captures the
     `session_id` endpoint the server emits on connect.
  2. Completes the required MCP initialization handshake.
  3. Sends `tools/list`, `resources/list`, and `prompts/list` requests.
  4. Prints the JSON-RPC results that come back on the SSE stream.

Usage
-----
Run the server (for example):
    python -m src.main serve --config config_files/ahrefs.json --port 9000

In another shell:
    python scripts/test_mcp_discovery.py http://localhost:9000/ahrefs/mcp

Dependencies
------------
Only the ubiquitous `requests` package is required. It is already in
`requirements.txt` for AutoMCP, but the script will tell you if it is
missing.
"""
from __future__ import annotations

import argparse
import json
import queue
import re
import sys
import threading
import time
from pathlib import Path
from types import TracebackType
from typing import Any, Dict, Optional, Type

try:
    import requests  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover – helpful error for CLI use
    print(
        "\nThis script needs the `requests` package. Install with:\n"
        "    pip install requests\n",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc

# ---------------------------------------------------------------------------
# Helper classes
# ---------------------------------------------------------------------------


class SseListener(threading.Thread):
    """Background thread that reads an SSE stream and pushes whole events to a queue."""

    def __init__(
        self, url: str, event_queue: "queue.Queue[str|None]", timeout: int = 60
    ) -> None:
        super().__init__(daemon=True, name="sse-listener")
        self._url = url
        self._queue = event_queue
        self._timeout = timeout
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    def run(self) -> None:  # noqa: D401 – simple worker method
        try:
            with requests.get(self._url, stream=True, timeout=self._timeout) as resp:
                resp.raise_for_status()
                buffer: list[str] = []
                for raw in resp.iter_lines(decode_unicode=True):
                    # Allow external request to stop reading (e.g., main thread done)
                    if self._stop_event.is_set():
                        break
                    if raw is None:
                        continue
                    line = raw.strip("\r\n")
                    if line == "":
                        if buffer:
                            self._queue.put("\n".join(buffer))
                            buffer.clear()
                        continue
                    buffer.append(line)
        except Exception as exc:  # pragma: no cover – just propagate to main thread
            self._queue.put(f"__ERROR__{exc}")
        finally:
            # Sentinel so the consumer knows we are done
            self._queue.put(None)

    # ------------------------------------------------------------------
    def stop(self) -> None:
        self._stop_event.set()


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def parse_endpoint_event(event: str) -> Optional[str]:
    """Return the `/messages/?session_id=...` path from an `endpoint` SSE event."""
    if not event.startswith("event: endpoint"):
        return None
    for line in event.split("\n"):
        if line.startswith("data: "):
            return line.removeprefix("data: ").strip()
    return None


def parse_json_event(event: str) -> Optional[Dict[str, Any]]:
    """Return JSON dict from a generic SSE event that contains a single `data:` line."""
    for line in event.split("\n"):
        if line.startswith("data: "):
            try:
                return json.loads(line.removeprefix("data: ").strip())
            except json.JSONDecodeError:
                return None
    return None


def post_json(url: str, payload: Dict[str, Any]) -> None:
    """Helper that sends JSON and checks for the FastMCP-expected 202 status."""
    resp = requests.post(url, json=payload, timeout=30)
    if resp.status_code != 202:
        raise RuntimeError(f"Unexpected HTTP status {resp.status_code}: {resp.text}")


# ---------------------------------------------------------------------------
# Public script entry-point
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> None:  # noqa: D401 – CLI entry
    parser = argparse.ArgumentParser(description="Quick MCP discovery smoke-test")
    parser.add_argument(
        "base",
        help="Base MCP path (e.g. http://localhost:9000/ahrefs/mcp)",
    )
    args = parser.parse_args(argv)

    base_path: str = args.base.rstrip("/")
    sse_url = f"{base_path}/sse"
    print(f"[+] Opening SSE stream → {sse_url}")

    q: "queue.Queue[str|None]" = queue.Queue()
    listener = SseListener(sse_url, q)
    listener.start()

    try:
        # ------------------------------------------------------------------
        # 1. Wait for the endpoint event
        # ------------------------------------------------------------------
        endpoint_path: Optional[str] = None
        while endpoint_path is None:
            evt = q.get(timeout=10)
            if evt is None:
                raise RuntimeError("SSE stream closed before endpoint event arrived")
            if evt.startswith("__ERROR__"):
                raise RuntimeError(evt.removeprefix("__ERROR__"))
            endpoint_path = parse_endpoint_event(evt)
        msg_url = f"{base_path}{endpoint_path}"
        session_id_match = re.search(r"session_id=([0-9a-fA-F]+)", endpoint_path)
        sid_disp = session_id_match.group(1) if session_id_match else "<unknown>"
        print(f"[+] Connected – session_id = {sid_disp}")

        # ------------------------------------------------------------------
        # 2. Initialization handshake
        # ------------------------------------------------------------------
        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                "clientInfo": {"name": "AutoMCP-SmokeTest", "version": "0.1"},
            },
        }
        print("[+] Sending initialize…")
        post_json(msg_url, init_payload)

        # Wait for the initialize result
        init_ok = False
        while not init_ok:
            evt = q.get(timeout=10)
            if evt is None:
                raise RuntimeError("SSE closed while waiting for initialize result")
            data = parse_json_event(evt)
            if data and data.get("id") == 1 and "result" in data:
                init_ok = True
                print("[✓] initialize acknowledged by server")

        # Send notifications/initialized
        post_json(msg_url, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        print("[+] Sent notifications/initialized")

        # ------------------------------------------------------------------
        # 3. tools/list, resources/list, prompts/list
        # ------------------------------------------------------------------
        requests_payloads = [
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "resources/list"},
            {"jsonrpc": "2.0", "id": 4, "method": "prompts/list"},
        ]
        for p in requests_payloads:
            post_json(msg_url, p)
            print(f"[+] Sent {p['method']}")

        # Collect the three results
        received: dict[int, Any] = {}
        while len(received) < 3:
            evt = q.get(timeout=15)
            if evt is None:
                raise RuntimeError("SSE closed before all results arrived")
            data = parse_json_event(evt)
            if data and isinstance(data.get("id"), int):
                req_id = data["id"]
                if req_id in (2, 3, 4):
                    received[req_id] = data["result"]
                    print(f"[✓] Received result for id={req_id}")

        # ------------------------------------------------------------------
        # 4. Pretty-print the results
        # ------------------------------------------------------------------
        print("\n================  tools/list  ================")
        print(json.dumps(received[2], indent=2))
        print("\n================  resources/list  ================")
        print(json.dumps(received[3], indent=2))
        print("\n================  prompts/list  ================")
        print(json.dumps(received[4], indent=2))

    finally:
        listener.stop()
        listener.join(timeout=2)


if __name__ == "__main__":  # pragma: no cover – CLI only
    main()
