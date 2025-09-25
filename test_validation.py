import requests
import json
import time

BASE_URL = "http://localhost:5000"

def run_test(test_name, test_func):
    """Run a single test and display results"""
    print(f"\n{'='*50}")
    print(f"🧪 {test_name}")
    print(f"{'='*50}")
    
    try:
        result = test_func()
        if result:
            print("✅ PASSED")
        else:
            print("❌ FAILED")
        return result
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_1_basic_clear():
    """Test Case 1: Basic Weather Fetch (Clear)"""
    response = requests.get(f"{BASE_URL}/api/weather?airports=KJFK")
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2)}")
    
    return (response.status_code == 200 and 
            'KJFK' in data and 
            'metar' in data['KJFK'])

def test_2_multiple_airports():
    """Test Case 2: Multiple Airports"""
    response = requests.get(f"{BASE_URL}/api/weather?airports=KJFK,KORD,KDEN")
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Airports found: {list(data.keys())}")
    
    return (response.status_code == 200 and 
            len(data) >= 3 and
            all(icao in data for icao in ['KJFK', 'KORD', 'KDEN']))

def test_3_flight_plan():
    """Test Case 3: Flight Plan Analysis"""
    payload = {
        "departure": "KJFK",
        "destination": "KLAX", 
        "waypoints": ["KORD"]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/flight-plan",
        json=payload,
        headers={'Content-Type': 'application/json'}
    )
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Route category: {data.get('route', {}).get('overall_category', 'N/A')}")
    
    return (response.status_code == 200 and 
            'route' in data and 
            'weather' in data)

def test_4_invalid_airport():
    """Test Case 4: Invalid Airport Code"""
    response = requests.get(f"{BASE_URL}/api/weather?airports=INVALID")
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2)}")
    
    # Should still return 200 but with empty data
    return response.status_code == 200

def test_5_empty_request():
    """Test Case 5: Empty Airport Request"""
    response = requests.get(f"{BASE_URL}/api/weather?airports=")
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Error: {data.get('error', 'N/A')}")
    
    return (response.status_code == 400 and 
            'error' in data)

def test_6_international():
    """Test Case 6: International Airport"""
    response = requests.get(f"{BASE_URL}/api/weather?airports=EGLL")
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Airport: {data.get('EGLL', {}).get('metar', {}).get('name', 'N/A')}")
    
    return (response.status_code == 200 and 
            'EGLL' in data)

def test_7_categorization():
    """Test Case 7: Weather Categorization"""
    response = requests.get(f"{BASE_URL}/api/weather?airports=KJFK,KORD,KDEN")
    data = response.json()
    
    categories = {}
    for icao, weather_data in data.items():
        category = weather_data.get('metar', {}).get('category', 'Unknown')
        categories[icao] = category
    
    print(f"Categories: {categories}")
    
    # Should have different categories
    unique_categories = set(categories.values())
    return len(unique_categories) >= 2

def test_8_ui_accessibility():
    """Test Case 8: UI Accessibility"""
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")
    
    # Check if HTML is returned
    return (response.status_code == 200 and 
            'text/html' in response.headers.get('content-type', ''))

def test_9_concurrent_requests():
    """Test Case 9: Concurrent Request Handling"""
    import concurrent.futures
    
    def make_request():
        return requests.get(f"{BASE_URL}/api/weather?airports=KJFK")
    
    # Make 5 concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request) for _ in range(5)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    success_count = sum(1 for r in results if r.status_code == 200)
    print(f"Successful requests: {success_count}/5")
    
    return success_count >= 4  # Allow 1 failure

def test_10_performance():
    """Test Case 10: Performance Test"""
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/api/weather?airports=KJFK,KORD,KDEN,EGLL,VIDP")
    end_time = time.time()
    
    response_time = end_time - start_time
    print(f"Response time: {response_time:.2f} seconds")
    print(f"Status: {response.status_code}")
    
    # Should complete within 15 seconds
    return response.status_code == 200 and response_time < 15

def main():
    """Run all test cases"""
    print("🛩️  Aviation Weather Briefing System - Validation Tests")
    print("="*60)
    
    tests = [
        ("Basic Weather Fetch (Clear)", test_1_basic_clear),
        ("Multiple Airports", test_2_multiple_airports),  
        ("Flight Plan Analysis", test_3_flight_plan),
        ("Invalid Airport Code", test_4_invalid_airport),
        ("Empty Request Handling", test_5_empty_request),
        ("International Airport", test_6_international),
        ("Weather Categorization", test_7_categorization),
        ("UI Accessibility", test_8_ui_accessibility),
        ("Concurrent Requests", test_9_concurrent_requests),
        ("Performance Test", test_10_performance)
    ]
    
    passed = 0
    for test_name, test_func in tests:
        if run_test(test_name, test_func):
            passed += 1
        time.sleep(1)  # Brief pause between tests
    
    print(f"\n{'='*60}")
    print(f"🏆 FINAL RESULTS: {passed}/{len(tests)} tests passed")
    
    if passed >= 8:
        print("🎉 System is hackathon-ready!")
    elif passed >= 6:
        print("⚠️  System mostly working, minor issues detected")
    else:
        print("❌ System has significant issues, review failures")

if __name__ == "__main__":
    main()
