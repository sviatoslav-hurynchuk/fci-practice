import requests


class SonarAPI:
    DEFAULT_BASE_URL = "https://ooi-lab1.up.railway.app"

    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def get_config(self) -> dict:
        url = f"{self.base_url}/api/config"
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        return response.json()

    def get_pulse(self) -> list[float]:
        url = f"{self.base_url}/api/pulse"
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        return response.json()

    def get_sensor_signal(self, step: int) -> list[float]:
        url = f"{self.base_url}/api/sensor?step={step}"
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        return response.json()

    def get_step_signals(self, step: int, count: int = 4) -> list[list[float]]:
        return [self.get_sensor_signal(step) for _ in range(count)]
