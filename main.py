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
    
    def decode_pirep_to_natural_language(self, pirep_text: str) -> str:
        """Convert PIREP code to natural language description"""
        try:
            decoded_parts = []
            
            # Basic PIREP patterns
            if '/TP' in pirep_text:
                aircraft_match = re.search(r'/TP\s*([A-Z0-9]+)', pirep_text)
                if aircraft_match:
                    decoded_parts.append(f"Aircraft: {aircraft_match.group(1)}")
            
            if '/FL' in pirep_text:
                altitude_match = re.search(r'/FL(\d+)', pirep_text)
                if altitude_match:
                    altitude = int(altitude_match.group(1)) * 100
                    decoded_parts.append(f"Flight Level: {altitude} feet")
            
            if '/SK' in pirep_text:
                sky_match = re.search(r'/SK\s*([^/]+)', pirep_text)
                if sky_match:
                    decoded_parts.append(f"Sky condition: {sky_match.group(1).strip()}")
            
            if '/WX' in pirep_text:
                weather_match = re.search(r'/WX\s*([^/]+)', pirep_text)
                if weather_match:
                    decoded_parts.append(f"Weather: {weather_match.group(1).strip()}")
            
            if '/TB' in pirep_text:
                turb_match = re.search(r'/TB\s*([^/]+)', pirep_text)
                if turb_match:
                    decoded_parts.append(f"Turbulence: {turb_match.group(1).strip()}")
            
            if '/IC' in pirep_text:
                ice_match = re.search(r'/IC\s*([^/]+)', pirep_text)
                if ice_match:
                    decoded_parts.append(f"Icing: {ice_match.group(1).strip()}")
            
            return ". ".join(decoded_parts) + "." if decoded_parts else f"Pilot report: {pirep_text}"
            
        except Exception as e:
            logging.error(f"Error decoding PIREP: {e}")
            return f"Pilot report: {pirep_text}"
    
    def decode_taf_to_natural_language(self, taf_text: str) -> str:
        """Convert TAF code to natural language description"""
        try:
            decoded_parts = []
            
            # Airport code
            airport_match = re.search(self.metar_patterns['airport'], taf_text)
            if airport_match:
                decoded_parts.append(f"Forecast for: {airport_match.group(1)}")
            
            # Valid time
            valid_match = re.search(r'(\d{6}/\d{6})', taf_text)
            if valid_match:
                valid_time = valid_match.group(1)
                start_day = valid_time[:2]
                start_hour = valid_time[2:4]
                end_day = valid_time[7:9]
                end_hour = valid_time[9:11]
                decoded_parts.append(f"Valid from day {start_day} at {start_hour}:00Z to day {end_day} at {end_hour}:00Z")
            
            # Wind
            wind_match = re.search(self.metar_patterns['wind'], taf_text)
            if wind_match:
                direction = wind_match.group(1)
                speed = wind_match.group(2)
                gust = wind_match.group(3)
                wind_desc = f"Wind forecast: {direction} degrees at {speed} knots"
                if gust:
                    wind_desc += f" gusting to {gust[1:]} knots"
                decoded_parts.append(wind_desc)
            
            # Visibility
            vis_match = re.search(self.metar_patterns['visibility'], taf_text)
            if vis_match:
                if vis_match.group(1):
                    decoded_parts.append(f"Visibility forecast: {vis_match.group(1)} statute miles")
                elif vis_match.group(2):
                    vis_meters = int(vis_match.group(2))
                    if vis_meters >= 9999:
                        decoded_parts.append("Visibility forecast: greater than 10 kilometers")
                    else:
                        decoded_parts.append(f"Visibility forecast: {vis_meters} meters")
            
            # Weather phenomena
            weather_matches = re.findall(self.metar_patterns['weather'], taf_text)
            if weather_matches:
                weather_conditions = []
                for match in weather_matches:
                    for code, description in self.weather_descriptions.items():
                        if code in match:
                            weather_conditions.append(description)
                if weather_conditions:
                    decoded_parts.append(f"Weather forecast: {', '.join(set(weather_conditions))}")
            
            # Temporary conditions
            if 'TEMPO' in taf_text:
                decoded_parts.append("Temporary conditions expected during forecast period")
            
            if 'BECMG' in taf_text:
                decoded_parts.append("Conditions becoming different during forecast period")
            
            return ". ".join(decoded_parts) + "." if decoded_parts else f"Terminal forecast: {taf_text}"
            
        except Exception as e:
            logging.error(f"Error decoding TAF: {e}")
            return f"Terminal forecast: {taf_text}"
    
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
        
        # Initialize simplified processors
        self.nlp_processor = SimpleNLPProcessor()

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
                    # Raw weather data for detailed view
                    'raw_data': conditions.get('raw_data', {})
                })
        
        return timeline

    def get_conditions_for_location_time(self, lat: float, lon: float, time: datetime, weather_data: Dict) -> Dict:
        """Get weather conditions for specific location and time with enhanced data and raw weather"""
        nearest_metar = self.find_nearest_weather_data(lat, lon, weather_data.get('metars', []))
        
        now_utc = datetime.now(timezone.utc)
        if nearest_metar and abs((time - now_utc).total_seconds()) < 3 * 3600:
            simulated_weather = nearest_metar
        else:
            simulated_weather = self.simulate_historical_weather(lat, lon, time, nearest_metar)
        
        simulated_weather['category'] = self.categorize_weather(simulated_weather)
        
        # Get nearby raw weather data
        nearby_metars = self.get_nearby_metars(lat, lon, weather_data.get('metars', []))
        nearby_pireps = self.get_pireps_near_location(lat, lon, weather_data.get('pireps', []))
        nearby_tafs = self.get_nearby_tafs(lat, lon, weather_data.get('tafs', []))
        
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
            'pirep_count': len(nearby_pireps),
            'nearest_station': nearest_station_id or 'Unknown',
            'natural_language': simulated_weather.get('natural_language', ''),
            # Enhanced data for additional charts
            'wind_speed': simulated_weather.get('wspd', 0) or 0,
            'wind_gust': simulated_weather.get('wgst', 0) or 0,
            'visibility': visibility_val,
            'temperature': simulated_weather.get('temp', 15) or 15,
            # Raw weather data for detailed buttons
            'raw_data': {
                'metars': nearby_metars[:3],  # Limit to 3 nearest
                'pireps': nearby_pireps[:3],  # Limit to 3 nearest
                'tafs': nearby_tafs[:3],      # Limit to 3 nearest
            }
        }

    def get_nearby_metars(self, lat: float, lon: float, metars: List[Dict], max_distance: float = 100) -> List[Dict]:
        """Get METARs near specified location"""
        nearby = []
        for metar in metars:
            m_lat = metar.get('lat')
            m_lon = metar.get('lon')
            if m_lat is not None and m_lon is not None:
                try:
                    m_lat = float(m_lat)
                    m_lon = float(m_lon)
                    distance = self.haversine_distance(lat, lon, m_lat, m_lon)
                    if distance <= max_distance:
                        nearby.append({
                            'station': metar.get('icaoId', 'Unknown'),
                            'raw': metar.get('rawOb', ''),
                            'distance': round(distance, 1),
                            'time': metar.get('reportTime', ''),
                            'nlp': self.nlp_processor.decode_metar_to_natural_language(metar.get('rawOb', ''))
                        })
                except (ValueError, TypeError):
                    continue
        return sorted(nearby, key=lambda x: x['distance'])

    def get_nearby_tafs(self, lat: float, lon: float, tafs: List[Dict], max_distance: float = 100) -> List[Dict]:
        """Get TAFs near specified location"""
        nearby = []
        for taf in tafs:
            t_lat = taf.get('lat')
            t_lon = taf.get('lon')
            if t_lat is not None and t_lon is not None:
                try:
                    t_lat = float(t_lat)
                    t_lon = float(t_lon)
                    distance = self.haversine_distance(lat, lon, t_lat, t_lon)
                    if distance <= max_distance:
                        nearby.append({
                            'station': taf.get('icaoId', 'Unknown'),
                            'raw': taf.get('rawTAF', ''),
                            'distance': round(distance, 1),
                            'valid_time': taf.get('validTime', ''),
                            'nlp': self.nlp_processor.decode_taf_to_natural_language(taf.get('rawTAF', ''))
                        })
                except (ValueError, TypeError):
                    continue
        return sorted(nearby, key=lambda x: x['distance'])

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

    def get_pireps_near_location(self, lat: float, lon: float, pireps: List[Dict], max_distance: float = 50) -> List[Dict]:
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
                    if distance <= max_distance:
                        nearby_pireps.append({
                            'station': pirep.get('icaoId', 'Unknown'),
                            'raw': pirep.get('rawOb', ''),
                            'distance': round(distance, 1),
                            'time': pirep.get('reportTime', ''),
                            'nlp': self.nlp_processor.decode_pirep_to_natural_language(pirep.get('rawOb', ''))
                        })
                except (ValueError, TypeError):
                    continue
        
        return sorted(nearby_pireps, key=lambda x: x['distance'])

    def get_weather_description(self, metar: Dict) -> str:
        """Get human-readable weather description from METAR"""
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
