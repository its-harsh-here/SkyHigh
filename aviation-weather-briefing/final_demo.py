#!/usr/bin/env python3
"""
Final demonstration of the Aviation Weather Briefing System
Shows the complete NLP-enhanced weather analysis
"""
import requests
import json
import sys

def test_complete_system():
    """Test the complete system with NLP analysis"""
    print("🛩️" + "=" * 70)
    print("   AVIATION WEATHER BRIEFING SYSTEM - FINAL DEMO")
    print("=" * 72)
    
    # Test different route scenarios
    test_routes = [
        {
            'name': 'Cross-Country VFR',
            'departure': 'KJFK',
            'arrival': 'KLAX',
            'waypoints': ['KORD', 'KDEN']
        },
        {
            'name': 'East Coast Short Hop',
            'departure': 'KJFK',
            'arrival': 'KBOS',
            'waypoints': []
        },
        {
            'name': 'West Coast Route',
            'departure': 'KSEA',
            'arrival': 'KLAX',
            'waypoints': ['KPDX']
        }
    ]
    
    for i, route in enumerate(test_routes, 1):
        print(f"\n🧪 TEST {i}: {route['name']}")
        print("-" * 50)
        
        try:
            response = requests.post(
                'http://localhost:5001/api/flight-plan/analyze',
                json=route,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                display_analysis_results(data, route)
            else:
                print(f"❌ API Error: {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"❌ Request Error: {str(e)}")
    
    print("\n" + "=" * 72)
    print("🎉 DEMO COMPLETE - Aviation Weather Briefing System Ready!")
    print("🌐 Access the full interface at: http://localhost:5001")
    print("🔧 Debug interface at: http://localhost:5001/debug")
    print("=" * 72)

def display_analysis_results(data, route):
    """Display the analysis results in a formatted way"""
    route_str = f"{route['departure']} → {route['arrival']}"
    if route['waypoints']:
        route_str = f"{route['departure']} → {' → '.join(route['waypoints'])} → {route['arrival']}"
    
    print(f"📍 Route: {route_str}")
    
    # NLP Analysis
    nlp = data.get('nlp_analysis', {})
    if nlp:
        risk = nlp.get('risk_assessment', 'UNKNOWN')
        risk_emoji = {'HIGH': '🔴', 'MODERATE': '🟡', 'LOW': '🟢', 'MINIMAL': '✅'}.get(risk, '⚪')
        
        print(f"🎯 Risk Level: {risk_emoji} {risk}")
        print(f"📋 Executive Summary:")
        print(f"   {nlp.get('executive_summary', 'N/A')}")
        
        recommendations = nlp.get('pilot_recommendations', [])
        if recommendations:
            print(f"✈️  Top Pilot Actions:")
            for rec in recommendations[:3]:
                print(f"   • {rec}")
        
        factors = nlp.get('decision_factors', [])
        if factors:
            print(f"⚠️  Decision Factors:")
            for factor in factors:
                print(f"   • {factor}")
    
    # Weather Summary
    weather_data = data.get('weather_data', {})
    airports = data.get('airports', [])
    
    print(f"🌤️  Airport Conditions:")
    for airport in airports:
        airport_weather = weather_data.get(airport, {})
        metar = airport_weather.get('metar', {})
        analysis = airport_weather.get('analysis', {})
        
        if metar:
            category = analysis.get('category', 'UNKNOWN')
            category_emoji = {'CLEAR': '✅', 'SIGNIFICANT': '⚠️', 'SEVERE': '🔴'}.get(category, '⚪')
            
            wind_str = f"{metar.get('wind_direction', 'VRB')}°/{metar.get('wind_speed', 0)}kt"
            temp_str = f"{metar.get('temperature', 'N/A')}°C"
            flight_cat = metar.get('flight_category', 'UNK')
            
            print(f"   {airport}: {category_emoji} {category} | {wind_str} | {temp_str} | {flight_cat}")
    
    print()

if __name__ == '__main__':
    # Check if server is running
    try:
        response = requests.get('http://localhost:5001/', timeout=5)
        if response.status_code != 200:
            raise Exception("Server not responding correctly")
    except:
        print("❌ Server not running on localhost:5001")
        print("   Please start the server with: python run.py")
        sys.exit(1)
    
    test_complete_system()
