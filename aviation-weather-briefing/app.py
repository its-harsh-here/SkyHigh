from flask import Flask, render_template, request, jsonify
import os
import logging
from config import config
from weather_service import WeatherService
from weather_analyzer import WeatherAnalyzer
from nlp_analyzer import AviationNLPAnalyzer
from visualizations import WeatherVisualizer
from airport_service import AirportService
from flight_parser import FlightPlanParser
from airport_coordinates import calculate_route_distance
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
config_name = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[config_name])

# Initialize services
weather_service = WeatherService()
flight_parser = FlightPlanParser()
weather_analyzer = WeatherAnalyzer()
visualizer = WeatherVisualizer()
nlp_analyzer = AviationNLPAnalyzer()
airport_service = AirportService()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/debug')
def debug():
    """Debug test page"""
    with open('debug_test.html', 'r') as f:
        return f.read()

@app.route('/api/airports/validate/<airport_code>')
def validate_airport(airport_code):
    """Validate an airport code"""
    try:
        is_valid = airport_service.validate_airport_code(airport_code)
        airport_info = airport_service.get_airport_info(airport_code) if is_valid else None
        
        return jsonify({
            'valid': is_valid,
            'airport_code': airport_code.upper(),
            'airport_info': airport_info
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/airports/search')
def search_airports():
    """Search for airports"""
    try:
        query = request.args.get('q', '')
        limit = int(request.args.get('limit', 10))
        
        results = airport_service.search_airports(query, limit)
        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather/individual', methods=['POST'])
def get_individual_weather():
    """Get individual weather reports for specific airports"""
    try:
        data = request.get_json()
        airport_code = data.get('airport_code', '').upper()
        report_types = data.get('report_types', ['METAR'])
        
        if not airport_code:
            return jsonify({'error': 'Airport code is required'}), 400
            
        results = {}
        
        for report_type in report_types:
            if report_type == 'METAR':
                results['metar'] = weather_service.get_metar(airport_code)
            elif report_type == 'TAF':
                results['taf'] = weather_service.get_taf(airport_code)
            elif report_type == 'PIREP':
                results['pirep'] = weather_service.get_pirep(airport_code)
                
        # Analyze weather conditions using ALL available data
        results['analysis'] = weather_analyzer.analyze_combined_weather_data(results)
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/api/flight-plan/analyze', methods=['POST'])
def analyze_flight_plan():
    """Analyze weather along a flight plan route"""
    try:
        data = request.get_json()
        
        # Handle different input methods
        if 'flight_plan_text' in data:
            # Parse uploaded flight plan
            airports = flight_parser.parse_flight_plan_text(data['flight_plan_text'])
        else:
            # Manual input of airports
            departure = data.get('departure', '').upper()
            arrival = data.get('arrival', '').upper()
            waypoints = [wp.upper() for wp in data.get('waypoints', [])]
            departure_time = data.get('departure_time', '')  # ISO format or relative time
            
            if not departure or not arrival:
                return jsonify({'error': 'Departure and arrival airports are required'}), 400
            
            airports = [departure] + waypoints + [arrival]
            
            # Basic ICAO format validation (4 letters)
            for airport in airports:
                if not airport or len(airport) != 4 or not airport.isalpha():
                    return jsonify({
                        'error': f"Invalid airport code format: {airport}. Please use 4-letter ICAO codes."
                    }), 400
        
        # Get weather data for all airports (time-aware) with validation
        weather_data = {}
        invalid_airports = []
        
        for airport in airports:
            # Use time-appropriate weather data
            time_weather = weather_service.get_time_appropriate_weather(airport, departure_time)
            
            # Check if we got valid weather data (airport exists)
            if not time_weather['metar'] and not time_weather['taf']:
                invalid_airports.append(airport)
                continue
                
            airport_weather = {
                'metar': time_weather['metar'],
                'taf': time_weather['taf'],
                'pirep': time_weather['pirep'],
                'time_appropriate_conditions': time_weather['time_appropriate_conditions'],
                'primary_source': time_weather['primary_source']
            }
            
            # Analyze conditions using ALL available data (METAR, TAF, PIREP)
            airport_weather['analysis'] = weather_analyzer.analyze_combined_weather_data(airport_weather)
            
            weather_data[airport] = airport_weather
        
        # Return error if any airports are invalid
        if invalid_airports:
            return jsonify({
                'error': f"No weather data found for airport(s): {', '.join(invalid_airports)}. Please check the airport codes and try again."
            }), 400
        
        # Generate visualizations
        visualizations = {
            'wind_chart': visualizer.create_wind_chart(weather_data),
            'visibility_chart': visualizer.create_visibility_chart(weather_data),
            'route_map': visualizer.create_route_map(airports, weather_data),
            'weather_timeline': visualizer.create_weather_timeline(weather_data)
        }
        
        # Generate consolidated briefing
        briefing = weather_analyzer.generate_flight_briefing(weather_data, airports)
        
        # Generate NLP-based intelligent summary
        nlp_analysis = nlp_analyzer.generate_comprehensive_summary(weather_data, airports, briefing)
        
        # Calculate route distance
        total_distance_nm = calculate_route_distance(airports)
        
        # Get current UTC time
        current_utc = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        return jsonify({
            'airports': airports,
            'weather_data': weather_data,
            'briefing': briefing,
            'visualizations': visualizations,
            'nlp_analysis': nlp_analysis,
            'route_info': {
                'total_distance_nm': round(total_distance_nm, 1),
                'current_utc_time': current_utc,
                'departure_airport': airports[0] if airports else None,
                'arrival_airport': airports[-1] if airports else None,
                'waypoints_count': len(airports) - 2 if len(airports) > 2 else 0
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
def get_weather_summary(airport_code):
    """Get a quick weather summary for an airport"""
    try:
        airport_code = airport_code.upper()
        
        # Get current weather
        metar = weather_service.get_metar(airport_code)
        if not metar:
            return jsonify({'error': 'No weather data found for airport'}), 404
            
        # Analyze and categorize
        analysis = weather_analyzer.analyze_metar(metar)
        
        return jsonify({
            'airport': airport_code,
            'current_conditions': metar,
            'category': analysis['category'],
            'summary': analysis['summary'],
            'key_factors': analysis['key_factors']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)
