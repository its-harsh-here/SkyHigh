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
from dataclasses import dataclass

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

class WeatherProcessor:
    """Process and categorize aviation weather data"""
    
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
        current_time = datetime.now(timezone.utc)
        if departure_time:
            try:
                current_time = datetime.fromisoformat(departure_time.replace('Z', '+00:00'))
            except:
                pass
        
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

    def get_comprehensive_weather(self, bbox: str = None, flight_segments: List[Dict] = None) -> Dict:
        """Fetch comprehensive weather data for flight path"""
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
        
        # Fetch different weather products concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                'metars': executor.submit(self.get_metars_by_bbox, bbox),
                'tafs': executor.submit(self.get_tafs_by_bbox, bbox),
                'pireps': executor.submit(self.get_pireps_by_bbox, bbox),
                'sigmets': executor.submit(self.get_sigmets),
                'gairmets': executor.submit(self.get_gairmets),
                'cwas': executor.submit(self.get_cwas)
            }
            
            for product_type, future in futures.items():
                try:
                    weather_data[product_type] = future.result(timeout=15)
                except Exception as e:
                    logging.error(f"Error fetching {product_type}: {e}")
                    weather_data[product_type] = []
        
        return weather_data

    def get_metars_by_bbox(self, bbox: str) -> List[Dict]:
        """Fetch METAR data by bounding box"""
        try:
            url = f"{self.base_url}/metar"
            params = {
                'bbox': bbox,
                'format': 'json',
                'hours': 3
            }
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return [self.enhance_metar(metar) for metar in data]
        except Exception as e:
            logging.error(f"Error fetching METARs: {e}")
        
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
        except Exception as e:
            logging.error(f"Error fetching TAFs: {e}")
        
        return []

    def get_pireps_by_bbox(self, bbox: str) -> List[Dict]:
        """Fetch PIREP data by bounding box"""
        try:
            url = f"{self.base_url}/pirep"
            params = {
                'bbox': bbox,
                'format': 'json',
                'age': 6
            }
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logging.error(f"Error fetching PIREPs: {e}")
        
        return []

    def get_sigmets(self) -> List[Dict]:
        """Fetch SIGMET data"""
        try:
            url = f"{self.base_url}/airsigmet"
            params = {'format': 'json'}
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
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
        except Exception as e:
            logging.error(f"Error fetching CWAs: {e}")
        
        return []

    def enhance_metar(self, metar: Dict) -> Dict:
        """Enhance METAR data with categorization"""
        metar['category'] = self.categorize_weather(metar)
        return metar

    def create_timeline_analysis(self, flight_segments: List[Dict], weather_data: Dict) -> List[Dict]:
        """Create detailed timeline weather analysis for flight path"""
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
                
                # Get weather conditions for this time/location
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
        """Get weather conditions for specific location and time"""
        
        # Find nearest METAR station
        nearest_metar = self.find_nearest_weather_data(lat, lon, weather_data.get('metars', []))
        
        # Check for PIREPs in area
        pirep_reports = self.get_pireps_near_location(lat, lon, weather_data.get('pireps', []))
        
        # Check for hazardous weather warnings - FIXED BUG HERE
        hazards = self.check_hazards_for_location(lat, lon, weather_data)
        
        # Determine primary weather condition
        if hazards:  # Only if there are actual hazards
            severity = "Severe" if any("SIGMET" in h or "thunderstorm" in h.lower() for h in hazards) else "Significant"
            condition = "Hazardous weather in area"
        elif nearest_metar:
            severity = nearest_metar.get('category', 'Clear')
            condition = self.get_weather_description(nearest_metar)
        else:
            severity = "Clear"
            condition = "No significant weather reported"
        
        return {
            'severity': severity,
            'condition': condition,
            'description': self.create_detailed_description(nearest_metar, pirep_reports, hazards),
            'hazards': hazards,
            'pirep_count': len(pirep_reports),
            'nearest_station': nearest_metar.get('icaoId') if nearest_metar else None
        }

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

    def check_hazards_for_location(self, lat: float, lon: float, weather_data: Dict) -> List[str]:
        """Check for weather hazards at location - FIXED BUG"""
        hazards = []
        
        # Only add hazards if there are actually hazardous conditions present
        sigmets = weather_data.get('sigmets', [])
        gairmets = weather_data.get('gairmets', [])  
        cwas = weather_data.get('cwas', [])
        
        # Check SIGMETs - only add if there are actual SIGMETs
        if sigmets and len(sigmets) > 0:
            # Check if any SIGMETs are relevant to the location
            relevant_sigmets = []
            for sigmet in sigmets:
                # Add basic location check if coordinates are available
                if sigmet.get('lat') and sigmet.get('lon'):
                    distance = self.haversine_distance(lat, lon, sigmet['lat'], sigmet['lon'])
                    if distance < 200:  # Within 200nm
                        relevant_sigmets.append(sigmet)
            
            if relevant_sigmets:
                hazards.append("SIGMET: Hazardous weather advisory active")
        
        # Check G-AIRMETs - only add if there are actual G-AIRMETs near location
        if gairmets and len(gairmets) > 0:
            relevant_gairmets = []
            for gairmet in gairmets:
                if gairmet.get('lat') and gairmet.get('lon'):
                    distance = self.haversine_distance(lat, lon, gairmet['lat'], gairmet['lon'])
                    if distance < 100:  # Within 100nm
                        relevant_gairmets.append(gairmet)
            
            if relevant_gairmets:
                hazards.append("G-AIRMET: Moderate weather advisory")
        
        # Check Center Weather Advisories - only add if relevant to location
        if cwas and len(cwas) > 0:
            relevant_cwas = []
            for cwa in cwas:
                if cwa.get('lat') and cwa.get('lon'):
                    distance = self.haversine_distance(lat, lon, cwa['lat'], cwa['lon'])
                    if distance < 150:  # Within 150nm
                        relevant_cwas.append(cwa)
            
            if relevant_cwas:
                hazards.append("CWA: Center weather advisory active")
        
        return hazards[:3]  # Limit to top 3 hazards

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
            conditions.append(f"Visibility: {visibility}")
        
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
    """Enhanced flight plan analysis with comprehensive weather timeline"""
    try:
        data = request.get_json()
        departure = data.get('departure', '').upper()
        destination = data.get('destination', '').upper()
        waypoints = [wp.strip().upper() for wp in data.get('waypoints', []) if wp.strip()]
        cruise_speed = int(data.get('cruise_speed', 450))
        departure_time = data.get('departure_time')
        
        if not departure or not destination:
            return jsonify({'error': 'Departure and destination required'}), 400
        
        # Calculate flight path with timing
        flight_segments = weather_processor.calculate_flight_path(
            departure, destination, waypoints, cruise_speed, departure_time
        )
        
        if not flight_segments:
            return jsonify({'error': 'Unable to calculate flight path'}), 400
        
        # Get comprehensive weather data for the flight path
        weather_data = weather_processor.get_comprehensive_weather(
            flight_segments=flight_segments
        )
        
        # Create detailed timeline analysis
        timeline = weather_processor.create_timeline_analysis(flight_segments, weather_data)
        
        # Calculate overall assessment - FIXED LOGIC
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
                'cwas_count': len(weather_data.get('cwas', []))
            }
        })
        
    except Exception as e:
        logging.error(f"Error in enhanced flight plan: {e}")
        return jsonify({'error': f'Processing error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
