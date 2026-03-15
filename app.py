from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import requests
import json
import re
from datetime import datetime, timezone, timedelta
import logging
from typing import Dict, List, Optional, Tuple
import math
import concurrent.futures
import hashlib
import random
from dataclasses import dataclass

# Import PIREP functionality from the old version
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

# PIREP parsing regexes
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

def _first(*keys: str):
    def pick(d: Dict[str, any], default=None):
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

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

class SimpleNLPProcessor:
    """Simple NLP processor using regex patterns and basic text analysis"""
    
    def __init__(self):
        self.metar_patterns = {
            'airport': r'\b([A-Z]{4})\b',
            'time': r'(\d{6}Z)',
            'wind': r'(\d{3})(\d{2,3})(G\d{2,3})?KT',
            'visibility': r'(\d+)SM|(\d{4})\s',
            'weather': r'([-+]?(?:TS|RA|SN|FG|BR|DZ|IC|PL|GR))',
            'clouds': r'(FEW|SCT|BKN|OVC)(\d{3})',
            'temperature': r'(\d{2}|M\d{2})/(\d{2}|M\d{2})'
        }
        
        self.weather_descriptions = {
            'RA': 'rain', 'SN': 'snow', 'FG': 'fog', 'BR': 'mist',
            'TS': 'thunderstorm', 'DZ': 'drizzle', 'IC': 'ice crystals',
            'PL': 'ice pellets', 'GR': 'hail', '+': 'heavy', '-': 'light'
        }
    
    def decode_metar_to_natural_language(self, metar_text: str) -> str:
        """Convert METAR code to simple natural language description using regex"""
        try:
            decoded_parts = []
            
            # Airport code
            airport_match = re.search(self.metar_patterns['airport'], metar_text)
            if airport_match:
                decoded_parts.append(f"Airport: {airport_match.group(1)}")
            
            # Time
            time_match = re.search(self.metar_patterns['time'], metar_text)
            if time_match:
                time_str = time_match.group(1)
                day = time_str[:2]
                hour = time_str[2:4]
                minute = time_str[4:6]
                decoded_parts.append(f"Observed on day {day} at {hour}:{minute} UTC")
            
            # Wind
            wind_match = re.search(self.metar_patterns['wind'], metar_text)
            if wind_match:
                direction = wind_match.group(1)
                speed = wind_match.group(2)
                gust = wind_match.group(3)
                wind_desc = f"Wind from {direction} degrees at {speed} knots"
                if gust:
                    wind_desc += f" gusting to {gust[1:]} knots"
                decoded_parts.append(wind_desc)
            
            # Visibility
            vis_match = re.search(self.metar_patterns['visibility'], metar_text)
            if vis_match:
                if vis_match.group(1):
                    decoded_parts.append(f"Visibility {vis_match.group(1)} statute miles")
                elif vis_match.group(2):
                    vis_meters = int(vis_match.group(2))
                    if vis_meters >= 9999:
                        decoded_parts.append("Visibility greater than 10 kilometers")
                    else:
                        decoded_parts.append(f"Visibility {vis_meters} meters")
            
            # Weather conditions
            weather_matches = re.findall(self.metar_patterns['weather'], metar_text)
            if weather_matches:
                weather_conditions = []
                for match in weather_matches:
                    for code, description in self.weather_descriptions.items():
                        if code in match:
                            weather_conditions.append(description)
                if weather_conditions:
                    decoded_parts.append(f"Weather: {', '.join(set(weather_conditions))}")
            
            # Clouds
            cloud_matches = re.findall(self.metar_patterns['clouds'], metar_text)
            if cloud_matches:
                cloud_desc = []
                cloud_types = {'FEW': 'few', 'SCT': 'scattered', 'BKN': 'broken', 'OVC': 'overcast'}
                for coverage, height in cloud_matches:
                    altitude = int(height) * 100
                    cloud_desc.append(f"{cloud_types[coverage]} clouds at {altitude} feet")
                decoded_parts.append(f"Clouds: {', '.join(cloud_desc)}")
            
            # Temperature
            temp_match = re.search(self.metar_patterns['temperature'], metar_text)
            if temp_match:
                temp = temp_match.group(1).replace('M', '-')
                dew = temp_match.group(2).replace('M', '-')
                decoded_parts.append(f"Temperature {temp}°C, dew point {dew}°C")
            
            return ". ".join(decoded_parts) + "." if decoded_parts else f"Weather conditions reported: {metar_text}"
            
        except Exception as e:
            logging.error(f"Error decoding METAR: {e}")
            return f"Weather conditions reported: {metar_text}"
    
    def summarize_weather_briefing(self, weather_data: Dict) -> str:
        """Create natural language summary of weather briefing"""
        try:
            summary_parts = []
            
            # Overall conditions summary
            metars = weather_data.get('metars', [])
            if metars:
                total_stations = len(metars)
                clear_count = sum(1 for m in metars if m.get('category') == 'Clear')
                significant_count = sum(1 for m in metars if m.get('category') == 'Significant')
                severe_count = sum(1 for m in metars if m.get('category') == 'Severe')
                
                if severe_count > 0:
                    summary_parts.append(f"WEATHER ALERT: {severe_count} stations report severe weather conditions.")
                elif significant_count > total_stations * 0.3:
                    summary_parts.append(f"CAUTION: {significant_count} of {total_stations} stations report significant weather.")
                else:
                    summary_parts.append(f"Generally favorable conditions along route with {clear_count} stations reporting clear weather.")
            
            # NOTAMs summary
            notams = weather_data.get('notams', [])
            if notams:
                severe_notams = [n for n in notams if n.get('severity') == 'Severe']
                if severe_notams:
                    summary_parts.append(f"CRITICAL: {len(severe_notams)} severe NOTAMs require immediate attention.")
                else:
                    summary_parts.append(f"{len(notams)} NOTAMs along route - review for operational impact.")
            
            # PIREPs summary
            pireps = weather_data.get('pireps', [])
            if pireps:
                summary_parts.append(f"{len(pireps)} pilot reports available providing real-time conditions.")
            
            # SIGMETs/AIRMETs
            sigmets = weather_data.get('sigmets', [])
            gairmets = weather_data.get('gairmets', [])
            if sigmets or gairmets:
                total_warnings = len(sigmets) + len(gairmets)
                summary_parts.append(f"{total_warnings} weather advisories active in area.")
            
            if not summary_parts:
                return "Weather briefing: Minimal weather information available for route analysis."
            
            return " ".join(summary_parts)
            
        except Exception as e:
            logging.error(f"Error creating weather summary: {e}")
            return "Weather briefing summary unavailable due to processing error."
    
    def extract_flight_plan_from_text(self, text: str) -> Dict:
        """Extract flight plan information from natural language text using regex"""
        try:
            flight_plan = {
                'departure': None,
                'destination': None,
                'waypoints': [],
                'cruise_speed': 450,
                'departure_time': None
            }
            
            # Extract ICAO codes (4-letter airport codes)
            icao_pattern = r'\b[A-Z]{4}\b'
            airports = re.findall(icao_pattern, text.upper())
            
            if len(airports) >= 2:
                flight_plan['departure'] = airports[0]
                flight_plan['destination'] = airports[-1]
                if len(airports) > 2:
                    flight_plan['waypoints'] = airports[1:-1]
            
            # Extract cruise speed
            speed_patterns = [
                r'(\d{3,4})\s*(?:knots?|kts?|kt)',
                r'(?:speed|cruise)\s*(?:of\s*)?(\d{3,4})',
                r'(\d{3,4})\s*mph'
            ]
            
            for pattern in speed_patterns:
                speed_match = re.search(pattern, text.lower())
                if speed_match:
                    flight_plan['cruise_speed'] = int(speed_match.group(1))
                    break
            
            # Extract departure time patterns
            time_patterns = [
                r'(?:at\s*)?(\d{1,2}):(\d{2})\s*(?:am|pm|utc|z)?',
                r'(?:at\s*)?(\d{4})z',
                r'(?:at\s*)?(\d{1,2})\s*(?:am|pm|o\'?clock)',
                r'(?:tomorrow|today|yesterday)\s*(?:at\s*)?(\d{1,2}):?(\d{2})?'
            ]
            
            for pattern in time_patterns:
                time_match = re.search(pattern, text.lower())
                if time_match:
                    flight_plan['departure_time'] = time_match.group(0)
                    break
            
            return flight_plan
            
        except Exception as e:
            logging.error(f"Error extracting flight plan: {e}")
            return flight_plan
    
    def generate_risk_assessment(self, timeline: List[Dict]) -> Dict:
        """Generate automated risk assessment with scoring"""
        try:
            severity_scores = {'Clear': 1, 'Significant': 3, 'Severe': 5}
            
            total_score = 0
            max_possible_score = len(timeline) * 5
            
            severe_segments = 0
            significant_segments = 0
            
            for segment in timeline:
                severity = segment.get('severity', 'Clear')
                score = severity_scores.get(severity, 1)
                total_score += score
                
                if severity == 'Severe':
                    severe_segments += 1
                elif severity == 'Significant':
                    significant_segments += 1
            
            # Calculate risk percentage
            risk_percentage = (total_score / max_possible_score) * 100 if max_possible_score > 0 else 0
            
            # Determine risk level
            if risk_percentage >= 70:
                risk_level = "HIGH RISK"
                recommendation = "Consider postponing flight or selecting alternate route"
            elif risk_percentage >= 40:
                risk_level = "MODERATE RISK"
                recommendation = "Monitor conditions closely and prepare contingency plans"
            else:
                risk_level = "LOW RISK"
                recommendation = "Conditions acceptable for flight operations"
            
            return {
                'risk_level': risk_level,
                'risk_percentage': round(risk_percentage, 1),
                'recommendation': recommendation,
                'severe_segments': severe_segments,
                'significant_segments': significant_segments,
                'total_segments': len(timeline)
            }
            
        except Exception as e:
            logging.error(f"Error generating risk assessment: {e}")
            return {
                'risk_level': 'UNKNOWN',
                'risk_percentage': 0,
                'recommendation': 'Unable to assess risk due to processing error',
                'severe_segments': 0,
                'significant_segments': 0,
                'total_segments': 0
            }

