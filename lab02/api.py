import json
import ssl
import urllib.error
import urllib.request


class FoxHuntAPI:
    def __init__(self, base_url: str = "https://ooi-lab2.up.railway.app"):
        self.base_url = base_url.rstrip("/")
        self.session_id: str | None = None
        self.ssl_context = ssl._create_unverified_context()

    def start_session(self, student_name: str, variant_number: int) -> dict:
        url = f"{self.base_url}/api/start"
        payload = {
            "student_name": student_name,
            "variant_number": variant_number
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0"
            }
        )
        try:
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=15) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                self.session_id = res["session_id"]
                return res
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            raise RuntimeError(f"API Error {e.code}: {err_msg}")

    def make_move(self, x: int, y: int) -> dict:
        if not self.session_id:
            raise ValueError("Session is not initialized. Call start_session first.")

        url = f"{self.base_url}/api/move"
        payload = {
            "session_id": self.session_id,
            "target_position": {"x": int(x), "y": int(y)}
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0"
            }
        )
        try:
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            raise RuntimeError(f"Move Error {e.code} at ({x}, {y}): {err_msg}")
