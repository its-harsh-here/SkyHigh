"""
Flight plan parser for extracting airports from flight plan text
"""
import re
import logging

class FlightPlanParser:
    """Parse flight plan text to extract airports"""
    
    def __init__(self):
        # ICAO airport code pattern (4 letters)
        self.icao_pattern = r'\b[A-Z]{4}\b'
        
    def parse_flight_plan_text(self, flight_plan_text):
        """
        Parse flight plan text to extract airport codes
        
        Args:
            flight_plan_text (str): Raw flight plan text
            
        Returns:
            list: List of airport codes found in the text
        """
        try:
            if not flight_plan_text:
                return []
            
            # Find all potential ICAO codes
            potential_codes = re.findall(self.icao_pattern, flight_plan_text.upper())
            
            # Filter out common false positives
            false_positives = {
                'FROM', 'DEST', 'DEPA', 'ARRI', 'ROUT', 'TIME', 'FUEL', 'ALTN',
                'RMKS', 'ENDM', 'ITEM', 'TYPE', 'EQUIP', 'WAKE', 'SURV'
            }
            
            valid_codes = [code for code in potential_codes if code not in false_positives]
            
            # Remove duplicates while preserving order
            seen = set()
            unique_codes = []
            for code in valid_codes:
                if code not in seen:
                    seen.add(code)
                    unique_codes.append(code)
            
            logging.info(f"Extracted airports from flight plan: {unique_codes}")
            return unique_codes
            
        except Exception as e:
            logging.error(f"Error parsing flight plan: {str(e)}")
            return []
    
    def extract_route_from_flight_plan(self, flight_plan_text):
        """
        Extract departure, arrival, and waypoints from flight plan
        
        Args:
            flight_plan_text (str): Raw flight plan text
            
        Returns:
            dict: Dictionary with departure, arrival, and waypoints
        """
        try:
            airports = self.parse_flight_plan_text(flight_plan_text)
            
            if len(airports) < 2:
                return {
                    'departure': None,
                    'arrival': None,
                    'waypoints': []
                }
            
            return {
                'departure': airports[0],
                'arrival': airports[-1],
                'waypoints': airports[1:-1]
            }
            
        except Exception as e:
            logging.error(f"Error extracting route from flight plan: {str(e)}")
            return {
                'departure': None,
                'arrival': None,
                'waypoints': []
            }
