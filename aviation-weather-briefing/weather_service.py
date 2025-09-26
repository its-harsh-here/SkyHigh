import requests
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import logging
from config import Config

class WeatherService:
    """Service to fetch weather data from aviationweather.gov API"""
    
    def __init__(self):
        self.base_url = "https://aviationweather.gov/api/data"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Aviation-Weather-Briefing/1.0'
        })
        self.timeout = Config.REQUEST_TIMEOUT
        
    def get_metar(self, airport_code, hours_before=2):
        """
        Get METAR data for an airport
        
        Args:
            airport_code (str): ICAO airport code
            hours_before (int): Hours of data to retrieve
            
        Returns:
            dict: Parsed METAR data or None if error
        """
        try:
            # Calculate start time
            start_time = datetime.utcnow() - timedelta(hours=hours_before)
            start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            params = {
                'ids': airport_code,
                'format': 'json',
                'hours': hours_before
            }
            
            response = self.session.get(f"{self.base_url}/metar", params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if data and len(data) > 0:
                # Return the most recent METAR
                latest_metar = max(data, key=lambda x: x.get('obsTime', ''))
                return self._parse_metar(latest_metar)
            
            return None
            
        except Exception as e:
            logging.error(f"Error fetching METAR for {airport_code}: {str(e)}")
            return None
    
    def get_taf(self, airport_code):
        """
        Get TAF (Terminal Aerodrome Forecast) data for an airport
        
        Args:
            airport_code (str): ICAO airport code
            
        Returns:
            dict: Parsed TAF data or None if error
        """
        try:
            params = {
                'ids': airport_code,
                'format': 'json'
            }
            
            response = self.session.get(f"{self.base_url}/taf", params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if data and len(data) > 0:
                return self._parse_taf(data[0])
            
            return None
            
        except Exception as e:
            logging.error(f"Error fetching TAF for {airport_code}: {str(e)}")
            return None
    
    def get_pirep(self, airport_code, radius=50):
        """
        Get PIREP (Pilot Reports) data near an airport
        
        Args:
            airport_code (str): ICAO airport code
            radius (int): Search radius in nautical miles
            
        Returns:
            list: List of PIREPs or empty list if error
        """
        try:
            params = {
                'ids': airport_code,
                'format': 'json',
                'radius': radius,
                'hours': 6  # Last 6 hours
            }
            
            response = self.session.get(f"{self.base_url}/aircraftreports", params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if data:
                return [self._parse_pirep(pirep) for pirep in data]
            
            return []
            
        except Exception as e:
            logging.error(f"Error fetching PIREPs for {airport_code}: {str(e)}")
            return []
    
    def get_sigmet(self, airport_code):
        """
        Get SIGMET data for an area
        
        Args:
            airport_code (str): ICAO airport code
            
        Returns:
            list: List of SIGMETs or empty list if error
        """
        try:
            params = {
                'format': 'json',
                'hazards': 'conv,turb,ice,ifr'  # Common hazards
            }
            
            response = self.session.get(f"{self.base_url}/airsigmet", params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if data:
                # Filter SIGMETs relevant to the airport area
                return [self._parse_sigmet(sigmet) for sigmet in data]
            
            return []
            
        except Exception as e:
            logging.error(f"Error fetching SIGMETs: {str(e)}")
            return []
    
    def _parse_metar(self, metar_data):
        """Parse METAR JSON data into structured format"""
        try:
            # Handle visibility - API returns "10+" for visibility >= 10 SM
            visibility = metar_data.get('visib', None)
            if visibility == "10+":
                visibility = 10.0
            elif visibility and isinstance(visibility, str):
                try:
                    visibility = float(visibility)
                except:
                    visibility = None
            
            # Convert obsTime from timestamp to ISO string if needed
            obs_time = metar_data.get('reportTime', metar_data.get('obsTime', ''))
            
            # Handle ceiling - calculate from cloud layers if not directly provided
            ceiling = metar_data.get('ceiling', None)
            if not ceiling and metar_data.get('clouds'):
                # Find lowest BKN or OVC layer
                for cloud in metar_data.get('clouds', []):
                    if cloud.get('cover') in ['BKN', 'OVC']:
                        ceiling = cloud.get('base')
                        break
            
            parsed = {
                'raw_text': metar_data.get('rawOb', ''),
                'station_id': metar_data.get('icaoId', ''),
                'observation_time': obs_time,
                'temperature': metar_data.get('temp', None),
                'dewpoint': metar_data.get('dewp', None),
                'wind_direction': metar_data.get('wdir', None),
                'wind_speed': metar_data.get('wspd', None),
                'wind_gust': metar_data.get('wgst', None),  # Note: API might not have this field
                'visibility': visibility,
                'altimeter': metar_data.get('altim', None),
                'flight_category': metar_data.get('fltCat', 'UNKNOWN'),  # Correct field name
                'clouds': metar_data.get('clouds', []),
                'weather_conditions': metar_data.get('wxString', ''),
                'ceiling': ceiling
            }
            
            return parsed
            
        except Exception as e:
            logging.error(f"Error parsing METAR data: {str(e)}")
            logging.error(f"Raw METAR data: {metar_data}")
            return None
    
    def _parse_taf(self, taf_data):
        """Parse TAF JSON data into structured format"""
        try:
            parsed = {
                'raw_text': taf_data.get('rawTAF', ''),
                'station_id': taf_data.get('icaoId', ''),
                'issue_time': taf_data.get('issueTime', ''),
                'valid_time_from': taf_data.get('validTimeFrom', ''),
                'valid_time_to': taf_data.get('validTimeTo', ''),
                'forecasts': taf_data.get('forecast', [])
            }
            
            return parsed
            
        except Exception as e:
            logging.error(f"Error parsing TAF data: {str(e)}")
            return None
    
    def _parse_pirep(self, pirep_data):
        """Parse PIREP JSON data into structured format"""
        try:
            parsed = {
                'raw_text': pirep_data.get('rawOb', ''),
                'receipt_time': pirep_data.get('rcptTime', ''),
                'observation_time': pirep_data.get('obsTime', ''),
                'aircraft_type': pirep_data.get('acType', ''),
                'altitude': pirep_data.get('alt', None),
                'turbulence': pirep_data.get('turb', []),
                'icing': pirep_data.get('ice', []),
                'visibility': pirep_data.get('vis', None),
                'weather': pirep_data.get('wx', []),
                'clouds': pirep_data.get('clouds', []),
                'temperature': pirep_data.get('temp', None)
            }
            
            return parsed
            
        except Exception as e:
            logging.error(f"Error parsing PIREP data: {str(e)}")
            return None
    
    def _parse_sigmet(self, sigmet_data):
        """Parse SIGMET JSON data into structured format"""
        try:
            parsed = {
                'raw_text': sigmet_data.get('rawAirsigmet', ''),
                'valid_time_from': sigmet_data.get('validTimeFrom', ''),
                'valid_time_to': sigmet_data.get('validTimeTo', ''),
                'hazard': sigmet_data.get('hazard', ''),
                'severity': sigmet_data.get('severity', ''),
                'altitude_low': sigmet_data.get('altitudeLow', None),
                'altitude_high': sigmet_data.get('altitudeHigh', None),
                'movement': sigmet_data.get('movement', ''),
                'area': sigmet_data.get('area', [])
            }
            
            return parsed
            
        except Exception as e:
            logging.error(f"Error parsing SIGMET data: {str(e)}")
            return None
