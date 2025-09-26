# services/nlp_service.py
import logging, re
from typing import Dict, List

class SimpleNLPProcessor:
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
            'RA': 'rain','SN':'snow','FG':'fog','BR':'mist','TS':'thunderstorm',
            'DZ':'drizzle','IC':'ice crystals','PL':'ice pellets','GR':'hail',
            '+':'heavy','-':'light'
        }

    def decode_metar_to_natural_language(self, metar_text: str) -> str:
        try:
            decoded_parts: List[str] = []

            airport = re.search(self.metar_patterns['airport'], metar_text)
            if airport: decoded_parts.append(f"Airport: {airport.group(1)}")

            t = re.search(self.metar_patterns['time'], metar_text)
            if t:
                time_str = t.group(1)
                decoded_parts.append(f"Observed on day {time_str[:2]} at {time_str[2:4]}:{time_str[4:6]} UTC")

            w = re.search(self.metar_patterns['wind'], metar_text)
            if w:
                direction, speed, gust = w.group(1), w.group(2), w.group(3)
                msg = f"Wind from {direction}° at {speed} kt"
                if gust: msg += f" gusting {gust[1:]} kt"
                decoded_parts.append(msg)

            vis = re.search(self.metar_patterns['visibility'], metar_text)
            if vis:
                if vis.group(1): decoded_parts.append(f"Visibility {vis.group(1)} SM")
                elif vis.group(2):
                    vm = int(vis.group(2))
                    decoded_parts.append("Visibility >10 km" if vm >= 9999 else f"Visibility {vm} m")

            wxs = re.findall(self.metar_patterns['weather'], metar_text)
            if wxs:
                conditions = []
                for m in wxs:
                    for code, desc in self.weather_descriptions.items():
                        if code in m:
                            conditions.append(desc)
                if conditions:
                    decoded_parts.append(f"Weather: {', '.join(sorted(set(conditions)))}")

            clouds = re.findall(self.metar_patterns['clouds'], metar_text)
            if clouds:
                map_cov = {'FEW': 'few', 'SCT': 'scattered', 'BKN': 'broken', 'OVC':'overcast'}
                parts = [f"{map_cov[c]} at {int(h)*100} ft" for c,h in clouds]
                decoded_parts.append(f"Clouds: {', '.join(parts)}")

            temp = re.search(self.metar_patterns['temperature'], metar_text)
            if temp:
                t, d = temp.group(1).replace('M','-'), temp.group(2).replace('M','-')
                decoded_parts.append(f"Temperature {t}°C, dew point {d}°C")

            return ". ".join(decoded_parts) + "." if decoded_parts else f"Weather conditions reported: {metar_text}"
        except Exception as e:
            logging.error(f"Error decoding METAR: {e}")
            return f"Weather conditions reported: {metar_text}"

    def summarize_weather_briefing(self, weather_data: Dict) -> str:
        try:
            parts = []
            mets = weather_data.get('metars', [])
            if mets:
                total = len(mets)
                clear = sum(1 for m in mets if m.get('category') == 'Clear')
                sig = sum(1 for m in mets if m.get('category') == 'Significant')
                sev = sum(1 for m in mets if m.get('category') == 'Severe')
                if sev > 0: parts.append(f"WEATHER ALERT: {sev} stations report severe conditions.")
                elif sig > total * 0.3: parts.append(f"CAUTION: {sig}/{total} stations significant weather.")
                else: parts.append(f"Generally favorable: {clear} clear stations.")
            nts = weather_data.get('notams', [])
            if nts:
                severe_notams = [n for n in nts if n.get('severity') == 'Severe']
                parts.append(f"CRITICAL: {len(severe_notams)} severe NOTAMs." if severe_notams
                             else f"{len(nts)} NOTAMs—review impact.")
            prs = weather_data.get('pireps', [])
            if prs: parts.append(f"{len(prs)} pilot reports available.")
            sigmets = weather_data.get('sigmets', [])
            gairmets = weather_data.get('gairmets', [])
            if sigmets or gairmets: parts.append(f"{len(sigmets)+len(gairmets)} weather advisories active.")
            return " ".join(parts) if parts else "Weather briefing: minimal data."
        except Exception as e:
            logging.error(f"Error creating weather summary: {e}")
            return "Weather briefing summary unavailable."

    def extract_flight_plan_from_text(self, text: str) -> Dict:
        # (unchanged logic from your code, just moved here)
        try:
            fp = {'departure': None,'destination': None,'waypoints': [],'cruise_speed': 450,'departure_time': None}
            icao_pattern = r'\b[A-Z]{4}\b'
            airports = re.findall(icao_pattern, text.upper())
            if len(airports) >= 2:
                fp['departure'], fp['destination'] = airports[0], airports[-1]
                if len(airports) > 2: fp['waypoints'] = airports[1:-1]
            for p in [r'(\d{3,4})\s*(?:knots?|kts?|kt)', r'(?:speed|cruise)\s*(?:of\s*)?(\d{3,4})', r'(\d{3,4})\s*mph']:
                m = re.search(p, text.lower())
                if m: fp['cruise_speed'] = int(m.group(1)); break
            for p in [r'(?:at\s*)?(\d{1,2}):(\d{2})\s*(?:am|pm|utc|z)?', r'(?:at\s*)?(\d{4})z',
                      r'(?:at\s*)?(\d{1,2})\s*(?:am|pm|o\'?clock)', r'(?:tomorrow|today|yesterday)\s*(?:at\s*)?(\d{1,2}):?(\d{2})?']:
                m = re.search(p, text.lower())
                if m: fp['departure_time'] = m.group(0); break
            return fp
        except Exception:
            return fp

    def generate_risk_assessment(self, timeline: List[Dict]) -> Dict:
        try:
            scores = {'Clear': 1, 'Significant': 3, 'Severe': 5}
            total, max_total, sev_cnt, sig_cnt = 0, len(timeline)*5, 0, 0
            for seg in timeline:
                s = scores.get(seg.get('severity','Clear'), 1)
                total += s
                if seg.get('severity') == 'Severe': sev_cnt += 1
                elif seg.get('severity') == 'Significant': sig_cnt += 1
            pct = (total/max_total)*100 if max_total else 0
            if pct >= 70: lvl, rec = "HIGH RISK","Consider postponing flight or alternate route"
            elif pct >= 40: lvl, rec = "MODERATE RISK","Monitor closely; prepare contingencies"
            else: lvl, rec = "LOW RISK","Conditions acceptable"
            return {'risk_level': lvl,'risk_percentage': round(pct,1),'recommendation': rec,
                    'severe_segments': sev_cnt,'significant_segments': sig_cnt,'total_segments': len(timeline)}
        except Exception:
            return {'risk_level':'UNKNOWN','risk_percentage':0,'recommendation':'Unable to assess',
                    'severe_segments':0,'significant_segments':0,'total_segments':0}
