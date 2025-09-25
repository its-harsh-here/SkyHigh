import asyncio
import httpx
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import re
from models.extended_weather_models import *
from services.categorization_service import WeatherCategorizationService
from utils.weather_parser import MetarParser
from config import settings

class ComprehensiveWeatherService:
    """Service for fetching and processing all aviation weather products"""
    
    def __init__(self):
        self.base_url = settings.AVIATION_WEATHER_BASE_URL
        self.categorizer = WeatherCategorizationService()
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def fetch_all_weather_data(self, station_id: str, radius_nm: int = 50) -> ComprehensiveWeatherBriefing:
        """Fetch all available weather products for a station"""
        
        # Fetch all products concurrently
        tasks = {
            'metar': self._fetch_metar(station_id),
            'taf': self._fetch_taf(station_id),
            'pirep': self._fetch_pireps(station_id, radius_nm),
            'sigmet': self._fetch_sigmets(station_id, radius_nm),
            'gairmet': self._fetch_gairmets(station_id, radius_nm),
            'airmet': self._fetch_airmets(station_id, radius_nm),
            'cwa': self._fetch_cwas(station_id, radius_nm)
        }
        
        # Execute all requests concurrently
        results = {}
        for product_type, task in tasks.items():
            try:
                results[product_type] = await task
            except Exception as e:
                print(f"Error fetching {product_type}: {e}")
                results[product_type] = None
        
        # Create comprehensive briefing
        briefing = await self._create_comprehensive_briefing(station_id, results)
        return briefing
    
    async def _fetch_metar(self, station_id: str) -> Optional[MetarData]:
        """Fetch METAR data"""
        try:
            response = await self.client.get(
                f"{self.base_url}/metar",
                params={'ids': station_id, 'format': 'json', 'taf': 'false'}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    item = data[0]
                    raw_text = item.get('rawOb', '')
                    if raw_text:
                        metar = MetarParser.parse_metar(raw_text, station_id)
                        metar.category = self.categorizer.categorize_metar(metar)
                        return metar
            return None
            
        except Exception as e:
            print(f"METAR fetch error: {e}")
            return None
    
    async def _fetch_taf(self, station_id: str) -> Optional[TafData]:
        """Fetch TAF data"""
        try:
            response = await self.client.get(
                f"{self.base_url}/taf",
                params={'ids': station_id, 'format': 'json'}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    item = data[0]
                    taf = TafData(
                        station_id=station_id,
                        issue_time=datetime.fromisoformat(item.get('issueTime', '').replace('Z', '+00:00')),
                        valid_from=datetime.fromisoformat(item.get('validTimeFrom', '').replace('Z', '+00:00')),
                        valid_until=datetime.fromisoformat(item.get('validTimeTo', '').replace('Z', '+00:00')),
                        raw_text=item.get('rawTAF', ''),
                        category=WeatherCategory.CLEAR  # Would need proper TAF parsing
                    )
                    return taf
            return None
            
        except Exception as e:
            print(f"TAF fetch error: {e}")
            return None
    
    async def _fetch_pireps(self, station_id: str, radius_nm: int) -> List[PirepData]:
        """Fetch PIREP data within radius"""
        try:
            # PIREPs are fetched by area, not specific station
            response = await self.client.get(
                f"{self.base_url}/aircraftreport", 
                params={
                    'format': 'json',
                    'distance': f'{radius_nm}',
                    'coord': f'{self._get_station_coords(station_id)}'  # Would need station lookup
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                pireps = []
                
                for item in data:
                    try:
                        pirep = self._parse_pirep(item, station_id)
                        if pirep:
                            pireps.append(pirep)
                    except Exception as e:
                        print(f"PIREP parse error: {e}")
                        continue
                
                return pireps
            return []
            
        except Exception as e:
            print(f"PIREP fetch error: {e}")
            return []
    
    async def _fetch_sigmets(self, station_id: str, radius_nm: int) -> List[SigmetData]:
        """Fetch SIGMET data"""
        try:
            response = await self.client.get(
                f"{self.base_url}/sigmet",
                params={'format': 'json'}
            )
            
            if response.status_code == 200:
                data = response.json()
                sigmets = []
                
                for item in data:
                    try:
                        sigmet = self._parse_sigmet(item)
                        if sigmet and self._is_relevant_to_station(sigmet, station_id, radius_nm):
                            sigmets.append(sigmet)
                    except Exception as e:
                        print(f"SIGMET parse error: {e}")
                        continue
                
                return sigmets
            return []
            
        except Exception as e:
            print(f"SIGMET fetch error: {e}")
            return []
    
    async def _fetch_gairmets(self, station_id: str, radius_nm: int) -> List[GAirmetData]:
        """Fetch G-AIRMET data"""
        try:
            response = await self.client.get(
                f"{self.base_url}/gairmet",
                params={'format': 'json'}
            )
            
            if response.status_code == 200:
                data = response.json()
                gairmets = []
                
                for item in data:
                    try:
                        gairmet = self._parse_gairmet(item)
                        if gairmet and self._is_relevant_to_station(gairmet, station_id, radius_nm):
                            gairmets.append(gairmet)
                    except Exception as e:
                        print(f"G-AIRMET parse error: {e}")
                        continue
                
                return gairmets
            return []
            
        except Exception as e:
            print(f"G-AIRMET fetch error: {e}")
            return []
    
    async def _fetch_airmets(self, station_id: str, radius_nm: int) -> List[AirmetData]:
        """Fetch AIRMET data"""
        try:
            response = await self.client.get(
                f"{self.base_url}/airmet",
                params={'format': 'json'}
            )
            
            if response.status_code == 200:
                data = response.json()
                airmets = []
                
                for item in data:
                    try:
                        airmet = self._parse_airmet(item)
                        if airmet and self._is_relevant_to_station(airmet, station_id, radius_nm):
                            airmets.append(airmet)
                    except Exception as e:
                        print(f"AIRMET parse error: {e}")
                        continue
                
                return airmets
            return []
            
        except Exception as e:
            print(f"AIRMET fetch error: {e}")
            return []
    
    async def _fetch_cwas(self, station_id: str, radius_nm: int) -> List[CwaData]:
        """Fetch CWA data"""  
        try:
            response = await self.client.get(
                f"{self.base_url}/cwa",
                params={'format': 'json'}
            )
            
            if response.status_code == 200:
                data = response.json()
                cwas = []
                
                for item in data:
                    try:
                        cwa = self._parse_cwa(item)
                        if cwa and self._is_relevant_to_station(cwa, station_id, radius_nm):
                            cwas.append(cwa)
                    except Exception as e:
                        print(f"CWA parse error: {e}")
                        continue
                
                return cwas
            return []
            
        except Exception as e:
            print(f"CWA fetch error: {e}")
            return []
    
    def _parse_pirep(self, item: Dict, station_id: str) -> Optional[PirepData]:
        """Parse PIREP from API response"""
        try:
            raw_text = item.get('rawOb', '')
            if not raw_text:
                return None
            
            pirep = PirepData(
                station_id=station_id,
                report_time=datetime.fromisoformat(item.get('obsTime', '').replace('Z', '+00:00')),
                raw_text=raw_text,
                aircraft_type=item.get('acType'),
                altitude=item.get('fltlvl'),
                category=WeatherCategory.CLEAR  # Will be determined by content analysis
            )
            
            # Analyze PIREP content for weather conditions
            pirep.category = self._categorize_pirep(raw_text)
            
            return pirep
            
        except Exception as e:
            print(f"PIREP parsing error: {e}")
            return None
    
    def _parse_sigmet(self, item: Dict) -> Optional[SigmetData]:
        """Parse SIGMET from API response"""
        try:
            sigmet = SigmetData(
                identifier=item.get('id', ''),
                issue_time=datetime.fromisoformat(item.get('issueTime', '').replace('Z', '+00:00')),
                valid_from=datetime.fromisoformat(item.get('validTimeFrom', '').replace('Z', '+00:00')),
                valid_until=datetime.fromisoformat(item.get('validTimeTo', '').replace('Z', '+00:00')),
                raw_text=item.get('rawSigmet', ''),
                phenomenon=item.get('hazard', ''),
                severity=item.get('severity', '')
            )
            
            return sigmet
            
        except Exception as e:
            print(f"SIGMET parsing error: {e}")
            return None
    
    def _parse_gairmet(self, item: Dict) -> Optional[GAirmetData]:
        """Parse G-AIRMET from API response"""
        try:
            gairmet = GAirmetData(
                identifier=item.get('id', ''),
                issue_time=datetime.fromisoformat(item.get('issueTime', '').replace('Z', '+00:00')),
                valid_from=datetime.fromisoformat(item.get('validTimeFrom', '').replace('Z', '+00:00')),
                valid_until=datetime.fromisoformat(item.get('validTimeTo', '').replace('Z', '+00:00')),
                raw_text=item.get('rawGAirmet', ''),
                hazard_type=item.get('hazard', ''),
                base_altitude=item.get('base'),
                top_altitude=item.get('top'),
                category=WeatherCategory.SIGNIFICANT  # Default for G-AIRMETs
            )
            
            return gairmet
            
        except Exception as e:
            print(f"G-AIRMET parsing error: {e}")
            return None
    
    def _parse_airmet(self, item: Dict) -> Optional[AirmetData]:
        """Parse AIRMET from API response"""
        try:
            airmet = AirmetData(
                identifier=item.get('id', ''),
                issue_time=datetime.fromisoformat(item.get('issueTime', '').replace('Z', '+00:00')),
                valid_from=datetime.fromisoformat(item.get('validTimeFrom', '').replace('Z', '+00:00')),
                valid_until=datetime.fromisoformat(item.get('validTimeTo', '').replace('Z', '+00:00')),
                raw_text=item.get('rawAirmet', ''),
                series=item.get('series', ''),
                hazard_type=item.get('hazard', ''),
                category=WeatherCategory.SIGNIFICANT  # Default for AIRMETs
            )
            
            return airmet
            
        except Exception as e:
            print(f"AIRMET parsing error: {e}")
            return None
    
    def _parse_cwa(self, item: Dict) -> Optional[CwaData]:
        """Parse CWA from API response"""
        try:
            cwa = CwaData(
                identifier=item.get('id', ''),
                issue_time=datetime.fromisoformat(item.get('issueTime', '').replace('Z', '+00:00')),
                valid_from=datetime.fromisoformat(item.get('validTimeFrom', '').replace('Z', '+00:00')),
                valid_until=datetime.fromisoformat(item.get('validTimeTo', '').replace('Z', '+00:00')),
                raw_text=item.get('rawCwa', ''),
                center=item.get('cwsu', ''),
                phenomenon=item.get('hazard', ''),
                category=WeatherCategory.SIGNIFICANT  # Default for CWAs
            )
            
            return cwa
            
        except Exception as e:
            print(f"CWA parsing error: {e}")
            return None
    
    async def _create_comprehensive_briefing(
        self, 
        station_id: str, 
        weather_data: Dict
    ) -> ComprehensiveWeatherBriefing:
        """Create intelligent comprehensive weather briefing"""
        
        # Determine available products
        available_products = []
        for product_type, data in weather_data.items():
            if data is not None:
                if isinstance(data, list) and len(data) > 0:
                    available_products.append(WeatherProductType(product_type.upper()))
                elif not isinstance(data, list):
                    available_products.append(WeatherProductType(product_type.upper()))
        
        # Determine primary source using intelligent algorithm
        primary_source, confidence = self._determine_primary_source(weather_data)
        
        # Generate pilot-focused summary
        pilot_summary = self._generate_pilot_summary(weather_data, primary_source)
        
        # Determine overall category
        overall_category = self._determine_overall_category(weather_data)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(weather_data, overall_category)
        
        # Extract current conditions and forecast
        current_conditions = self._extract_current_conditions(weather_data, primary_source)
        forecast = self._extract_forecast(weather_data)
        
        # Extract hazards
        hazards = self._extract_hazards(weather_data)
        
        briefing = ComprehensiveWeatherBriefing(
            station_id=station_id,
            primary_source=primary_source,
            overall_category=overall_category,
            confidence_score=confidence,
            pilot_summary=pilot_summary,
            recommendations=recommendations,
            current_conditions=current_conditions,
            forecast=forecast,
            hazards=hazards,
            metar_data=weather_data.get('metar'),
            taf_data=weather_data.get('taf'),
            pirep_data=weather_data.get('pirep', []),
            sigmet_data=weather_data.get('sigmet', []),
            gairmet_data=weather_data.get('gairmet', []),
            airmet_data=weather_data.get('airmet', []),
            cwa_data=weather_data.get('cwa', []),
            available_products=available_products
        )
        
        return briefing
    
    def _determine_primary_source(self, weather_data: Dict) -> Tuple[WeatherProductType, float]:
        """Determine the most reliable source for current conditions"""
        
        source_scores = {}
        
        for product_name, data in weather_data.items():
            if data is None:
                continue
                
            try:
                product_type = WeatherProductType(product_name.upper())
                priority_info = WEATHER_PRIORITIES.get(product_type)
                
                if not priority_info:
                    continue
                
                # Calculate base score
                base_score = priority_info.confidence * (8 - priority_info.priority)
                
                # Apply recency weight for time-sensitive products
                recency_bonus = 1.0  # Default
                
                if product_name == 'pirep' and isinstance(data, list) and data:
                    # PIREPs get bonus for being recent
                    latest_pirep = max(data, key=lambda p: p.report_time)
                    age_hours = (datetime.utcnow() - latest_pirep.report_time).total_seconds() / 3600
                    recency_bonus = max(0.3, 1.0 - (age_hours * priority_info.recency_weight / 6))
                
                elif product_name == 'metar' and data:
                    age_hours = (datetime.utcnow() - data.observation_time).total_seconds() / 3600
                    recency_bonus = max(0.5, 1.0 - (age_hours * priority_info.recency_weight / 3))
                
                final_score = base_score * recency_bonus
                source_scores[product_type] = final_score
                
            except ValueError:
                # Unknown product type
                continue
        
        if not source_scores:
            return WeatherProductType.METAR, 0.5
        
        best_source = max(source_scores.items(), key=lambda x: x[1])
        return best_source[0], min(best_source[1] / 10, 1.0)
    
    def _generate_pilot_summary(self, weather_data: Dict, primary_source: WeatherProductType) -> str:
        """Generate concise, actionable summary for pilots"""
        
        summary_parts = []
        
        # Start with primary source information
        if primary_source == WeatherProductType.PIREP and weather_data.get('pirep'):
            latest_pirep = max(weather_data['pirep'], key=lambda p: p.report_time)
            summary_parts.append(f"PILOT REPORT: {self._summarize_pirep(latest_pirep)}")
        
        elif primary_source == WeatherProductType.METAR and weather_data.get('metar'):
            summary_parts.append(f"CURRENT: {self._summarize_metar(weather_data['metar'])}")
        
        # Add critical hazards
        hazards = []
        if weather_data.get('sigmet'):
            hazards.extend([f"SIGMET: {s.phenomenon}" for s in weather_data['sigmet']])
        
        if weather_data.get('gairmet'):
            hazards.extend([f"G-AIRMET: {g.hazard_type}" for g in weather_data['gairmet']])
        
        if hazards:
            summary_parts.append(f"HAZARDS: {', '.join(hazards[:3])}")  # Limit to 3 most important
        
        # Add forecast if available
        if weather_data.get('taf'):
            summary_parts.append(f"FORECAST: {self._summarize_taf(weather_data['taf'])}")
        
        return " | ".join(summary_parts) if summary_parts else "Limited weather information available."
    
    def _summarize_metar(self, metar: MetarData) -> str:
        """Create concise METAR summary"""
        parts = []
        
        if metar.wind and metar.wind.speed:
            wind_str = f"Wind {metar.wind.direction:03d}°/{metar.wind.speed}kt"
            if metar.wind.gust:
                wind_str += f"G{metar.wind.gust}"
            parts.append(wind_str)
        
        if metar.visibility and metar.visibility.distance:
            parts.append(f"Vis {metar.visibility.distance}SM")
        
        if metar.clouds:
            cloud_str = metar.clouds[0].coverage
            if metar.clouds[0].base:
                cloud_str += f" {metar.clouds[0].base}ft"
            parts.append(cloud_str)
        
        return ", ".join(parts)
    
    def _summarize_pirep(self, pirep: PirepData) -> str:
        """Create concise PIREP summary"""
        parts = []
        
        if pirep.aircraft_type:
            parts.append(pirep.aircraft_type)
        
        if pirep.altitude:
            parts.append(f"FL{pirep.altitude//100:03d}")
        
        if pirep.turbulence:
            parts.append(f"Turb: {pirep.turbulence}")
        
        if pirep.icing:
            parts.append(f"Ice: {pirep.icing}")
        
        return ", ".join(parts)
    
    def _summarize_taf(self, taf: TafData) -> str:
        """Create concise TAF summary"""
        # Simplified TAF summary - would need full TAF parser
        return f"Valid {taf.valid_from.strftime('%H%M')}-{taf.valid_until.strftime('%H%M')}Z"
    
    def _determine_overall_category(self, weather_data: Dict) -> WeatherCategory:
        """Determine overall weather category"""
        
        # SIGMETs always indicate severe weather
        if weather_data.get('sigmet'):
            return WeatherCategory.SEVERE
        
        # Check individual product categories
        categories = []
        
        if weather_data.get('metar'):
            categories.append(weather_data['metar'].category)
        
        for pirep in weather_data.get('pirep', []):
            categories.append(pirep.category)
        
        for gairmet in weather_data.get('gairmet', []):
            categories.append(gairmet.category)
        
        # Return highest severity
        if WeatherCategory.SEVERE in categories:
            return WeatherCategory.SEVERE
        elif WeatherCategory.SIGNIFICANT in categories:
            return WeatherCategory.SIGNIFICANT
        else:
            return WeatherCategory.CLEAR
    
    def _generate_recommendations(self, weather_data: Dict, overall_category: WeatherCategory) -> List[str]:
        """Generate actionable recommendations for pilots"""
        recommendations = []
        
        if overall_category == WeatherCategory.SEVERE:
            recommendations.append("CAUTION: Severe weather conditions present - consider alternate planning")
        
        # SIGMET recommendations
        if weather_data.get('sigmet'):
            for sigmet in weather_data['sigmet']:
                if 'TS' in sigmet.phenomenon:
                    recommendations.append("AVOID: Thunderstorm activity - maintain safe distance")
                elif 'TURB' in sigmet.phenomenon:
                    recommendations.append("CAUTION: Severe turbulence reported - consider altitude change")
                elif 'ICE' in sigmet.phenomenon:
                    recommendations.append("WARNING: Icing conditions - verify anti-ice systems")
        
        # PIREP-based recommendations
        if weather_data.get('pirep'):
            for pirep in weather_data['pirep']:
                if pirep.turbulence and 'MOD' in pirep.turbulence.upper():
                    recommendations.append(f"INFO: Moderate turbulence reported at FL{pirep.altitude//100:03d}")
                elif pirep.icing and 'LGT' in pirep.icing.upper():
                    recommendations.append(f"INFO: Light icing reported at FL{pirep.altitude//100:03d}")
        
        # Wind recommendations
        if weather_data.get('metar') and weather_data['metar'].wind:
            wind = weather_data['metar'].wind
            if wind.speed and wind.speed >= 25:
                recommendations.append(f"CAUTION: Strong winds {wind.speed}kt - verify crosswind limits")
            if wind.gust and wind.gust >= 35:
                recommendations.append(f"WARNING: Strong gusts to {wind.gust}kt - consider delay")
        
        return recommendations[:5]  # Limit to 5 most important recommendations
    
    def _extract_current_conditions(self, weather_data: Dict, primary_source: WeatherProductType) -> Dict[str, Any]:
        """Extract current conditions based on primary source"""
        conditions = {}
        
        if primary_source == WeatherProductType.PIREP and weather_data.get('pirep'):
            latest_pirep = max(weather_data['pirep'], key=lambda p: p.report_time)
            conditions = {
                "source": "PIREP",
                "time": latest_pirep.report_time.isoformat(),
                "aircraft": latest_pirep.aircraft_type,
                "altitude": latest_pirep.altitude,
                "turbulence": latest_pirep.turbulence,
                "icing": latest_pirep.icing,
                "reliability": "High (Pilot Experience)"
            }
        
        elif primary_source == WeatherProductType.METAR and weather_data.get('metar'):
            metar = weather_data['metar']
            conditions = {
                "source": "METAR",
                "time": metar.observation_time.isoformat(),
                "wind_direction": metar.wind.direction if metar.wind else None,
                "wind_speed": metar.wind.speed if metar.wind else None,
                "wind_gust": metar.wind.gust if metar.wind else None,
                "visibility": metar.visibility.distance if metar.visibility else None,
                "temperature": metar.temperature,
                "dewpoint": metar.dewpoint,
                "altimeter": metar.altimeter,
                "reliability": "High (Official Observation)"
            }
        
        return conditions
    
    def _extract_forecast(self, weather_data: Dict) -> Dict[str, Any]:
        """Extract forecast information"""
        forecast = {}
        
        if weather_data.get('taf'):
            taf = weather_data['taf']
            forecast = {
                "source": "TAF",
                "issued": taf.issue_time.isoformat(),
                "valid_from": taf.valid_from.isoformat(),
                "valid_until": taf.valid_until.isoformat(),
                "raw_text": taf.raw_text[:100] + "..." if len(taf.raw_text) > 100 else taf.raw_text
            }
        
        return forecast
    
    def _extract_hazards(self, weather_data: Dict) -> List[Dict[str, Any]]:
        """Extract hazard information from all sources"""
        hazards = []
        
        # SIGMETs
        for sigmet in weather_data.get('sigmet', []):
            hazards.append({
                "type": "SIGMET",
                "severity": "SEVERE",
                "phenomenon": sigmet.phenomenon,
                "valid_until": sigmet.valid_until.isoformat(),
                "details": sigmet.raw_text[:100] + "..."
            })
        
        # G-AIRMETs
        for gairmet in weather_data.get('gairmet', []):
            hazards.append({
                "type": "G-AIRMET", 
                "severity": "SIGNIFICANT",
                "hazard": gairmet.hazard_type,
                "altitude_range": f"{gairmet.base_altitude or 0}-{gairmet.top_altitude or 'TOP'}",
                "valid_until": gairmet.valid_until.isoformat()
            })
        
        # AIRMETs
        for airmet in weather_data.get('airmet', []):
            hazards.append({
                "type": "AIRMET",
                "series": airmet.series,
                "hazard": airmet.hazard_type,
                "valid_until": airmet.valid_until.isoformat()
            })
        
        return hazards
    
    # Helper methods (simplified implementations)
    def _get_station_coords(self, station_id: str) -> str:
        """Get station coordinates - simplified implementation"""
        # In real implementation, would look up from station database
        return "40.6413,-73.7781"  # JFK coordinates as example
    
    def _is_relevant_to_station(self, product, station_id: str, radius_nm: int) -> bool:
        """Check if weather product is relevant to station - simplified"""
        # In real implementation, would do geographic relevance check
        return True
    
    def _categorize_pirep(self, raw_text: str) -> WeatherCategory:
        """Categorize PIREP based on content"""
        text_upper = raw_text.upper()
        
        # Severe conditions
        if any(word in text_upper for word in ['SEV', 'EXTREME', 'EMBD TS', 'HVY ICE']):
            return WeatherCategory.SEVERE
        
        # Significant conditions
        elif any(word in text_upper for word in ['MOD', 'LGT-MOD', 'CHOP', 'TURB']):
            return WeatherCategory.SIGNIFICANT
        
        return WeatherCategory.CLEAR

# Global service instance
weather_service = ComprehensiveWeatherService()
