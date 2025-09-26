# routes/api.py
from flask import Blueprint, request, jsonify, send_from_directory
import logging
from services.weather_service import WeatherService
from services.nlp_service import SimpleNLPProcessor
from models.schemas import FlightPlanInput
from exceptions import UserInputError

api_bp = Blueprint("api", __name__)

# Singletons for this process (can DI elsewhere if needed)
_weather = WeatherService()
_nlp = SimpleNLPProcessor()

@api_bp.route("/")
def index():
    return send_from_directory(".", "index.html")

@api_bp.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(".", filename)

@api_bp.route("/api/process-natural-language", methods=["POST"])
def process_natural_language():
    try:
        data = request.get_json() or {}
        text = data.get("text", "")
        if not text:
            return jsonify({"error": "No text provided"}), 400
        flight_plan = _nlp.extract_flight_plan_from_text(text)
        return jsonify({"flight_plan": flight_plan, "original_text": text, "success": True})
    except Exception as e:
        logging.exception("NLU processing error")
        return jsonify({"error": f"Processing error: {e}"}), 500

@api_bp.route("/api/enhanced-flight-plan", methods=["POST"])
def enhanced_flight_plan():
    try:
        data = request.get_json() or {}
        fpi = FlightPlanInput(
            departure=(data.get("departure", "") or "").upper(),
            destination=(data.get("destination", "") or "").upper(),
            waypoints=[(wp or "").strip().upper() for wp in data.get("waypoints", []) if (wp or "").strip()],
            cruise_speed=int(data.get("cruise_speed", 450)),
            departure_time=data.get("departure_time")
        )
        if not fpi.departure or not fpi.destination:
            return jsonify({"error": "Departure and destination required"}), 400

        segments = _weather.calculate_flight_path(
            fpi.departure, fpi.destination, fpi.waypoints, fpi.cruise_speed, fpi.departure_time
        )

        weather_data = _weather.get_comprehensive_weather(segments)
        timeline = _weather.create_timeline_analysis(segments, weather_data)

        severities = [t['severity'] for t in timeline]
        overall = 'Severe' if 'Severe' in severities else ('Significant' if 'Significant' in severities else 'Clear')

        briefing = _nlp.summarize_weather_briefing(weather_data)
        risk = _nlp.generate_risk_assessment(timeline)

        return jsonify({
            'route': {
                'departure': fpi.departure,
                'destination': fpi.destination,
                'waypoints': fpi.waypoints,
                'cruise_speed': fpi.cruise_speed,
                'total_distance': sum(s['distance_nm'] for s in segments),
                'total_flight_time': sum(s['flight_time_hours'] for s in segments),
                'overall_severity': overall,
                'risk_assessment': risk,
            },
            'flight_segments': [{
                'from': s['from'], 'to': s['to'], 'distance_nm': s['distance_nm'],
                'flight_time_hours': s['flight_time_hours'],
                'start_time': s['start_time'].isoformat(), 'end_time': s['end_time'].isoformat()
            } for s in segments],
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
            'nlp_briefing_summary': briefing,
            'risk_assessment': risk
        })

    except UserInputError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.exception("enhanced-flight-plan error")
        return jsonify({"error": f"Processing error: {e}"}), 500
