"""QMP (QEMU Monitor Protocol) client for VM control."""
import socket
import json
import time


class QMPClient:
    """Connect to QEMU via QMP Unix socket and send commands."""

    def __init__(self, sock_path: str):
        self.sock_path = sock_path
        self._sock = None
        self._connected = False

    def connect(self, timeout=5.0):
        """Connect to QMP socket and complete handshake."""
        if self._connected:
            return

        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.settimeout(timeout)
        self._sock.connect(self.sock_path)

        # Read greeting
        greeting = self._recv_json()
        if greeting.get("QMP", {}).get("capabilities"):
            pass  # Greeting OK

        # Send capabilities negotiation
        self._send_json({"execute": "qmp-capabilities"})
        result = self._recv_json()
        self._connected = True

    def _send_json(self, obj: dict):
        """Send a JSON object."""
        data = json.dumps(obj).encode("utf-8") + b"\n"
        self._sock.sendall(data)

    def _recv_json(self) -> dict:
        """Receive a JSON object."""
        buf = b""
        while True:
            chunk = self._sock.recv(4096)
            buf += chunk
            if b"\n" in buf:
                line = buf.split(b"\n")[0]
                return json.loads(line.decode("utf-8"))

    def exec(self, cmd: str, **kwargs) -> dict:
        """Execute a QMP command."""
        if not self._connected:
            self.connect()

        self._send_json({"execute": cmd, "arguments": kwargs})
        return self._recv_json()

    def close(self):
        """Close the connection."""
        if self._sock:
            self._sock.close()
            self._sock = None
            self._connected = False

    # Convenience methods
    def stop(self) -> dict:
        return self.exec("stop")

    def cont(self) -> dict:
        return self.exec("cont")

    def system_reset(self) -> dict:
        return self.exec("system_reset")

    def shutdown(self) -> dict:
        return self.exec("system_powerdown")

    def query_status(self) -> dict:
        return self.exec("query-status")

    def query_vnc(self) -> dict:
        return self.exec("query-vnc")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()
