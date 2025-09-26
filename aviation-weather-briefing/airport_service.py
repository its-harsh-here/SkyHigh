"""
Airport lookup service using live API data
"""
import requests
import json
import logging
from typing import List, Dict, Optional

class AirportService:
    """Service to lookup and validate airport codes using live data"""
    
    def __init__(self):
        # Using a free airport API service
        self.airport_api_base = "https://airport-info.p.rapidapi.com/airport"
        self.backup_api_base = "https://airportdb.io/api/v1/airport"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Aviation-Weather-Briefing/1.0'
        })
        
        # Cache for airport lookups to avoid repeated API calls
        self.airport_cache = {}
        
    def validate_airport_code(self, icao_code: str) -> bool:
        """
        Validate if an ICAO airport code exists
        
        Args:
            icao_code (str): ICAO airport code to validate
            
        Returns:
            bool: True if valid airport code
        """
        if not icao_code or len(icao_code) != 4:
            return False
            
        icao_code = icao_code.upper()
        
        # Check cache first
        if icao_code in self.airport_cache:
            return self.airport_cache[icao_code] is not None
        
        try:
            # Try to get airport info from airportdb.io (free API)
            response = self.session.get(
                f"{self.backup_api_base}/{icao_code}",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data and 'icao_code' in data:
                    self.airport_cache[icao_code] = data
                    return True
            
            # If that fails, try a simple validation by checking if aviationweather.gov has data
            weather_response = self.session.get(
                f"https://aviationweather.gov/api/data/metar?ids={icao_code}&format=json&hours=6",
                timeout=5
            )
            
            if weather_response.status_code == 200:
                weather_data = weather_response.json()
                if weather_data and len(weather_data) > 0:
                    # Cache basic info
                    self.airport_cache[icao_code] = {
                        'icao_code': icao_code,
                        'name': weather_data[0].get('name', 'Unknown Airport')
                    }
                    return True
            
            # Mark as invalid in cache
            self.airport_cache[icao_code] = None
            return False
            
        except Exception as e:
            logging.warning(f"Error validating airport code {icao_code}: {str(e)}")
            # Don't cache errors, allow retry
            return False
    
    def get_airport_info(self, icao_code: str) -> Optional[Dict]:
        """
        Get detailed airport information
        
        Args:
            icao_code (str): ICAO airport code
            
        Returns:
            dict: Airport information or None if not found
        """
        icao_code = icao_code.upper()
        
        # Check cache first
        if icao_code in self.airport_cache:
            return self.airport_cache[icao_code]
        
        # Validate and cache
        if self.validate_airport_code(icao_code):
            return self.airport_cache.get(icao_code)
        
        return None
    
    def search_airports(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for airports by name or code
        
        Args:
            query (str): Search query
            limit (int): Maximum number of results
            
        Returns:
            list: List of matching airports
        """
        results = []
        
        # If query looks like ICAO code, validate it
        if len(query) == 4 and query.isalpha():
            airport_info = self.get_airport_info(query.upper())
            if airport_info:
                results.append(airport_info)
        
        # For now, return basic validation result
        # In a production system, you'd implement full text search
        return results[:limit]
    
    def get_nearby_airports(self, icao_code: str, radius_nm: int = 100) -> List[Dict]:
        """
        Get airports within specified radius (placeholder for future implementation)
        
        Args:
            icao_code (str): Center airport ICAO code
            radius_nm (int): Radius in nautical miles
            
        Returns:
            list: List of nearby airports
        """
        # This would require a more comprehensive airport database
        # For now, return empty list
        return []
    
    def validate_route(self, airports: List[str]) -> Dict:
        """
        Validate a list of airport codes for a route
        
        Args:
            airports (list): List of ICAO airport codes
            
        Returns:
            dict: Validation results with valid/invalid airports
        """
        result = {
            'valid_airports': [],
            'invalid_airports': [],
            'airport_info': {}
        }
        
        for airport in airports:
            if self.validate_airport_code(airport):
                result['valid_airports'].append(airport.upper())
                result['airport_info'][airport.upper()] = self.get_airport_info(airport.upper())
            else:
                result['invalid_airports'].append(airport.upper())
        
        return result