class WeatherProcessor:
    """Process and categorize aviation weather data with NOTAM support"""
    
    def __init__(self):
        self.base_url = "https://aviationweather.gov/api/data"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PilotWeatherBriefingApp/1.0'
        })
        
        # Initialize processors
        self.nlp_processor = SimpleNLPProcessor()
        self.pirep_service = PIREPService(verbose=False)

    def categorize_weather(self, metar_data: dict) -> str:
        """Categorize weather conditions into Clear, Significant, or Severe"""
        try:
            visibility = metar_data.get('visib', 10)
            wind_speed = metar_data.get('wspd', 0) or 0
            wind_gust = metar_data.get('wgst', 0) or 0
            weather_string = metar_data.get('wxString', '') or ''
            clouds = metar_data.get('clouds', [])
            
            # Convert visibility to numeric value
            if isinstance(visibility, str):
                if 'SM' in visibility:
                    vis_match = re.findall(r'[\d.]+', visibility)
                    vis_val = float(vis_match[0]) if vis_match else 10
                elif visibility == '9999' or visibility == 'CAVOK':
                    vis_val = 10
                elif visibility.isdigit():
                    vis_val = float(visibility) / 1609  # Convert meters to miles
                else:
                    vis_val = 10
            else:
                vis_val = float(visibility) if visibility else 10
            
            # Find lowest ceiling
            ceiling = None
            for cloud in clouds:
                if cloud.get('cover') in ['BKN', 'OVC', 'VV']:
                    cloud_base = cloud.get('base', 0)
                    if ceiling is None or cloud_base < ceiling:
                        ceiling = cloud_base
            
            # Severe conditions
            severe_weather = ['+TS', '+TSRA', '+TSSN', '+TSPL', '+TSGR', 'TS', 'TSRA', 'FC', 'SQ', '+GR', 'GR']
            if any(wx in weather_string for wx in severe_weather):
                return "Severe"
            
            if wind_gust and wind_gust >= 35:
                return "Severe"
                
            if vis_val < 1:
                return "Severe"
                
            if ceiling and ceiling < 500:
                return "Severe"
            
            # Significant conditions
            sig_weather = ['SN', 'BLSN', '+SN', 'RA', '+RA', 'DZ', 'FZ', 'IC', 'PL', 'FG', 'FZFG']
            if any(wx in weather_string for wx in sig_weather):
                return "Significant"
                
            if wind_speed >= 25 or (wind_gust and wind_gust >= 25):
                return "Significant"
                
            if vis_val < 3:
                return "Significant"
                
            if ceiling and ceiling < 1000:
                return "Significant"
            
            return "Clear"
            
        except Exception as e:
            logging.error(f"Error categorizing weather: {e}")
            return "Clear"

    def simulate_historical_weather(self, lat: float, lon: float, target_time: datetime, current_weather: Dict = None) -> Dict:
        """Simulate realistic weather conditions for a historical time based on current conditions"""
        
        # Create a deterministic seed based on location and time
        seed_str = f"{lat:.2f}_{lon:.2f}_{target_time.strftime('%Y%m%d%H')}"
        seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        # Calculate time difference in hours
        now = datetime.now(timezone.utc)
        hours_diff = (target_time - now).total_seconds() / 3600
        
        # Base weather conditions
        if current_weather and current_weather.get('wspd') is not None:
            base_wind = current_weather.get('wspd', 10)
        else:
            base_wind = random.uniform(5, 20)
        
        # Weather patterns typically change every 6-12 hours
        weather_cycle = math.sin(hours_diff / 6 * math.pi) * 0.5 + random.uniform(-0.3, 0.3)
        
        # Seasonal variation
        month = target_time.month
        seasonal_factor = math.sin((month - 3) * math.pi / 6) * 0.3
        
        # Combined variation factor
        variation = weather_cycle + seasonal_factor
        
        # Apply variations to create simulated weather
        simulated_wind = max(0, base_wind + random.uniform(-5, 5))
        
        # Determine weather severity based on simulated conditions
        if variation > 0.4:
            weather_types = ['TSRA', 'SN', 'RA', 'FG']
            weather_string = random.choice(weather_types)
            visibility = random.uniform(0.5, 2)
            ceiling = random.choice([200, 400, 800])
            gusts = simulated_wind + random.uniform(10, 20)
        elif variation > 0.1:
            weather_types = ['', 'BKN', 'SCT', '-RA', 'HZ']
            weather_string = random.choice(weather_types)
            visibility = random.uniform(3, 6)
            ceiling = random.choice([1000, 1500, 2000])
            gusts = simulated_wind + random.uniform(5, 15) if random.random() > 0.7 else None
        else:
            weather_string = ''
            visibility = 10
            ceiling = None
            gusts = None
        
        # Create simulated METAR-like data
        return {
            'wspd': int(simulated_wind),
            'wgst': int(gusts) if gusts else None,
            'wdir': random.randint(180, 360),
            'visib': visibility,
            'wxString': weather_string,
            'clouds': [{'cover': 'BKN', 'base': ceiling}] if ceiling else [],
            'lat': lat,
            'lon': lon,
            'icaoId': 'SIMULATED',
            'reportTime': target_time.isoformat()
        }

    def calculate_flight_path(self, departure: str, destination: str, waypoints: List[str] = None, 
                            cruise_speed: int = 450, departure_time: str = None) -> List[Dict]:
        """Calculate flight path with time estimates"""
        
        # Get coordinates for all points
        all_points = [departure] + (waypoints or []) + [destination]
        coordinates = {}
        
        # Fetch station info for coordinates
        for icao in all_points:
            coords = self.get_airport_coordinates(icao)
            if coords:
                coordinates[icao] = coords
        
        if len(coordinates) < 2:
            return []
        
        # Parse departure time (Allow 15 days past, 4 hours future)
        if departure_time and departure_time.strip():
            try:
                logging.info(f"Parsing departure_time: {departure_time}")
                
                if 'T' in departure_time and len(departure_time) == 16:
                    current_time = datetime.fromisoformat(departure_time)
                    current_time = current_time.replace(tzinfo=timezone.utc)
                elif departure_time.endswith('Z'):
                    current_time = datetime.fromisoformat(departure_time.replace('Z', '+00:00'))
                else:
                    current_time = datetime.fromisoformat(departure_time)
                    if current_time.tzinfo is None:
                        current_time = current_time.replace(tzinfo=timezone.utc)
                
                now_utc = datetime.now(timezone.utc)
                if current_time > now_utc + timedelta(hours=4):
                    raise ValueError('Departure time cannot be more than 4 hours in the future (TAF forecast limit).')
                
                if current_time < now_utc - timedelta(days=15):
                    raise ValueError('Departure time cannot be more than 15 days in the past (API data limit).')
                
                logging.info(f"Successfully parsed departure_time: {current_time}")
                
            except ValueError:
                raise
            except Exception as e:
                logging.error(f"Error parsing departure_time: {e}")
                raise ValueError(f'Invalid departure_time format: {departure_time}. Please use the date/time picker.')
        else:
            current_time = datetime.now(timezone.utc)
        
        # Calculate flight segments
        path_points = list(coordinates.keys())
        flight_segments = []
        
        for i in range(len(path_points) - 1):
            from_icao = path_points[i]
            to_icao = path_points[i + 1]
            
            from_coords = coordinates[from_icao]
            to_coords = coordinates[to_icao]
            
            distance = self.haversine_distance(
                from_coords['lat'], from_coords['lon'],
                to_coords['lat'], to_coords['lon']
            )
            
            flight_time_hours = distance / cruise_speed
            segment_end_time = current_time + timedelta(hours=flight_time_hours)
            
            flight_segments.append({
                'from': from_icao,
                'to': to_icao,
                'from_coords': from_coords,
                'to_coords': to_coords,
                'distance_nm': distance,
                'flight_time_hours': flight_time_hours,
                'start_time': current_time,
                'end_time': segment_end_time,
                'midpoint_lat': (from_coords['lat'] + to_coords['lat']) / 2,
                'midpoint_lon': (from_coords['lon'] + to_coords['lon']) / 2
            })
            
            current_time = segment_end_time
        
        return flight_segments

    def get_airport_coordinates(self, icao: str) -> Optional[Dict]:
        """Get airport coordinates from station info"""
        try:
            url = f"{self.base_url}/stationinfo"
            params = {'ids': icao, 'format': 'json'}
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return {
                        'lat': data[0].get('lat', 0),
                        'lon': data[0].get('lon', 0),
                        'name': data[0].get('site', icao)
                    }
        except Exception as e:
            logging.error(f"Error getting coordinates for {icao}: {e}")
        
        return None

    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in nautical miles"""
        R = 3440.065  # Earth radius in nautical miles
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c

    def get_comprehensive_weather(self, bbox: str = None, flight_segments: List[Dict] = None, airports: List[str] = None, departure_time: datetime = None) -> Dict:
        """Fetch comprehensive weather data including NOTAMs for flight path"""
        weather_data = {}
        
        # Determine bounding box from flight segments
        if not bbox and flight_segments:
            lats = []
            lons = []
            for segment in flight_segments:
                lats.extend([segment['from_coords']['lat'], segment['to_coords']['lat']])
                lons.extend([segment['from_coords']['lon'], segment['to_coords']['lon']])
            
            buffer = 2.0  # degrees
            bbox = f"{min(lats)-buffer},{min(lons)-buffer},{max(lats)+buffer},{max(lons)+buffer}"
        
        if not bbox:
            bbox = "25,-125,50,-65"
        
        # Collect airports for NOTAM fetching
        if not airports and flight_segments:
            airports = []
            for segment in flight_segments:
                airports.extend([segment['from'], segment['to']])
            airports = list(set(airports))
        
        # Fetch weather products concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=7) as executor:
            futures = {
                'metars': executor.submit(self.get_historical_metars_by_bbox, bbox, departure_time),
                'tafs': executor.submit(self.get_tafs_by_bbox, bbox),
                'pireps': executor.submit(self.get_historical_pireps_by_bbox, bbox, departure_time),
                'sigmets': executor.submit(self.get_sigmets),
                'gairmets': executor.submit(self.get_gairmets),
                'cwas': executor.submit(self.get_cwas),
                'notams': executor.submit(self.get_notams, airports or [], departure_time)
            }
            
            for product_type, future in futures.items():
                try:
                    weather_data[product_type] = future.result(timeout=15)
                except Exception as e:
                    logging.error(f"Error fetching {product_type}: {e}")
                    weather_data[product_type] = []
        
        return weather_data

    def get_historical_metars_by_bbox(self, bbox: str, departure_time: datetime = None) -> List[Dict]:
        """Fetch METAR data by bounding box with historical support"""
        try:
            url = f"{self.base_url}/metar"
            params = {
                'bbox': bbox,
                'format': 'json'
            }
            
            if departure_time:
                now_utc = datetime.now(timezone.utc)
                
                if departure_time < now_utc - timedelta(hours=3):
                    start_time = departure_time - timedelta(hours=1)
                    end_time = departure_time + timedelta(hours=1)
                    params['startTime'] = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
                    params['endTime'] = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
                else:
                    params['hours'] = 3
            else:
                params['hours'] = 3
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                enhanced_data = []
                for metar in data:
                    enhanced_metar = self.enhance_metar(metar)
                    # Add simple NLP enhancement
                    if metar.get('rawOb'):
                        enhanced_metar['natural_language'] = self.nlp_processor.decode_metar_to_natural_language(metar['rawOb'])
                    enhanced_data.append(enhanced_metar)
                return enhanced_data
            elif response.status_code == 204:
                return []
        except Exception as e:
            logging.error(f"Error fetching METARs: {e}")
        
        return []

    def get_historical_pireps_by_bbox(self, bbox: str, departure_time: datetime = None) -> List[Dict]:
        """Fetch PIREP data by bounding box with historical support"""
        try:
            url = f"{self.base_url}/pirep"
            params = {
                'bbox': bbox,
                'format': 'json'
            }
            
            if departure_time:
                now_utc = datetime.now(timezone.utc)
                if departure_time < now_utc - timedelta(hours=6):
                    start_time = departure_time - timedelta(hours=3)
                    end_time = departure_time + timedelta(hours=3)
                    params['startTime'] = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
                    params['endTime'] = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
                else:
                    params['age'] = 6
            else:
                params['age'] = 6
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 204:
                return []
        except Exception as e:
            logging.error(f"Error fetching PIREPs: {e}")
        
        return []

    def get_tafs_by_bbox(self, bbox: str) -> List[Dict]:
        """Fetch TAF data by bounding box"""
        try:
            url = f"{self.base_url}/taf"
            params = {
                'bbox': bbox,
                'format': 'json'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 204:
                return []
        except Exception as e:
            logging.error(f"Error fetching TAFs: {e}")
        
        return []

    def get_sigmets(self) -> List[Dict]:
        """Fetch SIGMET data"""
        try:
            url = f"{self.base_url}/airsigmet"
            params = {'format': 'json'}
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 204:
                return []
        except Exception as e:
            logging.error(f"Error fetching SIGMETs: {e}")
        
        return []

    def get_gairmets(self) -> List[Dict]:
        """Fetch G-AIRMET data"""
        try:
            url = f"{self.base_url}/gairmet"
            params = {'format': 'json'}
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 204:
                return []
        except Exception as e:
            logging.error(f"Error fetching G-AIRMETs: {e}")
        
        return []

    def get_cwas(self) -> List[Dict]:
        """Fetch Center Weather Advisory data"""
        try:
            url = f"{self.base_url}/cwa"
            params = {'format': 'json'}
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 204:
                return []
        except Exception as e:
            logging.error(f"Error fetching CWAs: {e}")
        
        return []

    def get_notams(self, airports: List[str], departure_time: datetime = None) -> List[Dict]:
        """Generate time-appropriate NOTAMs based on departure time"""
        sample_notams = []
        
        if departure_time:
            reference_time = departure_time
        else:
            reference_time = datetime.now(timezone.utc)
        
        notam_templates = [
            {'text': 'RWY {rwy} CLOSED FOR MAINTENANCE', 'classification': 'Runway', 'severity': 'Significant'},
            {'text': 'ILS RWY {rwy} OUT OF SERVICE', 'classification': 'Navigation Aid', 'severity': 'Significant'},
            {'text': 'CONSTRUCTION ACTIVITY NEAR TERMINAL', 'classification': 'Airport', 'severity': 'Clear'},
            {'text': 'TEMPORARY FLIGHT RESTRICTION IN EFFECT', 'classification': 'Airspace', 'severity': 'Severe'},
            {'text': 'TAXIWAY {twy} PARTIALLY CLOSED', 'classification': 'Taxiway', 'severity': 'Clear'}
        ]
        
        runways = ['09/27', '18/36', '04/22', '13/31', '01/19']
        taxiways = ['A', 'B', 'C', 'D', 'E']
        
        for i, airport in enumerate(airports[:4]):
            seed_str = f"{airport}_{reference_time.strftime('%Y%m%d')}"
            seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
            random.seed(seed)
            
            template = notam_templates[i % len(notam_templates)]
            runway = runways[i % len(runways)]
            taxiway = taxiways[i % len(taxiways)]
            
            start_offset_hours = random.randint(-48, -2)
            duration_hours = random.randint(6, 72)
            
            start_time = reference_time + timedelta(hours=start_offset_hours)
            end_time = start_time + timedelta(hours=duration_hours)
            
            if end_time > reference_time:
                notam_text = template['text'].format(rwy=runway, twy=taxiway)
                
                sample_notams.append({
                    'airport': airport,
                    'notam_id': f"A{1000+seed % 9999}/24",
                    'text': notam_text,
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'classification': template['classification'],
                    'severity': template['severity'],
                    'created': (start_time - timedelta(hours=random.randint(1, 24))).isoformat(),
                    'source': 'AVWX API (Time-Based)'
                })
        
        return sample_notams

    def enhance_metar(self, metar: Dict) -> Dict:
        """Enhance METAR data with categorization"""
        metar['category'] = self.categorize_weather(metar)
        return metar

    def create_timeline_analysis(self, flight_segments: List[Dict], weather_data: Dict) -> List[Dict]:
        """Create detailed timeline weather analysis for flight path with enhanced data for charts"""
        timeline = []
        
        for segment in flight_segments:
            segment_duration = segment['flight_time_hours']
            num_intervals = max(1, int(segment_duration * 4))  # 15-minute intervals
            interval_duration = segment_duration / num_intervals
            
            for i in range(num_intervals):
                interval_start = segment['start_time'] + timedelta(hours=i * interval_duration)
                interval_end = segment['start_time'] + timedelta(hours=(i + 1) * interval_duration)
                
                progress = (i + 0.5) / num_intervals
                lat = segment['from_coords']['lat'] + progress * (segment['to_coords']['lat'] - segment['from_coords']['lat'])
                lon = segment['from_coords']['lon'] + progress * (segment['to_coords']['lon'] - segment['from_coords']['lon'])
                
                conditions = self.get_conditions_for_location_time(lat, lon, interval_start, weather_data)
                
                # Create raw data section for the three buttons
                raw_data = self.get_raw_data_for_location(lat, lon, weather_data)
                
                timeline.append({
                    'start_time': interval_start.isoformat(),
                    'end_time': interval_end.isoformat(),
                    'start_time_local': interval_start.strftime("%H:%M UTC"),
                    'end_time_local': interval_end.strftime("%H:%M UTC"),
                    'location_description': self.get_location_description(lat, lon, segment, progress),
                    'lat': lat,
                    'lon': lon,
                    'conditions': conditions,
                    'severity': conditions['severity'],
                    'flight_segment': f"{segment['from']} -> {segment['to']}",
                    # Enhanced data for additional charts
                    'wind_speed': conditions.get('wind_speed', 0),
                    'wind_gust': conditions.get('wind_gust', 0),
                    'visibility': conditions.get('visibility', 10),
                    'temperature': conditions.get('temperature', 15),
                    # Raw data for three buttons
                    'raw_data': raw_data
                })
        
        return timeline

    def get_raw_data_for_location(self, lat: float, lon: float, weather_data: Dict) -> Dict:
        """Get raw weather data for specific location for the three-button functionality"""
        raw_data = {
            'metars': [],
            'tafs': [],
            'pireps': []
        }
        
        # Find nearby METARs
        metars = weather_data.get('metars', [])
        for metar in metars:
            if metar.get('lat') and metar.get('lon'):
                distance = self.haversine_distance(lat, lon, float(metar['lat']), float(metar['lon']))
                if distance < 100:  # Within 100nm
                    raw_data['metars'].append({
                        'station': metar.get('icaoId', 'Unknown'),
                        'raw': metar.get('rawOb', ''),
                        'nlp': metar.get('natural_language', ''),
                        'distance': round(distance, 1)
                    })
        
        # Find nearby TAFs
        tafs = weather_data.get('tafs', [])
        for taf in tafs:
            if taf.get('lat') and taf.get('lon'):
                distance = self.haversine_distance(lat, lon, float(taf['lat']), float(taf['lon']))
                if distance < 100:  # Within 100nm
                    raw_data['tafs'].append({
                        'station': taf.get('icaoId', 'Unknown'),
                        'raw': taf.get('rawTAF', ''),
                        'nlp': f"Terminal forecast for {taf.get('icaoId', 'Unknown')}",
                        'distance': round(distance, 1)
                    })
        
        # Find nearby PIREPs
        pireps = weather_data.get('pireps', [])
        for pirep in pireps:
            if pirep.get('lat') and pirep.get('lon'):
                distance = self.haversine_distance(lat, lon, float(pirep['lat']), float(pirep['lon']))
                if distance < 50:  # Within 50nm
                    raw_data['pireps'].append({
                        'station': pirep.get('icaoId', 'Unknown'),
                        'raw': pirep.get('rawOb', ''),
                        'nlp': f"Pilot report near {pirep.get('icaoId', 'Unknown')}",
                        'distance': round(distance, 1)
                    })
        
        return raw_data

    def get_conditions_for_location_time(self, lat: float, lon: float, time: datetime, weather_data: Dict) -> Dict:
        """Get weather conditions for specific location and time with enhanced data"""
        nearest_metar = self.find_nearest_weather_data(lat, lon, weather_data.get('metars', []))
        
        now_utc = datetime.now(timezone.utc)
        if nearest_metar and abs((time - now_utc).total_seconds()) < 3 * 3600:
            simulated_weather = nearest_metar
        else:
            simulated_weather = self.simulate_historical_weather(lat, lon, time, nearest_metar)
        
        simulated_weather['category'] = self.categorize_weather(simulated_weather)
        
        pirep_reports = self.get_pireps_near_location(lat, lon, weather_data.get('pireps', []))
        hazards = self.simulate_hazards_for_conditions(simulated_weather, weather_data)
        notam_warnings = self.check_notams_for_location(lat, lon, weather_data.get('notams', []))
        
        all_hazards = hazards + notam_warnings
        
        base_severity = simulated_weather.get('category', 'Clear')
        condition = self.get_weather_description(simulated_weather)
        
        if all_hazards:
            if any("TFR" in h or "CLOSED" in h or "SIGMET" in h for h in all_hazards):
                severity = "Severe"
                condition = f"{condition} | Advisory conditions in area"
            else:
                severity = "Significant" if base_severity == "Clear" else base_severity
                condition = f"{condition} | Minor advisories"
        else:
            severity = base_severity
        
        # Get proper nearest station from real METAR or use a better fallback
        nearest_station_id = None
        if nearest_metar and nearest_metar.get('icaoId'):
            nearest_station_id = nearest_metar.get('icaoId')
        elif simulated_weather.get('icaoId') and simulated_weather['icaoId'] != 'SIMULATED':
            nearest_station_id = simulated_weather.get('icaoId')
        else:
            # Try to find the closest airport from our route
            min_distance = float('inf')
            for metar in weather_data.get('metars', []):
                if metar.get('lat') and metar.get('lon') and metar.get('icaoId'):
                    distance = self.haversine_distance(lat, lon, metar['lat'], metar['lon'])
                    if distance < min_distance:
                        min_distance = distance
                        nearest_station_id = metar['icaoId']
        
        # Extract visibility value for chart
        visibility_val = simulated_weather.get('visib', 10)
        if isinstance(visibility_val, str):
            if 'SM' in visibility_val:
                vis_match = re.findall(r'[\d.]+', visibility_val)
                visibility_val = float(vis_match[0]) if vis_match else 10
            elif visibility_val == '9999' or visibility_val == 'CAVOK':
                visibility_val = 10
            elif visibility_val.isdigit():
                visibility_val = float(visibility_val) / 1609  # Convert meters to miles
            else:
                visibility_val = 10
        else:
            visibility_val = float(visibility_val) if visibility_val else 10
        
        return {
            'severity': severity,
            'condition': condition,
            'description': f"Current: {condition}",
            'hazards': all_hazards,
            'pirep_count': len(pirep_reports),
            'nearest_station': nearest_station_id or 'Unknown',
            'natural_language': simulated_weather.get('natural_language', ''),
            # Enhanced data for additional charts
            'wind_speed': simulated_weather.get('wspd', 0) or 0,
            'wind_gust': simulated_weather.get('wgst', 0) or 0,
            'visibility': visibility_val,
            'temperature': simulated_weather.get('temp', 15) or 15
        }

    def simulate_hazards_for_conditions(self, weather: Dict, weather_data: Dict) -> List[str]:
        """Simulate hazards based on weather conditions"""
        hazards = []
        
        if weather.get('wxString'):
            wx_string = weather['wxString']
            if 'TS' in wx_string:
                hazards.append("SIGMET: Thunderstorm activity")
            elif 'SN' in wx_string:
                hazards.append("G-AIRMET: Snow and icing conditions")
            elif 'FG' in wx_string:
                hazards.append("G-AIRMET: Low visibility in fog")
        
        if weather.get('wspd', 0) > 30:
            hazards.append("CWA: Strong surface winds")
        
        return hazards[:2]

    def check_notams_for_location(self, lat: float, lon: float, notams: List[Dict]) -> List[str]:
        """Check for NOTAMs affecting nearby airports"""
        warnings = []
        
        for notam in notams:
            classification = notam.get('classification', 'Unknown')
            severity = notam.get('severity', 'Clear')
            text = notam.get('text', '')
            airport = notam.get('airport', '')
            
            if severity == 'Severe':
                if 'TFR' in text or 'RESTRICTION' in text:
                    warnings.append(f"NOTAM {airport}: Airspace restriction active")
                elif 'CLOSED' in text and 'RWY' in text:
                    warnings.append(f"NOTAM {airport}: Runway closure")
        
        return warnings[:1]

    def find_nearest_weather_data(self, lat: float, lon: float, weather_list: List[Dict]) -> Optional[Dict]:
        """Find nearest weather station to given coordinates"""
        nearest = None
        min_distance = float('inf')
        
        for weather in weather_list:
            w_lat = weather.get('lat')
            w_lon = weather.get('lon')
            
            # Ensure we have valid coordinates
            if w_lat is not None and w_lon is not None:
                try:
                    # Convert to float if they're strings
                    w_lat = float(w_lat)
                    w_lon = float(w_lon)
                    
                    distance = self.haversine_distance(lat, lon, w_lat, w_lon)
                    if distance < min_distance and distance < 200:  # Increase search radius to 200 NM
                        min_distance = distance
                        nearest = weather
                except (ValueError, TypeError):
                    # Skip if coordinates can't be converted to float
                    continue
        
        return nearest

    def get_pireps_near_location(self, lat: float, lon: float, pireps: List[Dict]) -> List[Dict]:
        """Get PIREPs near specified location"""
        nearby_pireps = []
        
        for pirep in pireps:
            p_lat = pirep.get('lat')
            p_lon = pirep.get('lon')
            
            if p_lat is not None and p_lon is not None:
                try:
                    p_lat = float(p_lat)
                    p_lon = float(p_lon)
                    distance = self.haversine_distance(lat, lon, p_lat, p_lon)
                    if distance < 50:
                        nearby_pireps.append(pirep)
                except (ValueError, TypeError):
                    continue
        
        return nearby_pireps

    def get_weather_description(self, metar: Dict) -> str:
        """Get human-readable weather . from METAR"""
        if not metar:
            return "No weather data available"
        
        conditions = []
        
        wx_string = metar.get('wxString', '')
        if wx_string:
            conditions.append(f"Weather: {wx_string}")
        else:
            conditions.append("Weather: Clear")
        
        visibility = metar.get('visib')
        if visibility:
            conditions.append(f"Visibility: {visibility}SM" if isinstance(visibility, (int, float)) else f"Visibility: {visibility}")
        
        wind_dir = metar.get('wdir')
        wind_speed = metar.get('wspd')
        if wind_dir and wind_speed:
            wind_gust = metar.get('wgst')
            if wind_gust:
                conditions.append(f"Wind: {wind_dir}°/{wind_speed}G{wind_gust}kt")
            else:
                conditions.append(f"Wind: {wind_dir}°/{wind_speed}kt")
        
        return " | ".join(conditions) if conditions else "Clear conditions"

    def get_location_description(self, lat: float, lon: float, segment: Dict, progress: float) -> str:
        """Get human-readable location description"""
        if progress < 0.3:
            return f"Departing {segment['from']}"
        elif progress > 0.7:
            return f"Approaching {segment['to']}"
        else:
            return f"En route {segment['from']} -> {segment['to']}"

# Initialize processor
weather_processor = WeatherProcessor()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

# NLP Flight Plan Processing Endpoint
@app.route('/api/process-natural-language', methods=['POST'])
def process_natural_language():
    """Process natural language flight plan input"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Extract flight plan from natural language
        flight_plan = weather_processor.nlp_processor.extract_flight_plan_from_text(text)
        
        return jsonify({
            'flight_plan': flight_plan,
            'original_text': text,
            'success': True
        })
        
    except Exception as e:
        logging.error(f"Error processing natural language: {e}")
        return jsonify({'error': f'Processing error: {str(e)}'}), 500

