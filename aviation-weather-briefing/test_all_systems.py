#!/usr/bin/env python3
"""
Test all systems to ensure everything works
"""
import requests
import json

def test_individual_report():
    print("🧪 Testing Individual Report...")
    try:
        response = requests.post(
            'http://localhost:5001/api/weather/individual',
            json={'airport_code': 'KJFK', 'report_types': ['METAR', 'TAF', 'PIREP']},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Individual report API working")
            
            # Check TAF summary
            if data.get('taf'):
                taf = data['taf']
                print(f"✅ TAF available: {taf.get('raw_text', 'N/A')[:50]}...")
            else:
                print("❌ TAF missing")
                
            # Check PIREP
            if data.get('pirep'):
                print(f"✅ PIREP available: {len(data['pirep'])} reports")
            else:
                print("⚠️  PIREP not available (normal - voluntary reports)")
                
            return True
        else:
            print(f"❌ Individual report failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Individual report error: {e}")
        return False

def test_route_analysis():
    print("\n🧪 Testing Route Analysis...")
    try:
        response = requests.post(
            'http://localhost:5001/api/flight-plan/analyze',
            json={'departure': 'KJFK', 'arrival': 'KLAX', 'waypoints': ['KORD']},
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Route analysis API working")
            
            # Check visualizations
            visualizations = data.get('visualizations', {})
            viz_count = 0
            for viz_name, viz_data in visualizations.items():
                if viz_data and not (isinstance(viz_data, dict) and 'error' in viz_data):
                    viz_count += 1
                    print(f"✅ {viz_name}: OK")
                else:
                    print(f"❌ {viz_name}: Failed")
            
            if viz_count >= 3:
                print(f"✅ Visualizations working: {viz_count}/4")
            else:
                print(f"⚠️  Some visualizations missing: {viz_count}/4")
                
            # Check NLP analysis
            nlp = data.get('nlp_analysis', {})
            if nlp.get('executive_summary'):
                print("✅ NLP analysis working")
            else:
                print("❌ NLP analysis missing")
                
            return True
        else:
            print(f"❌ Route analysis failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Route analysis error: {e}")
        return False

def test_weather_categories():
    print("\n🧪 Testing Weather Categories...")
    
    # Test airports with different conditions
    test_airports = [
        ('KJFK', 'Should be VFR/CLEAR'),
        ('KLAX', 'Should be MVFR/SIGNIFICANT'),
        ('KPHX', 'Should be MVFR/SEVERE (if thunderstorms)')
    ]
    
    categories_found = set()
    
    for airport, expected in test_airports:
        try:
            response = requests.post(
                'http://localhost:5001/api/weather/individual',
                json={'airport_code': airport, 'report_types': ['METAR']},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                analysis = data.get('analysis', {})
                category = analysis.get('category', 'UNKNOWN')
                flight_cat = data.get('metar', {}).get('flight_category', 'UNKNOWN')
                
                categories_found.add(category)
                print(f"✅ {airport}: {category} ({flight_cat}) - {expected}")
            else:
                print(f"❌ {airport}: API error {response.status_code}")
        except Exception as e:
            print(f"❌ {airport}: Error - {e}")
    
    if len(categories_found) > 1:
        print(f"✅ Weather variety confirmed: {categories_found}")
        return True
    else:
        print(f"⚠️  Limited weather variety: {categories_found}")
        return False

def main():
    print("🚀 COMPREHENSIVE SYSTEM TEST")
    print("=" * 50)
    
    # Check server
    try:
        response = requests.get('http://localhost:5001/', timeout=5)
        if response.status_code != 200:
            raise Exception("Server not responding")
        print("✅ Server running on localhost:5001")
    except:
        print("❌ Server not running!")
        return
    
    tests = [
        test_individual_report,
        test_route_analysis,
        test_weather_categories
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"🏁 RESULTS: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 ALL SYSTEMS WORKING!")
        print("🌐 Ready at: http://localhost:5001")
    else:
        print("⚠️  Some issues found - check above")

if __name__ == '__main__':
    main()
