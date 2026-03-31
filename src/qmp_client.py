"""
QMP (QEMU Monitor Protocol) client.

QMP is QEMU's management interface — a JSON-based protocol communicated over
a Unix socket. This client handles connection, handshake, and sends commands
like stop, cont, system_reset, and query-status.

Unlike libvirt, QMP talks directly to the QEMU process without requiring
a daemon. This keeps the dependency footprint minimal.
"""

import socket
import json
from typing import Optional


class QMPClient:
    """
    Low-level QMP client that sends JSON commands to a QEMU process
    via a Unix domain socket.

    Usage:
        with QMPClient("/path/to/qmp.sock") as client:
            client.stop()
            client.system_reset()
    """

    def __init__(self, sock_path: str, timeout: float = 5.0):
        """
        Args:
            sock_path: Path to the QMP Unix socket.
            timeout: Socket connection/read timeout in seconds.
        """
        self.sock_path = sock_path
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._connected = False

    def connect(self):
        """
        Connect to the QMP socket and complete the QMP handshake.

        QMP requires an initial greeting from the server, then the client
        must send 'qmp-capabilities' before other commands are accepted.
        """
        if self._connected:
            return

        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.settimeout(self.timeout)
        self._sock.connect(self.sock_path)

        # Read server greeting (QMP-capable banner)
        greeting = self._recv_json()
        if not greeting.get("QMP"):
            raise RuntimeError(f"Unexpected QMP greeting: {greeting}")

        # Negotiate capabilities — required before any other commands
        self._send_json({"execute": "qmp-capabilities"})
        result = self._recv_json()
        if result.get("error"):
            raise RuntimeError(f"QMP capabilities negotiation failed: {result}")
        self._connected = True

    def _send_json(self, obj: dict):
        """Send a JSON object as a newline-delimited message."""
        data = json.dumps(obj).encode("utf-8") + b"\n"
        self._sock.sendall(data)

    def _recv_json(self) -> dict:
        """
        Receive a single JSON object from the socket.
        Reads until a newline is found (QMP uses one-JSON-object-per-line format).
        """
        buf = b""
        while b"\n" not in buf:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise EOFError("QMP socket closed unexpectedly")
            buf += chunk
        line = buf.split(b"\n", 1)[0]
        return json.loads(line.decode("utf-8"))

    def exec(self, cmd: str, **kwargs) -> dict:
        """
        Execute a QMP command and return the response.

        Args:
            cmd: QMP command name (e.g. "stop", "cont", "system_reset").
            **kwargs: Command arguments as keyword arguments.

        Returns:
            QMP response dict. Use .get("return") for success, .get("error") for errors.
        """
        if not self._connected:
            self.connect()

        self._send_json({"execute": cmd, "arguments": kwargs})
        return self._recv_json()

    def close(self):
        """Close the socket connection."""
        if self._sock:
            self._sock.close()
            self._sock = None
            self._connected = False

    # ── Convenience methods ───────────────────────────────────────────────

    def stop(self) -> dict:
        """Pause VM execution (QMP: stop)."""
        return self.exec("stop")

    def cont(self) -> dict:
        """Resume VM execution (QMP: cont)."""
        return self.exec("cont")

    def system_reset(self) -> dict:
        """Reset the VM as if the reset button was pressed (QMP: system_reset)."""
        return self.exec("system_reset")

    def shutdown(self) -> dict:
        """
        Request graceful shutdown (QMP: system_powerdown).
        The guest OS may handle this differently depending on its ACPI support.
        """
        return self.exec("system_powerdown")

    def query_status(self) -> dict:
        """Query current VM run state (QMP: query-status)."""
        return self.exec("query-status")

    def query_vnc(self) -> dict:
        """Query VNC server status (QMP: query-vnc)."""
        return self.exec("query-vnc")

    # ── Context manager ───────────────────────────────────────────────────

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()