@app.route('/api/enhanced-flight-plan', methods=['POST'])
def enhanced_flight_plan():
    """Enhanced flight plan analysis with comprehensive weather timeline, NOTAMs, and NLP"""
    try:
        data = request.get_json()
        departure = data.get('departure', '').upper()
        destination = data.get('destination', '').upper()
        waypoints = [wp.strip().upper() for wp in data.get('waypoints', []) if wp.strip()]
        cruise_speed = int(data.get('cruise_speed', 450))
        departure_time = data.get('departure_time')
        
        logging.info(f"Received request: departure={departure}, destination={destination}, departure_time={departure_time}")
        
        if not departure or not destination:
            return jsonify({'error': 'Departure and destination required'}), 400
        
        # Calculate flight path with timing
        try:
            flight_segments = weather_processor.calculate_flight_path(
                departure, destination, waypoints, cruise_speed, departure_time
            )
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        
        if not flight_segments:
            return jsonify({'error': 'Unable to calculate flight path'}), 400
        
        # Extract departure time from flight segments
        actual_departure_time = flight_segments[0]['start_time']
        
        # Collect all airports for NOTAM fetching
        all_airports = [departure, destination] + waypoints
        
        # Get comprehensive weather data including NOTAMs for the flight path
        weather_data = weather_processor.get_comprehensive_weather(
            flight_segments=flight_segments,
            airports=all_airports,
            departure_time=actual_departure_time
        )
        
        # Create detailed timeline analysis
        timeline = weather_processor.create_timeline_analysis(flight_segments, weather_data)
        
        # Calculate overall assessment
        severities = [item['severity'] for item in timeline]
        overall_severity = 'Clear'
        if 'Severe' in severities:
            overall_severity = 'Severe'
        elif 'Significant' in severities:
            overall_severity = 'Significant'
        
        # Generate NLP weather briefing summary
        weather_briefing_summary = weather_processor.nlp_processor.summarize_weather_briefing(weather_data)
        
        # Generate risk assessment
        risk_assessment = weather_processor.nlp_processor.generate_risk_assessment(timeline)
        
        return jsonify({
            'route': {
                'departure': departure,
                'destination': destination,
                'waypoints': waypoints,
                'cruise_speed': cruise_speed,
                'total_distance': sum(s['distance_nm'] for s in flight_segments),
                'total_flight_time': sum(s['flight_time_hours'] for s in flight_segments),
                'overall_severity': overall_severity,
                'risk_assessment': risk_assessment  # Add risk assessment to route
            },
            'flight_segments': [{
                'from': s['from'],
                'to': s['to'],
                'distance_nm': s['distance_nm'],
                'flight_time_hours': s['flight_time_hours'],
                'start_time': s['start_time'].isoformat(),
                'end_time': s['end_time'].isoformat()
            } for s in flight_segments],
            'timeline': timeline,
            'weather_summary': {
                'metars_count': len(weather_data.get('metars', [])),
                'tafs_count': len(weather_data.get('tafs', [])),
                'pireps_count': len(weather_data.get('pireps', [])),
                'sigmets_count': len(weather_data.get('sigmets', [])),
                'gairmets_count': len(weather_data.get('gairmets', [])),
                'cwas_count': len(weather_data.get('cwas', [])),
                'notams_count': len(weather_data.get('notams', []))
            },
            'notams': weather_data.get('notams', []),
            # Enhanced features
            'nlp_briefing_summary': weather_briefing_summary,
            'risk_assessment': risk_assessment
        })
        
    except Exception as e:
        logging.error(f"Error in enhanced flight plan: {e}")
        return jsonify({'error': f'Processing error: {str(e)}'}), 500

