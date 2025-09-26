#!/usr/bin/env python3
"""
Test script for Aviation Weather Briefing System
"""
import requests
import json
import sys

def test_individual_weather():
    """Test individual weather endpoint"""
    print("🧪 Testing individual weather endpoint...")
    
    url = "http://localhost:5001/api/weather/individual"
    data = {
        "airport_code": "KJFK",
        "report_types": ["METAR", "TAF"]
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print("✅ Individual weather test passed")
            print(f"   Airport: {data['airport_code']}")
            print(f"   METAR available: {'metar' in result}")
            print(f"   Analysis available: {'analysis' in result}")
            return True
        else:
            print(f"❌ Individual weather test failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Individual weather test error: {str(e)}")
        return False

def test_flight_plan_analysis():
    """Test flight plan analysis endpoint"""
    print("\n🧪 Testing flight plan analysis endpoint...")
    
    url = "http://localhost:5001/api/flight-plan/analyze"
    data = {
        "departure": "KJFK",
        "arrival": "KLAX",
        "waypoints": ["KORD", "KDEN"]
    }
    
    try:
        response = requests.post(url, json=data, timeout=15)
        if response.status_code == 200:
            result = response.json()
            print("✅ Flight plan analysis test passed")
            print(f"   Route: {' → '.join(result.get('airports', []))}")
            print(f"   Weather data available: {len(result.get('weather_data', {}))}")
            print(f"   Briefing category: {result.get('briefing', {}).get('overall_category', 'N/A')}")
            print(f"   Visualizations: {len(result.get('visualizations', {}))}")
            return True
        else:
            print(f"❌ Flight plan analysis test failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Flight plan analysis test error: {str(e)}")
        return False

def test_weather_summary():
    """Test weather summary endpoint"""
    print("\n🧪 Testing weather summary endpoint...")
    
    url = "http://localhost:5001/api/weather/summary/KJFK"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print("✅ Weather summary test passed")
            print(f"   Airport: {result.get('airport', 'N/A')}")
            print(f"   Category: {result.get('category', 'N/A')}")
            print(f"   Summary available: {'summary' in result}")
            return True
        else:
            print(f"❌ Weather summary test failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Weather summary test error: {str(e)}")
        return False

def test_main_page():
    """Test main page loads"""
    print("\n🧪 Testing main page...")
    
    url = "http://localhost:5001/"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and "Aviation Weather Briefing" in response.text:
            print("✅ Main page test passed")
            print("   Page loads correctly with expected content")
            return True
        else:
            print(f"❌ Main page test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Main page test error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Aviation Weather Briefing System Tests")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:5001/", timeout=5)
    except:
        print("❌ Server not running on localhost:5001")
        print("   Please start the server with: python run.py")
        sys.exit(1)
    
    tests = [
        test_main_page,
        test_individual_weather,
        test_weather_summary,
        test_flight_plan_analysis
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The application is working correctly.")
        print("\n📋 Live weather data available for testing:")
        print("   • Try any valid ICAO airports: KJFK, KLAX, KORD, KDEN, KATL, KDFW, KSEA")
        print("   • Example route: KJFK → KORD → KDEN → KLAX")
        print("   • Real-time weather conditions from aviationweather.gov")
    else:
        print("⚠️  Some tests failed. Please check the server logs.")
        sys.exit(1)

if __name__ == '__main__':
    main()
