import json
import socket


class DockSimError(Exception):
    def __init__(self, msg):
        super().__init__(f"{msg.get('code', 'error')}: {msg.get('message', '')}")
        self.code = msg.get("code")
        self.message = msg.get("message")


class DockSimClient:
    def __init__(self, host="127.0.0.1", port=47555):
        self.host = host
        self.port = port
        self.sock = socket.create_connection((host, port))
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.file = self.sock.makefile("r", encoding="utf-8")
        self.hello = self.recv()
        self.realtime = (self.hello.get("pace") == "realtime")
        self.last_report = None

    def send(self, msg: dict):
        line = json.dumps(msg) + "\n"
        self.sock.sendall(line.encode("utf-8"))

    def recv(self) -> dict:
        line = self.file.readline()
        if not line:
            raise ConnectionError("Server closed connection")
        msg = json.loads(line)
        if msg.get("type") == "error":
            raise DockSimError(msg)
        if msg.get("type") == "report":
            self.last_report = msg
        return msg

    def reset(self, seed=None) -> dict:
        cmd = {"cmd": "reset"}
        if seed is not None:
            cmd["seed"] = int(seed)
        self.send(cmd)
        return self.recv()

    def step(self, thrust: int, turn: int):
        self.send({"cmd": "step", "thrust": int(thrust), "turn": int(turn)})
        if self.realtime:
            return None
        return self.recv()

    def close(self):
        try:
            self.send({"cmd": "close"})
        except Exception:
            pass
        finally:
            try:
                self.file.close()
            except Exception:
                pass
            try:
                self.sock.close()
            except Exception:
                pass
