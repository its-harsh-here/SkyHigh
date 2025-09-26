import re
import logging
from typing import List, Dict, Optional

class FlightPlanParser:
    """Parser for flight plans to extract airports and waypoints"""
    
    def __init__(self):
        # ICAO airport code pattern (4 letters)
        self.icao_pattern = re.compile(r'\b[A-Z]{4}\b')
        # Common flight plan formats
        self.route_keywords = ['DEP', 'DEST', 'ROUTE', 'VIA', 'DIRECT']
        
    def parse_flight_plan_text(self, flight_plan_text: str) -> List[str]:
        """
        Parse flight plan text to extract airports and waypoints
        
        Args:
            flight_plan_text (str): Raw flight plan text
            
        Returns:
            List[str]: List of ICAO codes in route order
        """
        try:
            # Clean and normalize the text
            text = flight_plan_text.upper().strip()
            
            # Try different parsing strategies
            airports = []
            
            # Strategy 1: Look for structured flight plan format
            structured_airports = self._parse_structured_format(text)
            if structured_airports:
                airports = structured_airports
            else:
                # Strategy 2: Extract all ICAO codes and filter
                airports = self._extract_icao_codes(text)
            
            # Remove duplicates while preserving order
            unique_airports = []
            seen = set()
            for airport in airports:
                if airport not in seen:
                    unique_airports.append(airport)
                    seen.add(airport)
            
            return unique_airports
            
        except Exception as e:
            logging.error(f"Error parsing flight plan: {str(e)}")
            return []
    
    def parse_manual_input(self, departure: str, arrival: str, waypoints: List[str] = None) -> List[str]:
        """
        Parse manually entered flight plan data
        
        Args:
            departure (str): Departure airport ICAO code
            arrival (str): Arrival airport ICAO code  
            waypoints (List[str]): Optional waypoints
            
        Returns:
            List[str]: List of ICAO codes in route order
        """
        try:
            airports = []
            
            # Validate and add departure
            if self._is_valid_icao(departure):
                airports.append(departure.upper())
            
            # Add waypoints if provided
            if waypoints:
                for waypoint in waypoints:
                    waypoint = waypoint.strip().upper()
                    if waypoint and self._is_valid_icao(waypoint):
                        airports.append(waypoint)
            
            # Validate and add arrival
            if self._is_valid_icao(arrival):
                airports.append(arrival.upper())
            
            return airports
            
        except Exception as e:
            logging.error(f"Error parsing manual input: {str(e)}")
            return []
    
    def _parse_structured_format(self, text: str) -> List[str]:
        """Parse structured flight plan formats (ICAO, FAA, etc.)"""
        airports = []
        
        # Look for departure airport
        dep_match = re.search(r'(?:DEP|DEPARTURE|FROM)[:\s]+([A-Z]{4})', text)
        if dep_match:
            airports.append(dep_match.group(1))
        
        # Look for route section
        route_match = re.search(r'(?:ROUTE|VIA)[:\s]+(.*?)(?:DEST|ARRIVAL|TO|$)', text, re.DOTALL)
        if route_match:
            route_text = route_match.group(1)
            route_airports = self.icao_pattern.findall(route_text)
            airports.extend(route_airports)
        
        # Look for destination airport
        dest_match = re.search(r'(?:DEST|DESTINATION|ARRIVAL|TO)[:\s]+([A-Z]{4})', text)
        if dest_match:
            airports.append(dest_match.group(1))
        
        return airports
    
    def _extract_icao_codes(self, text: str) -> List[str]:
        """Extract all potential ICAO codes from text"""
        # Find all 4-letter codes
        potential_codes = self.icao_pattern.findall(text)
        
        # Filter out common false positives
        false_positives = {
            'METAR', 'SPECI', 'AUTO', 'COR', 'NOSIG', 'TEMPO', 'BECMG',
            'FROM', 'TILL', 'TIME', 'DATE', 'WIND', 'GUST', 'CALM',
            'CAVOK', 'CLEAR', 'FEET', 'MILE', 'KNOT', 'DEGC', 'INHG'
        }
        
        filtered_codes = [code for code in potential_codes if code not in false_positives]
        
        return filtered_codes
    
    def _is_valid_icao(self, code: str) -> bool:
        """
        Validate if a code looks like a valid ICAO airport code
        
        Args:
            code (str): Code to validate
            
        Returns:
            bool: True if valid ICAO format
        """
        if not code or len(code) != 4:
            return False
        
        # Must be all letters
        if not code.isalpha():
            return False
        
        # Check against common false positives
        false_positives = {
            'METAR', 'SPECI', 'AUTO', 'COR', 'NOSIG', 'TEMPO', 'BECMG',
            'FROM', 'TILL', 'TIME', 'DATE', 'WIND', 'GUST', 'CALM',
            'CAVOK', 'CLEAR', 'FEET', 'MILE', 'KNOT', 'DEGC', 'INHG'
        }
        
        return code.upper() not in false_positives
    
    def validate_route(self, airports: List[str]) -> Dict[str, any]:
        """
        Validate a parsed route for completeness and logic
        
        Args:
            airports (List[str]): List of airport codes
            
        Returns:
            Dict: Validation results with warnings and suggestions
        """
        validation = {
            'is_valid': True,
            'warnings': [],
            'suggestions': [],
            'airport_count': len(airports)
        }
        
        # Check minimum requirements
        if len(airports) < 2:
            validation['is_valid'] = False
            validation['warnings'].append("Route must have at least departure and arrival airports")
        
        # Check for duplicate consecutive airports
        for i in range(len(airports) - 1):
            if airports[i] == airports[i + 1]:
                validation['warnings'].append(f"Duplicate consecutive airport: {airports[i]}")
        
        # Check route length
        if len(airports) > 20:
            validation['warnings'].append("Route has many waypoints - verify accuracy")
        
        # Suggest adding waypoints for long routes
        if len(airports) == 2:
            validation['suggestions'].append("Consider adding waypoints for long routes")
        
        return validation
    
    def extract_airports_from_coordinates(self, coordinates: List[tuple]) -> List[str]:
        """
        Extract nearest airports from a list of coordinates
        This is a placeholder for future enhancement with airport database
        
        Args:
            coordinates (List[tuple]): List of (lat, lon) tuples
            
        Returns:
            List[str]: List of nearest airport codes
        """
        # This would require an airport database with coordinates
        # For now, return empty list as placeholder
        logging.info("Coordinate-based airport extraction not yet implemented")
        return []
