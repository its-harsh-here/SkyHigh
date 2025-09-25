from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import re
from datetime import datetime, timezone, timedelta
import logging
import math
import concurrent.futures

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

class WeatherProcessor:
    def __init__(self):
        self.base_url = "https://aviationweather.gov/api/data"
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'PilotWeatherBriefingApp/1.0'})

    def categorize_weather(self, metar_data: dict) -> str:
        try:
            visibility = metar_data.get('visib', 10)
            wind_speed = metar_data.get('wspd', 0) or 0
            wind_gust = metar_data.get('wgst', 0) or 0
            weather_string = metar_data.get('wxString', '') or ''
            clouds = metar_data.get('clouds', [])
            if isinstance(visibility, str):
                if 'SM' in visibility:
                    vis_match = re.findall(r'[\d.]+', visibility)
                    vis_val = float(vis_match[0]) if vis_match else 10
                elif visibility == '9999' or visibility == 'CAVOK':
                    vis_val = 10
                elif visibility.isdigit():
                    vis_val = float(visibility) / 1609
                else:
                    vis_val = 10
            else:
                vis_val = float(visibility) if visibility else 10
            ceiling = None
            for cloud in clouds:
                if cloud.get('cover') in ['BKN', 'OVC', 'VV']:
                    cloud_base = cloud.get('base', 0)
                    if ceiling is None or cloud_base < ceiling:
                        ceiling = cloud_base
            severe_weather = ['+TS', '+TSRA', '+TSSN', '+TSPL', '+TSGR', 'TS', 'TSRA', 'FC', 'SQ', '+GR', 'GR']
            if any(wx in weather_string for wx in severe_weather):
                return "Severe"
            if wind_gust and wind_gust >= 35:
                return "Severe"
            if vis_val < 1:
                return "Severe"
            if ceiling and ceiling < 500:
                return "Severe"
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

    def calculate_flight_path(self, departure, destination, waypoints=None, cruise_speed=450, departure_time=None):
        all_points = [departure] + (waypoints or []) + [destination]
        coordinates = {}
        for icao in all_points:
            coords = self.get_airport_coordinates(icao)
            if coords:
                coordinates[icao] = coords
        if len(coordinates) < 2:
            return []
        # --- Parse user-provided departure_time strictly and check for future dates ---
        if departure_time:
            try:
                # Accepts ISO 8601, e.g. '2025-09-26T02:00:00Z' or '2025-09-26T02:00:00+00:00'
                if departure_time.endswith('Z'):
                    departure_time = departure_time.replace('Z', '+00:00')
                current_time = datetime.fromisoformat(departure_time)
                now_utc = datetime.now(timezone.utc)
                if current_time > now_utc:
                    raise ValueError('Departure time cannot be in the future.')
            except Exception:
                raise ValueError('Invalid departure_time format. Use ISO 8601 (e.g. 2025-09-26T02:00:00Z) and not a future date.')
        else:
            current_time = datetime.now(timezone.utc)
        path_points = list(coordinates.keys())
        flight_segments = []
        for i in range(len(path_points) - 1):
            from_icao = path_points[i]
            to_icao = path_points[i + 1]
            from_coords = coordinates[from_icao]
            to_coords = coordinates[to_icao]
            distance = self.haversine_distance(from_coords['lat'], from_coords['lon'], to_coords['lat'], to_coords['lon'])
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

    def get_airport_coordinates(self, icao: str):
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

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        R = 3440.065
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c

    def get_comprehensive_weather(self, bbox=None, flight_segments=None, airports=None):
        weather_data = {}
        if not bbox and flight_segments:
            lats = []
            lons = []
            for segment in flight_segments:
                lats.extend([segment['from_coords']['lat'], segment['to_coords']['lat']])
                lons.extend([segment['from_coords']['lon'], segment['to_coords']['lon']])
            buffer = 2.0
            bbox = f"{min(lats)-buffer},{min(lons)-buffer},{max(lats)+buffer},{max(lons)+buffer}"
        if not bbox:
            bbox = "25,-125,50,-65"
        if not airports and flight_segments:
            airports = []
            for segment in flight_segments:
                airports.extend([segment['from'], segment['to']])
            airports = list(set(airports))
        with concurrent.futures.ThreadPoolExecutor(max_workers=7) as executor:
            futures = {
                'metars': executor.submit(self.get_metars_by_bbox, bbox),
                'tafs': executor.submit(self.get_tafs_by_bbox, bbox),
                'pireps': executor.submit(self.get_pireps_by_bbox, bbox),
                'sigmets': executor.submit(self.get_sigmets),
                'gairmets': executor.submit(self.get_gairmets),
                'cwas': executor.submit(self.get_cwas),
                'notams': executor.submit(self.get_notams, airports or [])
            }
            for product_type, future in futures.items():
                try:
                    weather_data[product_type] = future.result(timeout=15)
                except Exception as e:
                    logging.error(f"Error fetching {product_type}: {e}")
                    weather_data[product_type] = []
        return weather_data

    def get_notams(self, airports):
        sample_notams = []
        notam_templates = [
            {'text': 'RWY {rwy} CLOSED FOR MAINTENANCE', 'classification': 'Runway', 'severity': 'Significant'},
            {'text': 'ILS RWY {rwy} OUT OF SERVICE', 'classification': 'Navigation Aid', 'severity': 'Significant'},
            {'text': 'CONSTRUCTION ACTIVITY NEAR TERMINAL', 'classification': 'Airport', 'severity': 'Clear'},
            {'text': 'TEMPORARY FLIGHT RESTRICTION IN EFFECT', 'classification': 'Airspace', 'severity': 'Severe'},
            {'text': 'TAXIWAY {twy} PARTIALLY CLOSED', 'classification': 'Taxiway', 'severity': 'Clear'}
        ]
        runways = ['09/27', '18/36', '04/22', '13/31', '01/19']
        taxiways = ['A', 'B', 'C', 'D', 'E']
        current_time = datetime.now(timezone.utc)
        for i, airport in enumerate(airports[:4]):
            template = notam_templates[i % len(notam_templates)]
            runway = runways[i % len(runways)]
            taxiway = taxiways[i % len(taxiways)]
            start_time = current_time - timedelta(hours=i*2)
            end_time = current_time + timedelta(days=1+i, hours=i*3)
            notam_text = template['text'].format(rwy=runway, twy=taxiway)
            sample_notams.append({
                'airport': airport,
                'notam_id': f"A{1000+i}/24",
                'text': notam_text,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'classification': template['classification'],
                'severity': template['severity'],
                'created': start_time.isoformat(),
                'source': 'Demo Data'
            })
        return sample_notams

    def get_metars_by_bbox(self, bbox):
        try:
            url = f"{self.base_url}/metar"
            params = {'bbox': bbox, 'format': 'json', 'hours': 3}
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return [self.enhance_metar(metar) for metar in data]
        except Exception as e:
            logging.error(f"Error fetching METARs: {e}")
        return []

    def get_tafs_by_bbox(self, bbox):
        try:
            url = f"{self.base_url}/taf"
            params = {'bbox': bbox, 'format': 'json'}
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logging.error(f"Error fetching TAFs: {e}")
        return []

    def get_pireps_by_bbox(self, bbox):
        try:
            url = f"{self.base_url}/pirep"
            params = {'bbox': bbox, 'format': 'json', 'age': 6}
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logging.error(f"Error fetching PIREPs: {e}")
        return []

    def get_sigmets(self):
        try:
            url = f"{self.base_url}/airsigmet"
            params = {'format': 'json'}
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logging.error(f"Error fetching SIGMETs: {e}")
        return []

    def get_gairmets(self):
        try:
            url = f"{self.base_url}/gairmet"
            params = {'format': 'json'}
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logging.error(f"Error fetching G-AIRMETs: {e}")
        return []

    def get_cwas(self):
        try:
            url = f"{self.base_url}/cwa"
            params = {'format': 'json'}
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logging.error(f"Error fetching CWAs: {e}")
        return []

    def enhance_metar(self, metar):
        metar['category'] = self.categorize_weather(metar)
        return metar

    def create_timeline_analysis(self, flight_segments, weather_data):
        timeline = []
        for segment in flight_segments:
            segment_duration = segment['flight_time_hours']
            num_intervals = max(1, int(segment_duration * 4))
            interval_duration = segment_duration / num_intervals
            for i in range(num_intervals):
                interval_start = segment['start_time'] + timedelta(hours=i * interval_duration)
                interval_end = segment['start_time'] + timedelta(hours=(i + 1) * interval_duration)
                progress = (i + 0.5) / num_intervals
                lat = segment['from_coords']['lat'] + progress * (segment['to_coords']['lat'] - segment['from_coords']['lat'])
                lon = segment['from_coords']['lon'] + progress * (segment['to_coords']['lon'] - segment['from_coords']['lon'])
                conditions = self.get_conditions_for_location_time(lat, lon, interval_start, weather_data)
                timeline.append({
                    'start_time': interval_start.isoformat(),
                    'end_time': interval_end.isoformat(),
                    'start_time_local': self.format_time_for_display(interval_start),
                    'end_time_local': self.format_time_for_display(interval_end),
                    'location_description': self.get_location_description(lat, lon, segment, progress),
                    'lat': lat,
                    'lon': lon,
                    'conditions': conditions,
                    'severity': conditions['severity'],
                    'flight_segment': f"{segment['from']} → {segment['to']}"
                })
        return timeline

    def get_conditions_for_location_time(self, lat, lon, time, weather_data):
        nearest_metar = self.find_nearest_weather_data(lat, lon, weather_data.get('metars', []))
        pirep_reports = self.get_pireps_near_location(lat, lon, weather_data.get('pireps', []))
        hazards = self.check_hazards_for_location(lat, lon, weather_data)
        notam_warnings = self.check_notams_for_location(lat, lon, weather_data.get('notams', []))
        all_hazards = hazards + notam_warnings
        if nearest_metar:
            base_severity = nearest_metar.get('category', 'Clear')
            condition = self.get_weather_description(nearest_metar)
        else:
            base_severity = "Clear"
            condition = "No significant weather reported"
        if all_hazards:
            if any("TFR" in h or "CLOSED" in h or "SIGMET" in h for h in all_hazards):
                severity = "Severe"
                condition = f"{condition} | Advisory conditions in area"
            else:
                severity = "Significant" if base_severity == "Clear" else base_severity
                condition = f"{condition} | Minor advisories"
        else:
            severity = base_severity
        return {
            'severity': severity,
            'condition': condition,
            'description': self.create_detailed_description(nearest_metar, pirep_reports, all_hazards),
            'hazards': all_hazards,
            'pirep_count': len(pirep_reports),
            'nearest_station': nearest_metar.get('icaoId') if nearest_metar else None
        }

    def check_notams_for_location(self, lat, lon, notams):
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

    def find_nearest_weather_data(self, lat, lon, weather_list):
        nearest = None
        min_distance = float('inf')
        for weather in weather_list:
            w_lat = weather.get('lat', 0)
            w_lon = weather.get('lon', 0)
            if w_lat and w_lon:
                distance = self.haversine_distance(lat, lon, w_lat, w_lon)
                if distance < min_distance and distance < 100:
                    min_distance = distance
                    nearest = weather
        return nearest

    def get_pireps_near_location(self, lat, lon, pireps):
        nearby_pireps = []
        for pirep in pireps:
            p_lat = pirep.get('lat', 0)
            p_lon = pirep.get('lon', 0)
            if p_lat and p_lon:
                distance = self.haversine_distance(lat, lon, p_lat, p_lon)
                if distance < 50:
                    nearby_pireps.append(pirep)
        return nearby_pireps

    def check_hazards_for_location(self, lat, lon, weather_data):
        hazards = []
        sigmets = weather_data.get('sigmets', [])
        gairmets = weather_data.get('gairmets', [])
        cwas = weather_data.get('cwas', [])
        if sigmets and len(sigmets) > 0:
            relevant_sigmets = []
            for sigmet in sigmets:
                if sigmet.get('lat') and sigmet.get('lon'):
                    distance = self.haversine_distance(lat, lon, sigmet['lat'], sigmet['lon'])
                    if distance < 200:
                        relevant_sigmets.append(sigmet)
            if relevant_sigmets:
                hazards.append("SIGMET: Hazardous weather advisory")
        if gairmets and len(gairmets) > 0:
            relevant_gairmets = []
            for gairmet in gairmets:
                if gairmet.get('lat') and gairmet.get('lon'):
                    distance = self.haversine_distance(lat, lon, gairmet['lat'], gairmet['lon'])
                    if distance < 100:
                        relevant_gairmets.append(gairmet)
            if relevant_gairmets:
                hazards.append("G-AIRMET: Moderate weather advisory")
        if cwas and len(cwas) > 0:
            relevant_cwas = []
            for cwa in cwas:
                if cwa.get('lat') and cwa.get('lon'):
                    distance = self.haversine_distance(lat, lon, cwa['lat'], cwa['lon'])
                    if distance < 150:
                        relevant_cwas.append(cwa)
            if relevant_cwas:
                hazards.append("CWA: Center weather advisory")
        return hazards[:2]

    def get_weather_description(self, metar):
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
            conditions.append(f"Visibility: {visibility}")
        wind_dir = metar.get('wdir')
        wind_speed = metar.get('wspd')
        if wind_dir and wind_speed:
            wind_gust = metar.get('wgst')
            if wind_gust:
                conditions.append(f"Wind: {wind_dir}°/{wind_speed}G{wind_gust}kt")
            else:
                conditions.append(f"Wind: {wind_dir}°/{wind_speed}kt")
        return " | ".join(conditions) if conditions else "Clear conditions"

    def create_detailed_description(self, metar, pireps, hazards):
        description_parts = []
        if metar:
            description_parts.append(f"Current: {self.get_weather_description(metar)}")
        if pireps:
            description_parts.append(f"{len(pireps)} pilot report(s) in area")
        if hazards:
            description_parts.extend(hazards)
        return " | ".join(description_parts) if description_parts else "No significant weather reported"

    def get_location_description(self, lat, lon, segment, progress):
        if progress < 0.3:
            return f"Departing {segment['from']}"
        elif progress > 0.7:
            return f"Approaching {segment['to']}"
        else:
            return f"En route {segment['from']} → {segment['to']}"

    def format_time_for_display(self, dt):
        return dt.strftime("%H:%M UTC")

