from flask import Flask, render_template, request, jsonify
import os
import logging
from config import config
from weather_service import WeatherService
from flight_plan_parser import FlightPlanParser
from weather_analyzer import WeatherAnalyzer
from visualizations import WeatherVisualizer
from nlp_analyzer import AviationNLPAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Load configuration
config_name = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[config_name])

# Initialize services
weather_service = WeatherService()
flight_parser = FlightPlanParser()
weather_analyzer = WeatherAnalyzer()
visualizer = WeatherVisualizer()
nlp_analyzer = AviationNLPAnalyzer()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/debug')
def debug():
    """Debug test page"""
    with open('debug_test.html', 'r') as f:
        return f.read()

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
                
        # Analyze weather conditions
        if 'metar' in results and results['metar']:
            analysis = weather_analyzer.analyze_metar(results['metar'])
            results['analysis'] = analysis
            
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
            
            if not departure or not arrival:
                return jsonify({'error': 'Departure and arrival airports are required'}), 400
                
            airports = [departure] + waypoints + [arrival]
        
        # Get weather data for all airports
        weather_data = {}
        for airport in airports:
            airport_weather = {
                'metar': weather_service.get_metar(airport),
                'taf': weather_service.get_taf(airport),
                'pirep': weather_service.get_pirep(airport)
            }
            
            # Analyze conditions
            if airport_weather['metar']:
                airport_weather['analysis'] = weather_analyzer.analyze_metar(airport_weather['metar'])
            
            weather_data[airport] = airport_weather
        
        # Generate visualizations
        visualizations = {
            'wind_chart': visualizer.create_wind_chart(weather_data),
            'visibility_chart': visualizer.create_visibility_chart(weather_data),
            'route_map': visualizer.create_route_map(airports, weather_data),
            'weather_timeline': visualizer.create_weather_timeline(weather_data)
        }
        
        # Generate consolidated briefing
        briefing = weather_analyzer.generate_flight_briefing(weather_data, airports)
        
        # Generate NLP-based intelligent summary and recommendations
        nlp_analysis = nlp_analyzer.generate_comprehensive_summary(weather_data, airports, briefing)
        
        return jsonify({
            'airports': airports,
            'weather_data': weather_data,
            'visualizations': visualizations,
            'briefing': briefing,
            'nlp_analysis': nlp_analysis
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather/summary/<airport_code>')
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
