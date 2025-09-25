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

class WeatherProcessor:
    """Process and categorize aviation weather data with NOTAM support"""
    
    def __init__(self):
        self.base_url = "https://aviationweather.gov/api/data"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PilotWeatherBriefingApp/1.0'
        })

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
            return "Clear"  # Default to Clear if error

    def simulate_historical_weather(self, lat: float, lon: float, target_time: datetime, current_weather: Dict = None) -> Dict:
        """Simulate realistic weather conditions for a historical time based on current conditions"""
        
        # Create a deterministic seed based on location and time
        seed_str = f"{lat:.2f}_{lon:.2f}_{target_time.strftime('%Y%m%d%H')}"
        seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        # Calculate time difference in hours
        now = datetime.now(timezone.utc)
        hours_diff = (target_time - now).total_seconds() / 3600
        
        # Base weather conditions (if we have current weather, modify it; otherwise create realistic conditions)
        if current_weather and current_weather.get('wspd') is not None:
            base_wind = current_weather.get('wspd', 10)
            base_visibility = 10
            base_ceiling = 5000
        else:
            # Create realistic base conditions
            base_wind = random.uniform(5, 20)
            base_visibility = random.choice([10, 8, 5, 3, 1.5])
            base_ceiling = random.choice([None, 5000, 3000, 1000, 500])
        
        # Simulate weather variation based on time difference and location
        # Weather patterns typically change every 6-12 hours
        weather_cycle = math.sin(hours_diff / 6 * math.pi) * 0.5 + random.uniform(-0.3, 0.3)
        
        # Seasonal variation (approximate)
        month = target_time.month
        seasonal_factor = math.sin((month - 3) * math.pi / 6) * 0.3  # Peak variation in winter/summer
        
        # Geographic factors (simplified)
        coastal_factor = 0.2 if abs(lat) < 45 else 0.1  # More variation near coasts
        
        # Combined variation factor
        variation = weather_cycle + seasonal_factor + coastal_factor
        
        # Apply variations to create simulated weather
        wind_variation = 1 + variation * 0.5
        simulated_wind = max(0, base_wind * wind_variation + random.uniform(-5, 5))
        
        # Determine weather severity based on simulated conditions
        if variation > 0.4:
            # Bad weather conditions
            weather_types = ['TSRA', 'SN', 'RA', 'FG']
            weather_string = random.choice(weather_types)
            visibility = random.uniform(0.5, 2)
            ceiling = random.choice([200, 400, 800])
            gusts = simulated_wind + random.uniform(10, 20)
        elif variation > 0.1:
            # Marginal conditions
            weather_types = ['', 'BKN', 'SCT', '-RA', 'HZ']
            weather_string = random.choice(weather_types)
            visibility = random.uniform(3, 6)
            ceiling = random.choice([1000, 1500, 2000])
            gusts = simulated_wind + random.uniform(5, 15) if random.random() > 0.7 else None
        else:
            # Good conditions
            weather_string = ''
            visibility = 10
            ceiling = None
            gusts = None
        
        # Create simulated METAR-like data
        simulated_metar = {
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
        
        return simulated_metar

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
        
        # Calculate flight segments with timing
        flight_segments = []
        
        # --- UPDATED: Allow 15 days in past and 4 hours in future ---
        if departure_time and departure_time.strip():
            try:
                logging.info(f"Parsing departure_time: {departure_time}")
                
                # Handle datetime-local format from frontend (YYYY-MM-DDTHH:MM)
                if 'T' in departure_time and len(departure_time) == 16:
                    # Convert datetime-local to UTC
                    current_time = datetime.fromisoformat(departure_time)
                    # Assume input is in UTC (since aviation uses UTC)
                    current_time = current_time.replace(tzinfo=timezone.utc)
                elif departure_time.endswith('Z'):
                    # ISO format with Z
                    current_time = datetime.fromisoformat(departure_time.replace('Z', '+00:00'))
                elif '+' in departure_time or departure_time.endswith('+00:00'):
                    # ISO format with timezone
                    current_time = datetime.fromisoformat(departure_time)
                else:
                    # Try to parse as ISO format
                    current_time = datetime.fromisoformat(departure_time)
                    if current_time.tzinfo is None:
                        current_time = current_time.replace(tzinfo=timezone.utc)
                
                # UPDATED: Allow 15 days in past and 4 hours in future (per Aviation Weather API)
                now_utc = datetime.now(timezone.utc)
                if current_time > now_utc + timedelta(hours=4):
                    raise ValueError('Departure time cannot be more than 4 hours in the future (TAF forecast limit).')
                
                if current_time < now_utc - timedelta(days=15):
                    raise ValueError('Departure time cannot be more than 15 days in the past (API data limit).')
                
                logging.info(f"Successfully parsed departure_time: {current_time}")
                
            except ValueError as ve:
                logging.error(f"ValueError parsing departure_time: {ve}")
                raise ve
            except Exception as e:
                logging.error(f"Error parsing departure_time: {e}")
                raise ValueError(f'Invalid departure_time format: {departure_time}. Please use the date/time picker.')
        else:
            current_time = datetime.now(timezone.utc)
            logging.info(f"Using current UTC time: {current_time}")
        
        path_points = list(coordinates.keys())
        
        for i in range(len(path_points) - 1):
            from_icao = path_points[i]
            to_icao = path_points[i + 1]
            
            from_coords = coordinates[from_icao]
            to_coords = coordinates[to_icao]
            
            # Calculate distance and time
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
        
        # Determine bounding box from flight segments if not provided
        if not bbox and flight_segments:
            lats = []
            lons = []
            for segment in flight_segments:
                lats.extend([segment['from_coords']['lat'], segment['to_coords']['lat']])
                lons.extend([segment['from_coords']['lon'], segment['to_coords']['lon']])
            
            # Add buffer around flight path
            buffer = 2.0  # degrees
            bbox = f"{min(lats)-buffer},{min(lons)-buffer},{max(lats)+buffer},{max(lons)+buffer}"
        
        # Default US bounding box if no flight path
        if not bbox:
            bbox = "25,-125,50,-65"
        
        # Collect airports for NOTAM fetching
        if not airports and flight_segments:
            airports = []
            for segment in flight_segments:
                airports.extend([segment['from'], segment['to']])
            airports = list(set(airports))  # Remove duplicates
        
        # Fetch different weather products concurrently including NOTAMs
        with concurrent.futures.ThreadPoolExecutor(max_workers=7) as executor:
            futures = {
                'metars': executor.submit(self.get_historical_metars_by_bbox, bbox, departure_time),
                'tafs': executor.submit(self.get_tafs_by_bbox, bbox),
                'pireps': executor.submit(self.get_historical_pireps_by_bbox, bbox, departure_time),
                'sigmets': executor.submit(self.get_sigmets),
                'gairmets': executor.submit(self.get_gairmets),
                'cwas': executor.submit(self.get_cwas),
                'notams': executor.submit(self.get_notams, airports or [], departure_time)  # Pass departure_time
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
            
            # If departure time is provided, get historical data
            if departure_time:
                now_utc = datetime.now(timezone.utc)
                
                # For historical data (more than 3 hours old), use specific time range
                if departure_time < now_utc - timedelta(hours=3):
                    # Get historical METAR data around the departure time
                    start_time = departure_time - timedelta(hours=1)
                    end_time = departure_time + timedelta(hours=1)
                    params['startTime'] = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
                    params['endTime'] = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
                else:
                    # For recent/future times, get recent data
                    params['hours'] = 3
            else:
                params['hours'] = 3
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return [self.enhance_metar(metar) for metar in data]
            elif response.status_code == 204:
                # No data available - this is normal for historical periods
                logging.info(f"No METAR data available for time period")
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
            
            # If departure time is provided, get historical data
            if departure_time:
                now_utc = datetime.now(timezone.utc)
                
                # For historical data, use specific time range
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
                logging.info(f"No PIREP data available for time period")
                return []
        except Exception as e:
            logging.error(f"Error fetching PIREPs: {e}")
        
        return []

    def get_notams(self, airports: List[str], departure_time: datetime = None) -> List[Dict]:
        """Generate time-appropriate NOTAMs based on departure time"""
        sample_notams = []
        
        # Use departure_time if provided, otherwise current time
        if departure_time:
            reference_time = departure_time
        else:
            reference_time = datetime.now(timezone.utc)
        
        notam_templates = [
            {
                'text': 'RWY {rwy} CLOSED FOR MAINTENANCE',
                'classification': 'Runway',
                'severity': 'Significant'
            },
            {
                'text': 'ILS RWY {rwy} OUT OF SERVICE',
                'classification': 'Navigation Aid',
                'severity': 'Significant'
            },
            {
                'text': 'CONSTRUCTION ACTIVITY NEAR TERMINAL',
                'classification': 'Airport',
                'severity': 'Clear'
            },
            {
                'text': 'TEMPORARY FLIGHT RESTRICTION IN EFFECT',
                'classification': 'Airspace',
                'severity': 'Severe'
            },
            {
                'text': 'TAXIWAY {twy} PARTIALLY CLOSED',
                'classification': 'Taxiway',
                'severity': 'Clear'
            }
        ]
        
        runways = ['09/27', '18/36', '04/22', '13/31', '01/19']
        taxiways = ['A', 'B', 'C', 'D', 'E']
        
        # Create deterministic NOTAMs based on departure time
        for i, airport in enumerate(airports[:4]):  # Limit to 4 airports
            # Create deterministic seed based on airport and departure time
            seed_str = f"{airport}_{reference_time.strftime('%Y%m%d')}"
            seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
            random.seed(seed)
            
            template = notam_templates[i % len(notam_templates)]
            runway = runways[i % len(runways)]
            taxiway = taxiways[i % len(taxiways)]
            
            # Create NOTAMs that would be active around the departure time
            # Some NOTAMs start before departure, some during
            start_offset_hours = random.randint(-48, -2)  # 2-48 hours before departure
            duration_hours = random.randint(6, 72)  # 6-72 hours duration
            
            start_time = reference_time + timedelta(hours=start_offset_hours)
            end_time = start_time + timedelta(hours=duration_hours)
            
            # Only include NOTAMs that are active during or around the departure time
            if end_time > reference_time:  # NOTAM is still active
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
                    'source': 'Demo Data (Time-Based)'
                })
        
        return sample_notams

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

    def enhance_metar(self, metar: Dict) -> Dict:
        """Enhance METAR data with categorization"""
        metar['category'] = self.categorize_weather(metar)
        return metar

    def create_timeline_analysis(self, flight_segments: List[Dict], weather_data: Dict) -> List[Dict]:
        """Create detailed timeline weather analysis for flight path with time-based weather simulation"""
        timeline = []
        
        for segment in flight_segments:
            # Break segment into smaller time intervals for detailed analysis
            segment_duration = segment['flight_time_hours']
            num_intervals = max(1, int(segment_duration * 4))  # 15-minute intervals
            interval_duration = segment_duration / num_intervals
            
            for i in range(num_intervals):
                interval_start = segment['start_time'] + timedelta(hours=i * interval_duration)
                interval_end = segment['start_time'] + timedelta(hours=(i + 1) * interval_duration)
                
                # Interpolate position along flight path
                progress = (i + 0.5) / num_intervals
                lat = segment['from_coords']['lat'] + progress * (segment['to_coords']['lat'] - segment['from_coords']['lat'])
                lon = segment['from_coords']['lon'] + progress * (segment['to_coords']['lon'] - segment['from_coords']['lon'])
                
                # Get weather conditions for this time/location with historical simulation
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

    def get_conditions_for_location_time(self, lat: float, lon: float, time: datetime, weather_data: Dict) -> Dict:
        """Get weather conditions for specific location and time with historical simulation"""
        
        # Find nearest METAR station for reference
        nearest_metar = self.find_nearest_weather_data(lat, lon, weather_data.get('metars', []))
        
        # For historical data, try to use real weather data; otherwise simulate
        now_utc = datetime.now(timezone.utc)
        if nearest_metar and abs((time - now_utc).total_seconds()) < 3 * 3600:  # Within 3 hours
            # Use real weather data
            simulated_weather = nearest_metar
        else:
            # Simulate historical weather conditions based on the specific time
            simulated_weather = self.simulate_historical_weather(lat, lon, time, nearest_metar)
        
        # Enhance the simulated weather with categorization
        simulated_weather['category'] = self.categorize_weather(simulated_weather)
        
        # Check for PIREPs in area (use current PIREPs as reference)
        pirep_reports = self.get_pireps_near_location(lat, lon, weather_data.get('pireps', []))
        
        # Check for hazardous weather warnings (simulated based on weather conditions)
        hazards = self.simulate_hazards_for_conditions(simulated_weather, weather_data)
        
        # Check for NOTAMs affecting nearby airports
        notam_warnings = self.check_notams_for_location(lat, lon, weather_data.get('notams', []))
        
        # Combine hazards with NOTAM warnings
        all_hazards = hazards + notam_warnings
        
        # Determine primary weather condition based on simulated weather
        base_severity = simulated_weather.get('category', 'Clear')
        condition = self.get_weather_description(simulated_weather)
        
        # Only upgrade severity if there are actual hazards
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
            'description': self.create_detailed_description(simulated_weather, pirep_reports, all_hazards),
            'hazards': all_hazards,
            'pirep_count': len(pirep_reports),
            'nearest_station': simulated_weather.get('icaoId') if simulated_weather else None
        }

    def simulate_hazards_for_conditions(self, weather: Dict, weather_data: Dict) -> List[str]:
        """Simulate hazards based on weather conditions"""
        hazards = []
        
        # Create deterministic hazards based on weather severity
        if weather.get('wxString'):
            wx_string = weather['wxString']
            if 'TS' in wx_string:
                hazards.append("SIGMET: Thunderstorm activity")
            elif 'SN' in wx_string:
                hazards.append("G-AIRMET: Snow and icing conditions")
            elif 'FG' in wx_string:
                hazards.append("G-AIRMET: Low visibility in fog")
        
        # Add wind shear warnings for high winds
        if weather.get('wspd', 0) > 30:
            hazards.append("CWA: Strong surface winds")
        
        return hazards[:2]  # Limit to top 2 hazards

    def check_notams_for_location(self, lat: float, lon: float, notams: List[Dict]) -> List[str]:
        """Check for NOTAMs affecting nearby airports"""
        warnings = []
        
        # Only show significant NOTAMs for demo
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
        
        return warnings[:1]  # Limit to 1 most critical NOTAM

    def find_nearest_weather_data(self, lat: float, lon: float, weather_list: List[Dict]) -> Optional[Dict]:
        """Find nearest weather station to given coordinates"""
        nearest = None
        min_distance = float('inf')
        
        for weather in weather_list:
            w_lat = weather.get('lat', 0)
            w_lon = weather.get('lon', 0)
            
            if w_lat and w_lon:
                distance = self.haversine_distance(lat, lon, w_lat, w_lon)
                if distance < min_distance and distance < 100:  # Within 100nm
                    min_distance = distance
                    nearest = weather
        
        return nearest

    def get_pireps_near_location(self, lat: float, lon: float, pireps: List[Dict]) -> List[Dict]:
        """Get PIREPs near specified location"""
        nearby_pireps = []
        
        for pirep in pireps:
            p_lat = pirep.get('lat', 0)
            p_lon = pirep.get('lon', 0)
            
            if p_lat and p_lon:
                distance = self.haversine_distance(lat, lon, p_lat, p_lon)
                if distance < 50:  # Within 50nm
                    nearby_pireps.append(pirep)
        
        return nearby_pireps

    def get_weather_description(self, metar: Dict) -> str:
        """Get human-readable weather description from METAR"""
        if not metar:
            return "No weather data available"
        
        conditions = []
        
        # Weather phenomena
        wx_string = metar.get('wxString', '')
        if wx_string:
            conditions.append(f"Weather: {wx_string}")
        else:
            conditions.append("Weather: Clear")
        
        # Visibility
        visibility = metar.get('visib')
        if visibility:
            conditions.append(f"Visibility: {visibility}SM" if isinstance(visibility, (int, float)) else f"Visibility: {visibility}")
        
        # Wind
        wind_dir = metar.get('wdir')
        wind_speed = metar.get('wspd')
        if wind_dir and wind_speed:
            wind_gust = metar.get('wgst')
            if wind_gust:
                conditions.append(f"Wind: {wind_dir}°/{wind_speed}G{wind_gust}kt")
            else:
                conditions.append(f"Wind: {wind_dir}°/{wind_speed}kt")
        
        return " | ".join(conditions) if conditions else "Clear conditions"

    def create_detailed_description(self, metar: Dict, pireps: List[Dict], hazards: List[str]) -> str:
        """Create detailed weather description"""
        description_parts = []
        
        if metar:
            description_parts.append(f"Current: {self.get_weather_description(metar)}")
        
        if pireps:
            description_parts.append(f"{len(pireps)} pilot report(s) in area")
        
        if hazards:
            description_parts.extend(hazards)
        
        return " | ".join(description_parts) if description_parts else "No significant weather reported"

    def get_location_description(self, lat: float, lon: float, segment: Dict, progress: float) -> str:
        """Get human-readable location description"""
        if progress < 0.3:
            return f"Departing {segment['from']}"
        elif progress > 0.7:
            return f"Approaching {segment['to']}"
        else:
            return f"En route {segment['from']} → {segment['to']}"

    def format_time_for_display(self, dt: datetime) -> str:
        """Format datetime for display"""
        return dt.strftime("%H:%M UTC")

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
    """Enhanced flight plan analysis with comprehensive weather timeline and NOTAMs"""
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
        
        # Extract departure time from flight segments for weather/NOTAM processing
        actual_departure_time = flight_segments[0]['start_time']
        
        # Collect all airports for NOTAM fetching
        all_airports = [departure, destination] + waypoints
        
        # Get comprehensive weather data including NOTAMs for the flight path
        weather_data = weather_processor.get_comprehensive_weather(
            flight_segments=flight_segments,
            airports=all_airports,
            departure_time=actual_departure_time  # Pass the parsed departure time
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
