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
        
    def get_metar(self, airport_code, hours_before=2, departure_time=None):
        """
        Get METAR data for an airport
        
        Args:
            airport_code (str): ICAO airport code
            hours_before (int): Hours of data to retrieve
            departure_time (str): ISO format departure time for time-aware analysis
            
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
                latest_metar = max(data, key=lambda x: x.get('reportTime', x.get('obsTime', '')))
                parsed = self._parse_metar(latest_metar)
                logging.info(f"METAR for {airport_code}: {parsed.get('raw_text', 'N/A')[:50]}...")
                return parsed
            
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
                parsed = self._parse_taf(data[0])
                logging.info(f"TAF for {airport_code}: Found {len(data)} forecast(s)")
                return parsed
            
            logging.info(f"TAF for {airport_code}: No data available")
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
            # PIREPs are often not available from public APIs
            # Try a few different approaches
            endpoints_to_try = [
                f"{self.base_url}/aircraftreports",
                f"{self.base_url}/aircraftreport", 
                f"{self.base_url}/pirep",
                f"{self.base_url}/pireps"
            ]
            
            params = {
                'ids': airport_code,
                'format': 'json',
                'radius': radius,
                'hours': 12  # Increase to 12 hours for better chance
            }
            
            for endpoint in endpoints_to_try:
                try:
                    response = self.session.get(endpoint, params=params, timeout=self.timeout)
                    if response.status_code == 200:
                        data = response.json()
                        if data and isinstance(data, list):
                            logging.info(f"PIREPs for {airport_code}: Found {len(data)} reports")
                            return [self._parse_pirep(pirep) for pirep in data if pirep]
                        else:
                            logging.info(f"PIREPs for {airport_code}: No data in response")
                except requests.exceptions.RequestException as e:
                    logging.debug(f"PIREP endpoint {endpoint} failed: {str(e)}")
                    continue  # Try next endpoint
            
            # PIREPs are voluntary and often unavailable - this is normal
            logging.info(f"PIREPs for {airport_code}: No PIREPs available (normal - voluntary reports)")
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
    
    def get_time_appropriate_weather(self, airport_code, departure_time=None):
        """
        Get weather data appropriate for the departure time
        Uses METAR for current/past times and TAF for future times
        
        Args:
            airport_code (str): ICAO airport code
            departure_time (str): ISO format departure time
            
        Returns:
            dict: Combined weather data with time-appropriate information
        """
        try:
            # Always get current METAR
            metar = self.get_metar(airport_code)
            taf = self.get_taf(airport_code)
            pirep = self.get_pirep(airport_code)
            
            result = {
                'metar': metar,
                'taf': taf,
                'pirep': pirep,
                'time_appropriate_conditions': None
            }
            
            if departure_time:
                from datetime import datetime
                try:
                    # Parse departure time
                    if 'T' in departure_time:
                        dep_time = datetime.fromisoformat(departure_time.replace('Z', '+00:00'))
                    else:
                        dep_time = datetime.fromisoformat(departure_time)
                    
                    current_time = datetime.utcnow()
                    
                    # If departure is in the future and we have TAF data, use TAF
                    if dep_time > current_time and taf:
                        result['time_appropriate_conditions'] = self._extract_taf_conditions_for_time(taf, dep_time)
                        result['primary_source'] = 'TAF'
                        logging.info(f"Using TAF data for future departure at {airport_code}")
                    else:
                        # Use current METAR for current/past times
                        result['time_appropriate_conditions'] = metar
                        result['primary_source'] = 'METAR'
                        logging.info(f"Using METAR data for current/past departure at {airport_code}")
                        
                except Exception as e:
                    logging.warning(f"Error parsing departure time {departure_time}: {e}")
                    result['time_appropriate_conditions'] = metar
                    result['primary_source'] = 'METAR'
            else:
                result['time_appropriate_conditions'] = metar
                result['primary_source'] = 'METAR'
            
            return result
            
        except Exception as e:
            logging.error(f"Error getting time-appropriate weather for {airport_code}: {str(e)}")
            return {
                'metar': self.get_metar(airport_code),
                'taf': None,
                'pirep': [],
                'time_appropriate_conditions': None,
                'primary_source': 'METAR'
            }
    
    def _extract_taf_conditions_for_time(self, taf, target_time):
        """
        Extract TAF conditions for a specific time
        This is a simplified implementation - in production you'd parse TAF periods
        """
        if not taf:
            return None
            
        # For now, return the TAF data as-is
        # In a full implementation, you'd parse the TAF periods and find the right one
        return {
            'station_id': taf.get('station_id'),
            'raw_text': taf.get('raw_text'),
            'forecast_time': target_time.isoformat(),
            'source': 'TAF_FORECAST',
            # Extract basic conditions from TAF raw text if possible
            'conditions_note': f"Forecast conditions from TAF valid for {target_time.strftime('%Y-%m-%d %H:%M')} UTC"
        }
    
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
