# services/weather_service.py
import concurrent.futures
import hashlib, logging, math, random, re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from config import Settings
from clients.aviationweather import AviationWeatherClient
from services.nlp_service import SimpleNLPProcessor
from utils.geo import haversine_nm
from utils.timeutils import now_utc
from exceptions import UserInputError

class WeatherService:
    def __init__(self, client: Optional[AviationWeatherClient] = None, nlp: Optional[SimpleNLPProcessor] = None):
        self.client = client or AviationWeatherClient()
        self.nlp = nlp or SimpleNLPProcessor()

    # === Public API ===
    def calculate_flight_path(self, departure: str, destination: str, waypoints: List[str], cruise_speed: int, departure_time: Optional[str]) -> List[Dict]:
        points = [p for p in [departure, *(waypoints or []), destination] if p]
        coords = {}
        for icao in points:
            info = self.get_airport_coordinates(icao)
            if info: coords[icao] = info
        if len(coords) < 2:
            raise UserInputError("Unable to determine airport coordinates for given route.")

        current_time = self._parse_departure_time_or_now(departure_time)
        segments = []
        keys = list(coords.keys())
        for i in range(len(keys)-1):
            a, b = keys[i], keys[i+1]
            ca, cb = coords[a], coords[b]
            dist = haversine_nm(ca['lat'], ca['lon'], cb['lat'], cb['lon'])
            t_hours = dist / max(1, cruise_speed)
            end = current_time + timedelta(hours=t_hours)
            segments.append({
                'from': a, 'to': b,
                'from_coords': ca, 'to_coords': cb,
                'distance_nm': dist, 'flight_time_hours': t_hours,
                'start_time': current_time, 'end_time': end,
                'midpoint_lat': (ca['lat']+cb['lat'])/2, 'midpoint_lon': (ca['lon']+cb['lon'])/2
            })
            current_time = end
        return segments

    def get_comprehensive_weather(self, flight_segments: List[Dict]) -> Dict:
        bbox = self._bbox_from_segments(flight_segments) or Settings.DEFAULT_BBOX
        airports = sorted(set([seg['from'] for seg in flight_segments] + [seg['to'] for seg in flight_segments]))
        departure_time = flight_segments[0]['start_time'] if flight_segments else now_utc()

        result: Dict = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=Settings.MAX_WORKERS) as ex:
            futures = {
                'metars': ex.submit(self._get_historical_metars, bbox, departure_time),
                'tafs': ex.submit(self.client.taf, bbox=bbox),
                'pireps': ex.submit(self._get_historical_pireps, bbox, departure_time),
                'sigmets': ex.submit(self.client.airsigmet),
                'gairmets': ex.submit(self.client.gairmet),
                'cwas': ex.submit(self.client.cwa),
                'notams': ex.submit(self._generate_time_based_notams, airports, departure_time)
            }
            for k,f in futures.items():
                try: result[k] = f.result(timeout=15)
                except Exception as e:
                    logging.error(f"Error fetching {k}: {e}")
                    result[k] = []
        return result

    def create_timeline_analysis(self, flight_segments: List[Dict], weather_data: Dict) -> List[Dict]:
        timeline: List[Dict] = []
        for seg in flight_segments:
            duration = seg['flight_time_hours']
            n = max(1, int(duration * 4))  # 15-min bins
            step = duration / n
            for i in range(n):
                t0 = seg['start_time'] + timedelta(hours=i*step)
                t1 = seg['start_time'] + timedelta(hours=(i+1)*step)
                prog = (i+0.5)/n
                lat = seg['from_coords']['lat'] + prog*(seg['to_coords']['lat']-seg['from_coords']['lat'])
                lon = seg['from_coords']['lon'] + prog*(seg['to_coords']['lon']-seg['from_coords']['lon'])
                cond = self._conditions_for(lat, lon, t0, weather_data)
                timeline.append({
                    'start_time': t0.isoformat(), 'end_time': t1.isoformat(),
                    'start_time_local': t0.strftime("%H:%M UTC"), 'end_time_local': t1.strftime("%H:%M UTC"),
                    'location_description': self._location_desc(seg, prog),
                    'lat': lat, 'lon': lon,
                    'conditions': cond, 'severity': cond['severity'],
                    'flight_segment': f"{seg['from']} -> {seg['to']}",
                    'wind_speed': cond.get('wind_speed',0), 'wind_gust': cond.get('wind_gust',0),
                    'visibility': cond.get('visibility',10), 'temperature': cond.get('temperature',15)
                })
        return timeline

    # === Internals (mostly your original logic, reorganized) ===
    def get_airport_coordinates(self, icao: str) -> Optional[Dict]:
        try:
            data = self.client.stationinfo(ids=icao)
            if data:
                d = data[0]
                return {'lat': d.get('lat',0.0), 'lon': d.get('lon',0.0), 'name': d.get('site', icao)}
        except Exception as e:
            logging.error(f"stationinfo {icao} failed: {e}")
        return None

    def _parse_departure_time_or_now(self, departure_time: Optional[str]) -> datetime:
        if not departure_time:
            return now_utc()
        try:
            # Accept ISO, ISO with Z, or naive ISO (assume UTC)
            dt = datetime.fromisoformat(departure_time.replace('Z', '+00:00')) if 'Z' in departure_time else datetime.fromisoformat(departure_time)
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
            # Clamp (15 days past, 4 hours future)
            from utils.timeutils import clamp_past_future_window
            clamp_past_future_window(dt, max_past_days=15, max_future_hours=4)
            return dt
        except Exception as e:
            raise UserInputError(f"Invalid departure_time: {departure_time}. Error: {e}")

    def _bbox_from_segments(self, segments: List[Dict]) -> Optional[str]:
        if not segments: return None
        lats, lons = [], []
        for s in segments:
            lats += [s['from_coords']['lat'], s['to_coords']['lat']]
            lons += [s['from_coords']['lon'], s['to_coords']['lon']]
        buf = 2.0
        return f"{min(lats)-buf},{min(lons)-buf},{max(lats)+buf},{max(lons)+buf}"

    def _get_historical_metars(self, bbox: str, dt: datetime) -> List[Dict]:
        params = {'bbox': bbox}
        n = now_utc()
        if dt < n - timedelta(hours=3):
            params['startTime'] = (dt - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
            params['endTime']   = (dt + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        else:
            params['hours'] = 3
        data = self.client.metar(**params)
        enhanced = []
        for m in data:
            m['category'] = self._categorize(m)
            if m.get('rawOb'):
                m['natural_language'] = self.nlp.decode_metar_to_natural_language(m['rawOb'])
            enhanced.append(m)
        return enhanced

    def _get_historical_pireps(self, bbox: str, dt: datetime) -> List[Dict]:
        params = {'bbox': bbox}
        n = now_utc()
        if dt < n - timedelta(hours=6):
            params['startTime'] = (dt - timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M:%SZ')
            params['endTime']   = (dt + timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M:%SZ')
        else:
            params['age'] = 6
        return self.client.pirep(**params)

    def _categorize(self, metar: dict) -> str:
        try:
            visibility = metar.get('visib', 10)
            wspd = metar.get('wspd', 0) or 0
            wgst = metar.get('wgst', 0) or 0
            wx = metar.get('wxString', '') or ''
            clouds = metar.get('clouds', [])

            # visibility normalization
            if isinstance(visibility, str):
                if 'SM' in visibility:
                    nums = re.findall(r'[\d.]+', visibility)
                    vis_val = float(nums[0]) if nums else 10
                elif visibility in ('9999','CAVOK'):
                    vis_val = 10
                elif visibility.isdigit():
                    vis_val = float(visibility) / 1609
                else:
                    vis_val = 10
            else:
                vis_val = float(visibility) if visibility else 10

            # ceiling
            ceiling = None
            for c in clouds:
                if c.get('cover') in ['BKN','OVC','VV']:
                    base = c.get('base', 0)
                    if ceiling is None or base < ceiling:
                        ceiling = base

            severe_wx = ['+TS','+TSRA','+TSSN','+TSPL','+TSGR','TS','TSRA','FC','SQ','+GR','GR']
            if any(code in wx for code in severe_wx): return "Severe"
            if wgst and wgst >= 35: return "Severe"
            if vis_val < 1: return "Severe"
            if ceiling and ceiling < 500: return "Severe"

            sig_wx = ['SN','BLSN','+SN','RA','+RA','DZ','FZ','IC','PL','FG','FZFG']
            if any(code in wx for code in sig_wx): return "Significant"
            if wspd >= 25 or (wgst and wgst >= 25): return "Significant"
            if vis_val < 3: return "Significant"
            if ceiling and ceiling < 1000: return "Significant"
            return "Clear"
        except Exception:
            return "Clear"

    def _conditions_for(self, lat: float, lon: float, t: datetime, weather_data: Dict) -> Dict:
        nearest = self._nearest(lat, lon, weather_data.get('metars', []))
        # If near "now", use nearest; otherwise simulate
        if nearest and abs((t - now_utc()).total_seconds()) < 3*3600:
            sim = nearest
        else:
            sim = self._simulate(lat, lon, t, nearest)
        sim['category'] = self._categorize(sim)

        hazards = self._hazards(sim) + self._notam_warnings(weather_data.get('notams', []))
        base = sim.get('category','Clear')
        cond = self._describe(sim)
        if hazards:
            if any(k in " ".join(hazards) for k in ["TFR","RESTRICTION","CLOSED","SIGMET"]):
                severity = "Severe"; cond = f"{cond} | Advisory conditions in area"
            else:
                severity = "Significant" if base == "Clear" else base
                cond = f"{cond} | Minor advisories"
        else:
            severity = base

        vis_val = self._visibility_value(sim.get('visib', 10))
        nearest_station = (nearest or {}).get('icaoId') or 'Unknown'

        return {
            'severity': severity,
            'condition': cond,
            'description': f"Current: {cond}",
            'hazards': hazards[:2],
            'pirep_count': 0,  # hook: you can count nearby PIREPs here if desired
            'nearest_station': nearest_station,
            'natural_language': sim.get('natural_language',''),
            'wind_speed': sim.get('wspd',0) or 0,
            'wind_gust': sim.get('wgst',0) or 0,
            'visibility': vis_val,
            'temperature': sim.get('temp',15) or 15
        }

    def _nearest(self, lat: float, lon: float, items: List[Dict]) -> Optional[Dict]:
        best, best_d = None, float('inf')
        for it in items:
            try:
                la, lo = float(it.get('lat')), float(it.get('lon'))
            except (TypeError, ValueError):
                continue
            d = haversine_nm(lat, lon, la, lo)
            if d < best_d and d < Settings.NEAREST_METAR_RADIUS_NM:
                best, best_d = it, d
        return best

    def _simulate(self, lat: float, lon: float, target: datetime, current: Optional[Dict]) -> Dict:
        seed = int(hashlib.md5(f"{lat:.2f}_{lon:.2f}_{target.strftime('%Y%m%d%H')}".encode()).hexdigest()[:8], 16)
        random.seed(seed)
        base_wind = (current or {}).get('wspd', random.uniform(5,20))
        hours_diff = (target - now_utc()).total_seconds()/3600
        cycle = math.sin(hours_diff/6 * math.pi) * 0.5 + random.uniform(-0.3, 0.3)
        month = target.month
        seasonal = math.sin((month - 3) * math.pi / 6) * 0.3
        variation = cycle + seasonal
        wind = max(0, base_wind + random.uniform(-5,5))
        if variation > 0.4:
            wx = random.choice(['TSRA','SN','RA','FG'])
            vis = random.uniform(0.5,2)
            ceiling = random.choice([200,400,800])
            gusts = wind + random.uniform(10,20)
        elif variation > 0.1:
            wx = random.choice(['','BKN','SCT','-RA','HZ'])
            vis = random.uniform(3,6)
            ceiling = random.choice([1000,1500,2000])
            gusts = wind + random.uniform(5,15) if random.random()>0.7 else None
        else:
            wx, vis, ceiling, gusts = '', 10, None, None
        return {
            'wspd': int(wind), 'wgst': int(gusts) if gusts else None,
            'wdir': random.randint(180,360), 'visib': vis, 'wxString': wx,
            'clouds': [{'cover':'BKN','base': ceiling}] if ceiling else [],
            'lat': lat, 'lon': lon, 'icaoId': 'SIMULATED', 'reportTime': target.isoformat()
        }

    def _hazards(self, weather: Dict) -> List[str]:
        h = []
        wx = weather.get('wxString','')
        if 'TS' in wx: h.append("SIGMET: Thunderstorm activity")
        elif 'SN' in wx: h.append("G-AIRMET: Snow and icing conditions")
        elif 'FG' in wx: h.append("G-AIRMET: Low visibility in fog")
        if (weather.get('wspd',0) or 0) > 30: h.append("CWA: Strong surface winds")
        return h

    def _notam_warnings(self, notams: List[Dict]) -> List[str]:
        w = []
        for n in notams:
            sev, text, apt = n.get('severity',''), n.get('text',''), n.get('airport','')
            if sev == 'Severe':
                if 'TFR' in text or 'RESTRICTION' in text: w.append(f"NOTAM {apt}: Airspace restriction active")
                elif 'CLOSED' in text and 'RWY' in text: w.append(f"NOTAM {apt}: Runway closure")
        return w

    def _describe(self, m: Dict) -> str:
        parts = []
        wx = m.get('wxString','')
        parts.append(f"Weather: {wx}" if wx else "Weather: Clear")
        vis = m.get('visib')
        if vis is not None:
            parts.append(f"Visibility: {vis}SM" if isinstance(vis,(int,float)) else f"Visibility: {vis}")
        if m.get('wdir') and m.get('wspd') is not None:
            if m.get('wgst'): parts.append(f"Wind: {m['wdir']}°/{m['wspd']}G{m['wgst']}kt")
            else: parts.append(f"Wind: {m['wdir']}°/{m['wspd']}kt")
        return " | ".join(parts) if parts else "Clear conditions"

    def _visibility_value(self, v) -> float:
        if isinstance(v, str):
            if 'SM' in v:
                nums = re.findall(r'[\d.]+', v)
                return float(nums[0]) if nums else 10
            if v in ('9999','CAVOK'): return 10
            if v.isdigit(): return float(v)/1609
            return 10
        return float(v) if v else 10
    
    def _location_desc(self, segment: Dict, progress: float) -> str:
        """Human-readable location description along the segment."""
        try:
            if progress < 0.3:
                return f"Departing {segment['from']}"
            elif progress > 0.7:
                return f"Approaching {segment['to']}"
            else:
                return f"En route {segment['from']} -> {segment['to']}"
        except Exception:
            # Fallback if keys aren't present
            return "En route"

    def _generate_time_based_notams(self, airports: List[str], ref_time: datetime) -> List[Dict]:
        # same behavior as your sample generator
        runways = ['09/27','18/36','04/22','13/31','01/19']
        taxiways = ['A','B','C','D','E']
        templates = [
            {'text':'RWY {rwy} CLOSED FOR MAINTENANCE','classification':'Runway','severity':'Significant'},
            {'text':'ILS RWY {rwy} OUT OF SERVICE','classification':'Navigation Aid','severity':'Significant'},
            {'text':'CONSTRUCTION ACTIVITY NEAR TERMINAL','classification':'Airport','severity':'Clear'},
            {'text':'TEMPORARY FLIGHT RESTRICTION IN EFFECT','classification':'Airspace','severity':'Severe'},
            {'text':'TAXIWAY {twy} PARTIALLY CLOSED','classification':'Taxiway','severity':'Clear'}
        ]
        out = []
        for i, apt in enumerate(airports[:4]):
            seed = int(hashlib.md5(f"{apt}_{ref_time.strftime('%Y%m%d')}".encode()).hexdigest()[:8],16)
            random.seed(seed)
            t = templates[i % len(templates)]
            rwy = runways[i % len(runways)]
            twy = taxiways[i % len(taxiways)]
            start_offset = random.randint(-48,-2)
            duration = random.randint(6,72)
            start = ref_time + timedelta(hours=start_offset)
            end = start + timedelta(hours=duration)
            if end > ref_time:
                text = t['text'].format(rwy=rwy, twy=twy)
                out.append({
                    'airport': apt, 'notam_id': f"A{1000+seed%9999}/24", 'text': text,
                    'start_time': start.isoformat(), 'end_time': end.isoformat(),
                    'classification': t['classification'], 'severity': t['severity'],
                    'created': (start - timedelta(hours=random.randint(1,24))).isoformat(),
                    'source': 'AVWX API (Time-Based)'
                })
        return out
