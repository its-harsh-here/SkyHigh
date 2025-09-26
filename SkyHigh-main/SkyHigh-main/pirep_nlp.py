from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import requests
import re
from datetime import datetime, timezone
import argparse
import sys

# =============================
# Data class
# =============================
@dataclass
class PIREP:
    raw: str
    type: Optional[str] = None
    obs_time: Optional[str] = None
    receipt_time: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    altitude_ft_msl: Optional[int] = None
    station: Optional[str] = None
    turbulence: Optional[str] = None
    icing: Optional[str] = None
    sky: Optional[str] = None
    temp_c: Optional[float] = None
    aircraft: Optional[str] = None
    remarks: Optional[str] = None

# =============================
# Regex for raw decoding
# =============================
FL_RE = re.compile(r"/FL(\d+)")
TB_RE = re.compile(r"/TB\s*([^/]+)")
IC_RE = re.compile(r"/IC\s*([^/]+)")
SK_RE = re.compile(r"/SK\s*([^/]+)")
TA_RE = re.compile(r"/TA\s*([-+]?\d+)")
TP_RE = re.compile(r"/TP\s*([A-Z0-9]+)")
RM_RE = re.compile(r"/RM\s*([^/]+)")

INTENSITY_MAP = {
    "LGT": "Light",
    "MOD": "Moderate",
    "SEV": "Severe",
    "SVR": "Severe",
    "EXTM": "Extreme",
    "LGT-MOD": "Light to Moderate",
    "MOD-SEV": "Moderate to Severe",
    "NEG": "None",
    "OCNL": "Occasional",
    "CONS": "Continuous"
}

# =============================
# Severity icons
# =============================
def severity_icon(level: str) -> str:
    if not level:
        return ""
    if "Light" in level:
        return "✅"
    if "Moderate" in level:
        return "⚠️"
    if "Severe" in level or "Extreme" in level:
        return "🔴"
    return ""

# =============================
# ICAO → Airport Name lookup (extendable)
# =============================
AIRPORT_LOOKUP = {
    "KJFK": "John F. Kennedy International Airport, New York",
    "KLAX": "Los Angeles International Airport",
    "KBOS": "Boston Logan International Airport",
    "KSEA": "Seattle-Tacoma International Airport",
    "KSFO": "San Francisco International Airport",
    "KORD": "Chicago O'Hare International Airport",
    "KDEN": "Denver International Airport",
    "KATL": "Hartsfield-Jackson Atlanta International Airport",
    "KDFW": "Dallas/Fort Worth International Airport",
    "KLAS": "McCarran International Airport, Las Vegas",
    "KMIA": "Miami International Airport",
    "KPHX": "Phoenix Sky Harbor International Airport"
}

# =============================
# Parse raw text into fields
# =============================
def parse_raw(raw: str, base: Optional[PIREP] = None) -> PIREP:
    p = base or PIREP(raw=raw)
    if m := FL_RE.search(raw):
        p.altitude_ft_msl = int(m.group(1)) * 100
    if m := TB_RE.search(raw):
        tb_val = m.group(1).strip()
        p.turbulence = INTENSITY_MAP.get(tb_val, tb_val)
    if m := IC_RE.search(raw):
        ic_val = m.group(1).strip()
        p.icing = INTENSITY_MAP.get(ic_val, ic_val)
    if m := SK_RE.search(raw):
        p.sky = m.group(1).strip()
    if m := TA_RE.search(raw):
        try:
            p.temp_c = float(m.group(1))
        except:
            pass
    if m := TP_RE.search(raw):
        p.aircraft = m.group(1)
    if m := RM_RE.search(raw):
        p.remarks = m.group(1).strip()
    return p

# =============================
# Cloud parsing
# =============================
CLOUD_RE = re.compile(r"(FEW|SCT|BKN|OVC)(\d{2,3})?(CB|TCU)?", re.IGNORECASE)
CLOUD_WORD = {"FEW": "few", "SCT": "scattered", "BKN": "broken", "OVC": "overcast"}
CLOUD_TYPE = {"CB": "cumulonimbus", "TCU": "towering cumulus"}

def _format_clouds(sky: str) -> Optional[str]:
    if not sky:
        return None
    up = sky.upper()
    if "CLR" in up or "SKC" in up:
        return "clear skies"
    phrases = []
    for m in CLOUD_RE.finditer(up):
        layer, hgt, conv = m.groups()
        layer_word = CLOUD_WORD.get(layer, layer.lower())
        add = f" {CLOUD_TYPE.get(conv, conv.lower())}" if conv else ""
        if hgt:
            try:
                feet = int(hgt) * 100
                phrases.append(f"{layer_word}{add} at {feet} ft")
            except:
                phrases.append(f"{layer_word}{add}")
        else:
            phrases.append(f"{layer_word}{add}")
    return ", ".join(phrases) if phrases else sky.lower()

