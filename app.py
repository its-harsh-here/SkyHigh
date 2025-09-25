from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import requests
import json
import re
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Tuple
import os

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
        """
        Categorize weather conditions into Clear, Significant, or Severe
        Based on visibility, ceiling, weather phenomena, and wind conditions
        """
        try:
            visibility = metar_data.get('visib', 10)
            wind_speed = metar_data.get('wspd', 0) or 0
            wind_gust = metar_data.get('wgst', 0) or 0
            weather_string = metar_data.get('wxString', '') or ''
            clouds = metar_data.get('clouds', [])
            
            # Convert visibility to numeric value
            if isinstance(visibility, str):
                if 'SM' in visibility:
                    vis_val = float(re.findall(r'[\d.]+', visibility)[0]) if re.findall(r'[\d.]+', visibility) else 10
                elif visibility == '9999' or visibility == 'CAVOK':
                    vis_val = 10
                else:
                    vis_val = float(visibility) / 1609 if visibility.isdigit() else 10  # Convert meters to miles
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

    def get_metar_data(self, icao_codes: List[str]) -> Dict:
        """Fetch METAR data from Aviation Weather API"""
        try:
            ids_param = ','.join(icao_codes)
            url = f"{self.base_url}/metar"
            params = {
                'ids': ids_param,
                'format': 'json',
                'taf': 'false',
                'hours': 2
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            processed_data = {}
            
            for metar in data:
                icao = metar.get('icaoId', '')
                if icao:
                    category = self.categorize_weather(metar)
                    processed_data[icao] = {
                        **metar,
                        'category': category,
                        'processed_at': datetime.now(timezone.utc).isoformat()
                    }
            
            return processed_data
            
        except Exception as e:
            logging.error(f"Error fetching METAR data: {e}")
            return {}

    def get_taf_data(self, icao_codes: List[str]) -> Dict:
        """Fetch TAF data from Aviation Weather API"""
        try:
            ids_param = ','.join(icao_codes)
            url = f"{self.base_url}/taf"
            params = {
                'ids': ids_param,
                'format': 'json'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return {taf.get('icaoId', ''): taf for taf in response.json()}
            
        except Exception as e:
            logging.error(f"Error fetching TAF data: {e}")
            return {}

    def get_pirep_data(self, bbox: str = None) -> List:
        """Fetch PIREP data from Aviation Weather API"""
        try:
            url = f"{self.base_url}/pirep"
            params = {
                'format': 'json',
                'age': 6  # Last 6 hours
            }
            
            if bbox:
                params['bbox'] = bbox
            else:
                params['bbox'] = '25,-125,50,-65'  # Continental US
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logging.error(f"Error fetching PIREP data: {e}")
            return []

# Initialize processor
weather_processor = WeatherProcessor()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

@app.route('/api/weather', methods=['GET'])
def get_weather():
    """Get comprehensive weather data for specified airports"""
    icao_codes = request.args.get('airports', '').upper().split(',')
    icao_codes = [code.strip() for code in icao_codes if code.strip()]
    
    if not icao_codes:
        return jsonify({'error': 'No airport codes provided'}), 400
    
    try:
        # Get METAR and TAF data
        metar_data = weather_processor.get_metar_data(icao_codes)
        taf_data = weather_processor.get_taf_data(icao_codes)
        
        # Combine data
        result = {}
        for icao in icao_codes:
            result[icao] = {
                'metar': metar_data.get(icao, {}),
                'taf': taf_data.get(icao, {}),
                'icao': icao
            }
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error in /api/weather: {e}")
        return jsonify({'error': 'Failed to fetch weather data'}), 500

@app.route('/api/pireps', methods=['GET'])
def get_pireps():
    """Get pilot reports for a region"""
    bbox = request.args.get('bbox')
    pireps = weather_processor.get_pirep_data(bbox)
    return jsonify(pireps)

@app.route('/api/flight-plan', methods=['POST'])
def process_flight_plan():
    """Process flight plan and extract weather along route"""
    try:
        data = request.get_json()
        departure = data.get('departure', '').upper()
        destination = data.get('destination', '').upper()
        waypoints = data.get('waypoints', [])
        
        # Collect all airports along route
        airports = [departure, destination] + [wp.upper() for wp in waypoints if wp]
        airports = list(set(airports))  # Remove duplicates
        
        # Get weather for all points
        weather_data = {}
        if airports:
            metar_data = weather_processor.get_metar_data(airports)
            taf_data = weather_processor.get_taf_data(airports)
            
            for icao in airports:
                weather_data[icao] = {
                    'metar': metar_data.get(icao, {}),
                    'taf': taf_data.get(icao, {}),
                    'icao': icao
                }
        
        # Analyze route conditions
        categories = [weather_data[icao]['metar'].get('category', 'Clear') for icao in airports if weather_data[icao]['metar']]
        overall_category = 'Clear'
        if 'Severe' in categories:
            overall_category = 'Severe'
        elif 'Significant' in categories:
            overall_category = 'Significant'
        
        return jsonify({
            'route': {
                'departure': departure,
                'destination': destination,
                'waypoints': waypoints,
                'overall_category': overall_category
            },
            'weather': weather_data
        })
        
    except Exception as e:
        logging.error(f"Error processing flight plan: {e}")
        return jsonify({'error': 'Failed to process flight plan'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