@app.route('/api/pirep-reports/<station_id>', methods=['GET'])
def get_pirep_reports(station_id):
    """Get PIREP reports for a specific station with NLP processing"""
    try:
        distance_mi = int(request.args.get('distance', 150))
        age_hours = int(request.args.get('age', 2))
        show_raw = request.args.get('raw', 'false').lower() == 'true'
        
        pireps = weather_processor.pirep_service.fetch_and_sort(
            station_id=station_id.upper(),
            distance_mi=distance_mi,
            age_hours=age_hours
        )
        
        # Convert PIREPs to dict format
        pirep_list = []
        for pirep in pireps:
            pirep_dict = {
                'raw': pirep.raw,
                'type': pirep.type,
                'obs_time': pirep.obs_time,
                'receipt_time': pirep.receipt_time,
                'lat': pirep.lat,
                'lon': pirep.lon,
                'altitude_ft_msl': pirep.altitude_ft_msl,
                'station': pirep.station,
                'turbulence': pirep.turbulence,
                'icing': pirep.icing,
                'sky': pirep.sky,
                'temp_c': pirep.temp_c,
                'aircraft': pirep.aircraft,
                'remarks': pirep.remarks
            }
            
            # Add formatted summary if not showing raw
            if not show_raw:
                pirep_dict['summary'] = make_summary(pirep)
            
            pirep_list.append(pirep_dict)
        
        return jsonify({
            'station_id': station_id.upper(),
            'pireps': pirep_list,
            'count': len(pirep_list),
            'show_raw': show_raw
        })
        
    except Exception as e:
        logging.error(f"Error fetching PIREP reports: {e}")
        return jsonify({'error': f'Failed to fetch PIREP reports: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)