weather_processor = WeatherProcessor()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

@app.route('/api/enhanced-flight-plan', methods=['POST'])
def enhanced_flight_plan():
    try:
        data = request.get_json()
        departure = data.get('departure', '').upper()
        destination = data.get('destination', '').upper()
        waypoints = [wp.strip().upper() for wp in data.get('waypoints', []) if wp.strip()]
        cruise_speed = int(data.get('cruise_speed', 450))
        departure_time = data.get('departure_time')
        if not departure or not destination:
            return jsonify({'error': 'Departure and destination required'}), 400
        try:
            flight_segments = weather_processor.calculate_flight_path(
                departure, destination, waypoints, cruise_speed, departure_time
            )
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        if not flight_segments:
            return jsonify({'error': 'Unable to calculate flight path'}), 400
        all_airports = [departure, destination] + waypoints
        weather_data = weather_processor.get_comprehensive_weather(
            flight_segments=flight_segments,
            airports=all_airports
        )
        timeline = weather_processor.create_timeline_analysis(flight_segments, weather_data)
        severities = [item['severity'] for item in timeline]
        overall_severity = 'Clear'
        if 'Severe' in severities:
            overall_severity = 'Severe'
        elif 'Significant' in severities:
            overall_severity = 'Significant'
        return jsonify({
            'route': {
                'departure': departure,
                'destination': destination,
                'waypoints': waypoints,
                'cruise_speed': cruise_speed,
                'total_distance': sum(s['distance_nm'] for s in flight_segments),
                'total_flight_time': sum(s['flight_time_hours'] for s in flight_segments),
                'overall_severity': overall_severity
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
            'notams': weather_data.get('notams', [])
        })
    except Exception as e:
        logging.error(f"Error in enhanced flight plan: {e}")
        return jsonify({'error': f'Processing error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
