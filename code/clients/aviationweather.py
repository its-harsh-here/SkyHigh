# clients/aviationweather.py
import requests
from typing import Dict, Any, List
from config import Settings
from exceptions import ExternalAPIError

class AviationWeatherClient:
    def __init__(self, base_url: str = Settings.AVIATION_WEATHER_BASE, timeout: float = Settings.REQUEST_TIMEOUT_S):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "PilotWeatherBriefingApp/1.0"})
        self.timeout = timeout

    def _get(self, path: str, params: Dict[str, Any]) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        resp = self.session.get(url, params=params, timeout=self.timeout)
        if resp.status_code == 200:
            try:
                return resp.json()
            except Exception as e:
                raise ExternalAPIError(f"Bad JSON from {url}: {e}")
        if resp.status_code == 204:
            return []
        raise ExternalAPIError(f"HTTP {resp.status_code} fetching {url} with {params}")

    # Endpoints
    def stationinfo(self, ids: str) -> List[Dict]:
        return self._get("stationinfo", {"ids": ids, "format": "json"})

    def metar(self, **params) -> List[Dict]:
        return self._get("metar", {**params, "format": "json"})

    def taf(self, **params) -> List[Dict]:
        return self._get("taf", {**params, "format": "json"})

    def pirep(self, **params) -> List[Dict]:
        return self._get("pirep", {**params, "format": "json"})

    def airsigmet(self) -> List[Dict]:
        return self._get("airsigmet", {"format": "json"})

    def gairmet(self) -> List[Dict]:
        return self._get("gairmet", {"format": "json"})

    def cwa(self) -> List[Dict]:
        return self._get("cwa", {"format": "json"})
