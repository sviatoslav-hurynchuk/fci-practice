import json
import socket
from typing import Any, Dict, List, Optional, Tuple


class VRPSimClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 47560, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None
        self.reader = None
        self.writer = None
        self.connected = False
        self.task: Dict[str, Any] = {}
        self.reference_cost: float = 0.0

    def connect(self) -> Dict[str, Any]:
        self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self.reader = self.sock.makefile("r", encoding="utf-8", newline="\n")
        self.writer = self.sock.makefile("w", encoding="utf-8", newline="\n")
        hello_line = self.reader.readline()
        if not hello_line:
            raise ConnectionError("Server closed connection without greeting")
        hello = json.loads(hello_line)
        if hello.get("type") == "error":
            raise RuntimeError(hello.get("message", "Unknown error from VRPSim"))
        self.task = hello.get("task", {})
        self.reference_cost = float(hello.get("reference_cost", 0.0))
        self.connected = True
        return hello

    def send_solution(self, routes: List[List[int]], iteration: Optional[int] = None, info: Optional[str] = None) -> Dict[str, Any]:
        if not self.connected or not self.writer or not self.reader:
            raise ConnectionError("Not connected to VRPSim server")
        payload: Dict[str, Any] = {"type": "solution", "routes": routes}
        if iteration is not None:
            payload["iteration"] = int(iteration)
        if info is not None:
            payload["info"] = str(info)
        self.writer.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.writer.flush()
        response_line = self.reader.readline()
        if not response_line:
            raise ConnectionError("Connection lost while reading solution response")
        return json.loads(response_line)

    def send_pheromone(self, edges: List[Tuple[int, int, float]]) -> Dict[str, Any]:
        if not self.connected or not self.writer or not self.reader:
            raise ConnectionError("Not connected to VRPSim server")
        formatted_edges = [[int(u), int(v), float(round(tau, 4))] for u, v, tau in edges]
        payload = {"type": "pheromone", "edges": formatted_edges}
        self.writer.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.writer.flush()
        response_line = self.reader.readline()
        if not response_line:
            raise ConnectionError("Connection lost while reading pheromone response")
        return json.loads(response_line)

    def close(self) -> None:
        self.connected = False
        try:
            if self.writer:
                self.writer.close()
        except Exception:
            pass
        try:
            if self.reader:
                self.reader.close()
        except Exception:
            pass
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        self.sock = None
        self.reader = None
        self.writer = None