# =============================
# Relative time formatter
# =============================
def relative_time(timestr: Optional[str]) -> str:
    if not timestr:
        return "time unknown"
    if str(timestr).isdigit():
        try:
            t = datetime.fromtimestamp(int(timestr), tz=timezone.utc)
        except Exception:
            return f"reported at {timestr}"
    else:
        try:
            t = datetime.fromisoformat(str(timestr).replace("Z", "+00:00"))
        except Exception:
            return f"reported at {timestr}"

    now = datetime.now(timezone.utc)
    delta = now - t
    mins = int(delta.total_seconds() // 60)

    if mins < 1:
        return "observed just now"
    if mins < 60:
        return f"observed {mins} minutes ago"
    hours, mins = divmod(mins, 60)
    return f"observed {hours}h {mins}m ago"

# =============================
# Detailed English Summary
# =============================
def make_summary(p: PIREP) -> str:
    parts = []
    if p.turbulence:
        parts.append(f"{severity_icon(p.turbulence)} {p.turbulence} turbulence reported")
    if p.icing:
        parts.append(f"{severity_icon(p.icing)} {p.icing} icing observed")
    clouds = _format_clouds(p.sky or "")
    if clouds:
        parts.append(clouds)
    if p.temp_c is not None:
        temp_str = f"{p.temp_c:.0f}" if float(p.temp_c).is_integer() else f"{p.temp_c}"
        parts.append(f"temperature {temp_str} degrees Celsius")
    if p.aircraft:
        parts.append(f"aircraft type {p.aircraft}")
    if p.remarks:
        parts.append(f"remarks {p.remarks}")
    alt = f"{p.altitude_ft_msl} ft" if p.altitude_ft_msl else "altitude not given"
    loc = AIRPORT_LOOKUP.get(p.station, f"near {p.station}") if p.station else "location unknown"
    time_info = relative_time(p.obs_time or p.receipt_time)
    return " | ".join(str(x) for x in (parts + [alt, loc, time_info]))

# =============================
# API Response helpers
# =============================
def _first(*keys: str):
    def pick(d: Dict[str, Any], default=None):
        for k in keys:
            if k in d and d[k] not in (None, ""):
                return d[k]
        return default
    return pick

_pick_raw = _first("rawOb", "rawText", "raw", "report")
_pick_obs_time = _first("obsTime", "observationTime", "observation_time", "timeObs", "TM")
_pick_receipt_time = _first("receiptTime", "receipt_time")
_pick_lat = _first("lat", "latitude")
_pick_lon = _first("lon", "longitude")
_pick_alt_ft = _first("altitude_ft_msl", "altitudeFtMsl", "altitude_ft", "altitudeFt", "altitude", "FL")
_pick_station = _first("station", "stationId", "icaoId", "airport", "id", "location")

# =============================
# API Service
# =============================
class PIREPService:
    def __init__(self, base_url: str = "https://aviationweather.gov/api/data", verbose: bool = False):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "PIREPSummarizer/5.0"})
        self.verbose = verbose

    def _log(self, *args):
        if self.verbose:
            print(*args, file=sys.stderr)

    def fetch(self, *, station_id: str, distance_mi: int = 150, age_hours: int = 2, fmt: str = "json") -> List[Dict]:
        url = f"{self.base_url}/pirep"
        params = {"format": fmt, "age": age_hours, "id": station_id, "distance": distance_mi}
        try:
            r = self.session.get(url, params=params, timeout=15)
            if r.status_code == 204:
                return []
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                for key in ("reports", "data", "pireps", "items"):
                    if key in data and isinstance(data[key], list):
                        return data[key]
                return [data]
            return []
        except Exception as e:
            self._log(f"[WARN] Request failed: {e}")
            return []

    def parse_api_json(self, items: List[Dict]) -> List[PIREP]:
        pireps: List[PIREP] = []
        for it in items:
            p = PIREP(
                raw=_pick_raw(it, ""),
                type=_first("type", "reportType")(it),
                obs_time=_pick_obs_time(it),
                receipt_time=_pick_receipt_time(it),
                lat=_pick_lat(it),
                lon=_pick_lon(it),
                altitude_ft_msl=_pick_alt_ft(it),
                station=_pick_station(it),
            )
            pireps.append(parse_raw(p.raw or "", base=p))
        return pireps

    def fetch_and_sort(self, *, station_id: str, distance_mi: int = 150, age_hours: int = 2) -> List[PIREP]:
        items = self.fetch(station_id=station_id, distance_mi=distance_mi, age_hours=age_hours)
        if not items:
            return []
        pireps = self.parse_api_json(items)

        def sort_key(p: PIREP):
            time_str = p.obs_time or p.receipt_time
            try:
                if str(time_str).isdigit():
                    return datetime.fromtimestamp(int(time_str), tz=timezone.utc)
                return datetime.fromisoformat(str(time_str).replace("Z", "+00:00"))
            except Exception:
                return datetime.min

        return sorted(pireps, key=sort_key, reverse=True)

# =============================
# CLI & Main
# =============================
def main():
    parser = argparse.ArgumentParser(description="Fetch and summarize PIREPs (time-sorted).")
    parser.add_argument("--id", type=str, required=True, help="ICAO (e.g. KJFK)")
    parser.add_argument("--altmin", type=int, default=0, help="Minimum altitude in feet")
    parser.add_argument("--altmax", type=int, default=50000, help="Maximum altitude in feet")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    service = PIREPService(verbose=args.verbose)
    pireps = service.fetch_and_sort(station_id=args.id)

    # Altitude filter
    pireps = [p for p in pireps if p.altitude_ft_msl and args.altmin <= p.altitude_ft_msl <= args.altmax]

    if not pireps:
        print("No PIREPs available for given query.")
        return

    for p in pireps:
        print(make_summary(p))
        print(" RAW:", p.raw)

if __name__ == "__main__":
    main()
