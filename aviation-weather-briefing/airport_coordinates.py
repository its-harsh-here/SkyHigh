"""
Global airport coordinates database for route mapping
"""
import math

# Major global airports with coordinates
AIRPORT_COORDINATES = {
    # North America
    'KJFK': [40.6413, -73.7781],  # New York JFK
    'KLAX': [34.0522, -118.2437], # Los Angeles
    'KORD': [41.9742, -87.9073],  # Chicago O'Hare
    'KDEN': [39.8561, -104.6737], # Denver
    'KATL': [33.6407, -84.4277],  # Atlanta
    'KDFW': [32.8998, -97.0403],  # Dallas
    'KPHX': [33.4484, -112.0740], # Phoenix
    'KLAS': [36.0840, -115.1537], # Las Vegas
    'KSEA': [47.4502, -122.3088], # Seattle
    'KBOS': [42.3656, -71.0096],  # Boston
    'KMIA': [25.7959, -80.2870],  # Miami
    'KIAH': [29.9902, -95.3368],  # Houston
    
    # Europe
    'EGLL': [51.4700, -0.4543],   # London Heathrow
    'LFPG': [49.0097, 2.5479],    # Paris Charles de Gaulle
    'EDDF': [50.0379, 8.5622],    # Frankfurt
    'EHAM': [52.3105, 4.7683],    # Amsterdam Schiphol
    'LEMD': [40.4839, -3.5680],   # Madrid
    'LIRF': [41.8003, 12.2389],   # Rome Fiumicino
    'LOWW': [48.1103, 16.5697],   # Vienna
    'ESSA': [59.6519, 17.9186],   # Stockholm Arlanda
    'EKCH': [55.6181, 12.6561],   # Copenhagen
    'EDDM': [48.3537, 11.7750],   # Munich
    
    # Asia Pacific
    'VABB': [19.0896, 72.8656],   # Mumbai (Bombay)
    'VIDP': [28.5562, 77.1000],   # Delhi
    'VOMM': [13.0827, 80.2707],   # Chennai
    'VOBL': [12.9716, 77.5946],   # Bangalore
    'RJTT': [35.7647, 140.3864],  # Tokyo Haneda
    'RJAA': [35.7720, 140.3928],  # Tokyo Narita
    'RKSI': [37.4602, 126.4407],  # Seoul Incheon
    'VHHH': [22.3080, 113.9185],  # Hong Kong
    'WSSS': [1.3644, 103.9915],   # Singapore Changi
    'WIII': [6.1256, 106.6559],   # Jakarta
    'YBBN': [-27.3942, 153.1218], # Brisbane
    'YSSY': [-33.9399, 151.1753], # Sydney
    'YMML': [-37.6690, 144.8410], # Melbourne
    
    # Middle East
    'OMDB': [25.2532, 55.3657],   # Dubai
    'OERK': [24.9576, 46.6988],   # Riyadh
    'OTHH': [25.2731, 51.6080],   # Doha
    'OJAI': [29.9864, 47.9681],   # Kuwait
    'LTBA': [40.9769, 28.8146],   # Istanbul
    
    # Africa
    'HECA': [30.1127, 31.4000],   # Cairo
    'FACT': [-33.9648, 18.6017],  # Cape Town
    'FAOR': [-26.1367, 28.2411],  # Johannesburg
    'FALA': [-8.8583, 13.2312],   # Luanda
    
    # South America
    'SBGR': [-23.4356, -46.4731], # São Paulo
    'SCEL': [-33.3930, -70.7858], # Santiago
    'SAEZ': [-34.8222, -58.5358], # Buenos Aires
    'SKBO': [4.7016, -74.1469],   # Bogotá
}

def get_airport_coordinates(icao_code):
    """Get coordinates for an airport"""
    return AIRPORT_COORDINATES.get(icao_code.upper())

def calculate_distance_nm(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points in nautical miles using Haversine formula
    """
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth radius in nautical miles
    r_nm = 3440.065  # nautical miles
    
    return c * r_nm

def calculate_route_distance(airports):
    """Calculate total route distance in nautical miles"""
    total_distance = 0
    
    for i in range(len(airports) - 1):
        coords1 = get_airport_coordinates(airports[i])
        coords2 = get_airport_coordinates(airports[i + 1])
        
        if coords1 and coords2:
            distance = calculate_distance_nm(coords1[0], coords1[1], coords2[0], coords2[1])
            total_distance += distance
    
    return total_distance

def get_route_center(airports):
    """Get center point for route mapping"""
    valid_coords = []
    
    for airport in airports:
        coords = get_airport_coordinates(airport)
        if coords:
            valid_coords.append(coords)
    
    if not valid_coords:
        return [39.8283, -98.5795]  # Default center (US)
    
    # Calculate center
    avg_lat = sum(coord[0] for coord in valid_coords) / len(valid_coords)
    avg_lon = sum(coord[1] for coord in valid_coords) / len(valid_coords)
    
    return [avg_lat, avg_lon]
