import httpx
import asyncio
import re
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from models import *
from config import settings

class WeatherService:
    def __init__(self):
        self.base_url = settings.AVIATION_WEATHER_BASE_URL
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "Aviation-Weather-Briefing-System/1.0"}
        )

    async def fetch_comprehensive_weather(self, station_id: str) -> WeatherBriefing:
        """Fetch all weather products for a station"""
        tasks = {
            'metar': self._fetch_metar(station_id),
            'taf': self._fetch_taf(station_id),
            'pireps': self._fetch_pireps(station_id),
            'sigmets': self._fetch_sigmets(station_id),
            'gairmets': self._fetch_gairmets(station_id),
            'airmets': self._fetch_airmets(station_id),
            'cwas': self._fetch_cwas(station_id)
        }
        
        results = {}
        for product_type, task in tasks.items():
            try:
                results[product_type] = await task
            except Exception as e:
                print(f"Error fetching {product_type}: {e}")
                results[product_type] = None

        return self._create_briefing(station_id, results)

    async def _fetch_metar(self, station_id: str) -> Optional[MetarData]:
        try:
            response = await self.client.get(
                f"{self.base_url}/metar",
                params={'ids': station_id, 'format': 'json'}
            )
            
            if response.status_code == 204:
                return None
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    item = data[0]
                    return MetarData(
                        station_id=item.get('icaoId', station_id),
                        raw_text=item.get('rawOb', ''),
                        observation_time=self._parse_datetime(item.get('obsTime')),
                        category=self._categorize_metar(item.get('rawOb', '')),
                        wind_speed=item.get('wspd'),
                        wind_direction=item.get('wdir'),
                        wind_gust=item.get('wgst'),
                        visibility=self._parse_visibility(item.get('visib')),
                        temperature=item.get('temp'),
                        dewpoint=item.get('dewp'),
                        altimeter=item.get('altim')
                    )
        except Exception as e:
            print(f"METAR error: {e}")
        return None

    async def _fetch_taf(self, station_id: str) -> Optional[TafData]:
        try:
            response = await self.client.get(
                f"{self.base_url}/taf",
                params={'ids': station_id, 'format': 'json'}
            )
            
            if response.status_code == 204:
                return None
                
            if response.status_code == 200:
                data = response.json()
                if data:
                    item = data[0]
                    return TafData(
                        station_id=item.get('icaoId', station_id),
                        raw_text=item.get('rawTAF', ''),
                        issue_time=self._parse_datetime(item.get('issueTime')),
                        valid_from=self._parse_datetime(item.get('validTimeFrom')),
                        valid_until=self._parse_datetime(item.get('validTimeTo')),
                        category=WeatherCategory.CLEAR
                    )
        except Exception as e:
            print(f"TAF error: {e}")
        return None

    async def _fetch_pireps(self, station_id: str) -> List[PirepData]:
        try:
            response = await self.client.get(
                f"{self.base_url}/aircraftreport",
                params={'format': 'json', 'hours': '2'}
            )
            
            if response.status_code == 204:
                return []
                
            if response.status_code == 200:
                data = response.json()
                pireps = []
                for item in data[:10]:  # Limit to 10 most recent
                    try:
                        pireps.append(PirepData(
                            station_id=station_id,
                            raw_text=item.get('rawOb', ''),
                            report_time=self._parse_datetime(item.get('obsTime')),
                            aircraft_type=item.get('acType'),
                            altitude=item.get('fltlvl'),
                            category=self._categorize_pirep(item.get('rawOb', ''))
                        ))
                    except Exception as e:
                        print(f"PIREP parse error: {e}")
                        continue
                return pireps
        except Exception as e:
            print(f"PIREP error: {e}")
        return []

    async def _fetch_sigmets(self, station_id: str) -> List[SigmetData]:
        try:
            response = await self.client.get(f"{self.base_url}/sigmet", params={'format': 'json'})
            if response.status_code == 200:
                data = response.json()
                return [
                    SigmetData(
                        identifier=item.get('id', ''),
                        raw_text=item.get('rawSigmet', ''),
                        issue_time=self._parse_datetime(item.get('issueTime')),
                        valid_until=self._parse_datetime(item.get('validTimeTo')),
                        phenomenon=item.get('hazard', '')
                    ) for item in data[:5]
                ]
        except Exception as e:
            print(f"SIGMET error: {e}")
        return []

    async def _fetch_gairmets(self, station_id: str) -> List[GAirmetData]:
        try:
            response = await self.client.get(f"{self.base_url}/gairmet", params={'format': 'json'})
            if response.status_code == 200:
                data = response.json()
                return [
                    GAirmetData(
                        identifier=item.get('id', ''),
                        raw_text=item.get('rawGAirmet', ''),
                        issue_time=self._parse_datetime(item.get('issueTime')),
                        valid_until=self._parse_datetime(item.get('validTimeTo')),
                        hazard_type=item.get('hazard', '')
                    ) for item in data[:5]
                ]
        except Exception as e:
            print(f"G-AIRMET error: {e}")
        return []

    async def _fetch_airmets(self, station_id: str) -> List[AirmetData]:
        try:
            response = await self.client.get(f"{self.base_url}/airmet", params={'format': 'json'})
            if response.status_code == 200:
                data = response.json()
                return [
                    AirmetData(
                        identifier=item.get('id', ''),
                        raw_text=item.get('rawAirmet', ''),
                        issue_time=self._parse_datetime(item.get('issueTime')),
                        valid_until=self._parse_datetime(item.get('validTimeTo')),
                        hazard_type=item.get('hazard', '')
                    ) for item in data[:5]
                ]
        except Exception as e:
            print(f"AIRMET error: {e}")
        return []

    async def _fetch_cwas(self, station_id: str) -> List[CwaData]:
        try:
            response = await self.client.get(f"{self.base_url}/cwa", params={'format': 'json'})
            if response.status_code == 200:
                data = response.json()
                return [
                    CwaData(
                        identifier=item.get('id', ''),
                        raw_text=item.get('rawCwa', ''),
                        issue_time=self._parse_datetime(item.get('issueTime')),
                        valid_until=self._parse_datetime(item.get('validTimeTo')),
                        phenomenon=item.get('hazard', '')
                    ) for item in data[:5]
                ]
        except Exception as e:
            print(f"CWA error: {e}")
        return []

    def _parse_datetime(self, date_str: str) -> datetime:
        """Parse various datetime formats"""
        if not date_str:
            return datetime.utcnow()
        
        try:
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                return datetime.utcnow()
        except:
            return datetime.utcnow()

    def _parse_visibility(self, visib_str: str) -> Optional[float]:
        """Parse visibility string to float"""
        if not visib_str:
            return None
        
        if visib_str == "10+":
            return 10.0
        
        try:
            if '/' in visib_str:
                if ' ' in visib_str:
                    parts = visib_str.split()
                    whole = float(parts[0])
                    num, den = map(float, parts[1].split('/'))
                    return whole + num / den
                else:
                    num, den = map(float, visib_str.split('/'))
                    return num / den
            else:
                return float(visib_str)
        except:
            return None

    def _categorize_metar(self, raw_text: str) -> WeatherCategory:
        """Categorize METAR based on conditions"""
        if not raw_text:
            return WeatherCategory.CLEAR
        
        text = raw_text.upper()
        
        if (re.search(r'G4[5-9]|G[5-9]\d', text) or
            '1/2SM' in text or '1/4SM' in text or 
            'TS' in text or 'FZRA' in text):
            return WeatherCategory.SEVERE
        
        if (re.search(r'G[2-4]\d', text) or 
            '3SM' in text or '2SM' in text or 
            'BR' in text or 'FG' in text or
            'BKN' in text or 'OVC' in text):
            return WeatherCategory.SIGNIFICANT
        
        return WeatherCategory.CLEAR

    def _categorize_pirep(self, raw_text: str) -> WeatherCategory:
        """Categorize PIREP based on content"""
        if not raw_text:
            return WeatherCategory.CLEAR
        
        text = raw_text.upper()
        
        if any(word in text for word in ['SEV', 'EXTREME', 'HVY']):
            return WeatherCategory.SEVERE
        elif any(word in text for word in ['MOD', 'TURB', 'CHOP']):
            return WeatherCategory.SIGNIFICANT
        
        return WeatherCategory.CLEAR

    def _create_briefing(self, station_id: str, results: Dict[str, Any]) -> WeatherBriefing:
        """Create comprehensive weather briefing"""
        
        # ✅ FIXED: Proper product mapping
        available_products = []
        product_mapping = {
            'metar': WeatherProductType.METAR,
            'taf': WeatherProductType.TAF,
            'pireps': WeatherProductType.PIREP,
            'sigmets': WeatherProductType.SIGMET,
            'gairmets': WeatherProductType.G_AIRMET,
            'airmets': WeatherProductType.AIRMET,
            'cwas': WeatherProductType.CWA
        }
        
        for product, data in results.items():
            if data and product in product_mapping:
                if isinstance(data, list) and len(data) > 0:
                    available_products.append(product_mapping[product])
                elif not isinstance(data, list):
                    available_products.append(product_mapping[product])

        # Determine primary source and overall category
        primary_source, overall_category = self._determine_primary_source_and_category(results)
        
        # Generate pilot summary
        pilot_summary = self._generate_pilot_summary(results, primary_source)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(results, overall_category)
        
        # Extract hazards
        hazards = self._extract_hazards(results)
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence(results, primary_source)

        return WeatherBriefing(
            station_id=station_id,
            overall_category=overall_category,
            pilot_summary=pilot_summary,
            recommendations=recommendations,
            primary_source=primary_source,
            confidence_score=confidence_score,
            metar_data=results.get('metar'),
            taf_data=results.get('taf'),
            pirep_data=results.get('pireps', []),
            sigmet_data=results.get('sigmets', []),
            gairmet_data=results.get('gairmets', []),
            airmet_data=results.get('airmets', []),
            cwa_data=results.get('cwas', []),
            available_products=available_products,
            hazards=hazards
        )

    def _determine_primary_source_and_category(self, results: Dict) -> Tuple[WeatherProductType, WeatherCategory]:
        """Determine primary source and overall category"""
        if results.get('sigmets'):
            return WeatherProductType.SIGMET, WeatherCategory.SEVERE
        
        if results.get('pireps'):
            recent_pireps = [p for p in results['pireps'] 
                           if (datetime.utcnow() - p.report_time).total_seconds() < 3600]
            if recent_pireps:
                worst_category = max([p.category for p in recent_pireps], 
                                   key=lambda x: ['CLEAR', 'SIGNIFICANT', 'SEVERE'].index(x.value))
                return WeatherProductType.PIREP, worst_category
        
        if results.get('metar'):
            return WeatherProductType.METAR, results['metar'].category
        
        return WeatherProductType.METAR, WeatherCategory.CLEAR

    def _generate_pilot_summary(self, results: Dict, primary_source: WeatherProductType) -> str:
        """Generate pilot-focused summary"""
        summary_parts = []
        
        if primary_source == WeatherProductType.METAR and results.get('metar'):
            metar = results['metar']
            wind_desc = f"Wind {metar.wind_direction or 'VRB'}°/{metar.wind_speed or 0}kt"
            if metar.wind_gust:
                wind_desc += f"G{metar.wind_gust}"
            
            vis_desc = f"Vis {metar.visibility or 10}SM"
            temp_desc = f"Temp {metar.temperature or 'N/A'}°C"
            
            summary_parts.extend([wind_desc, vis_desc, temp_desc])
        
        elif primary_source == WeatherProductType.PIREP and results.get('pireps'):
            latest_pirep = max(results['pireps'], key=lambda p: p.report_time)
            summary_parts.append(f"PIREP: {latest_pirep.aircraft_type or 'Aircraft'} reports")
            if latest_pirep.turbulence:
                summary_parts.append(f"Turbulence: {latest_pirep.turbulence}")
        
        elif primary_source == WeatherProductType.SIGMET and results.get('sigmets'):
            latest_sigmet = max(results['sigmets'], key=lambda s: s.issue_time)
            summary_parts.append(f"SIGMET: {latest_sigmet.phenomenon}")
        
        total_hazards = (len(results.get('sigmets', [])) + 
                        len(results.get('gairmets', [])) + 
                        len(results.get('airmets', [])))
        
        if total_hazards > 0:
            summary_parts.append(f"{total_hazards} active hazard(s)")
        
        return " | ".join(summary_parts) if summary_parts else "Limited weather information available"

    def _generate_recommendations(self, results: Dict, overall_category: WeatherCategory) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if overall_category == WeatherCategory.SEVERE:
            recommendations.append("⚠️ SEVERE weather conditions - Exercise extreme caution")
        
        if results.get('sigmets'):
            recommendations.append("🚨 SIGMETs active - Review significant weather warnings")
        
        if results.get('metar'):
            metar = results['metar']
            if metar.wind_gust and metar.wind_gust > 35:
                recommendations.append(f"💨 Strong gusts to {metar.wind_gust}kt - Verify crosswind limits")
            if metar.visibility and metar.visibility < 3:
                recommendations.append(f"🌫️ Low visibility {metar.visibility}SM - IFR conditions")
        
        if len(results.get('pireps', [])) > 0:
            recommendations.append("✈️ Recent pilot reports available - Review for current conditions")
        
        return recommendations[:5]

    def _extract_hazards(self, results: Dict) -> List[Dict[str, Any]]:
        """Extract hazard information"""
        hazards = []
        
        for sigmet in results.get('sigmets', []):
            hazards.append({
                "type": "SIGMET",
                "severity": "SEVERE",
                "phenomenon": sigmet.phenomenon,
                "valid_until": sigmet.valid_until.isoformat(),
                "source": "SIGMET"
            })
        
        for gairmet in results.get('gairmets', []):
            hazards.append({
                "type": "G-AIRMET",
                "severity": "SIGNIFICANT",
                "hazard": gairmet.hazard_type,
                "valid_until": gairmet.valid_until.isoformat(),
                "source": "G-AIRMET"
            })
        
        return hazards

    def _calculate_confidence(self, results: Dict, primary_source: WeatherProductType) -> float:
        """Calculate confidence score for the briefing"""
        base_confidence = 0.5
        
        if results.get('metar'):
            age_hours = (datetime.utcnow() - results['metar'].observation_time).total_seconds() / 3600
            if age_hours < 1:
                base_confidence += 0.3
            elif age_hours < 3:
                base_confidence += 0.2
        
        if results.get('pireps'):
            base_confidence += min(0.2, len(results['pireps']) * 0.05)
        
        source_count = sum(1 for v in results.values() if v)
        base_confidence += min(0.2, source_count * 0.05)
        
        return min(base_confidence, 1.0)

# Global service instance
weather_service = WeatherService()
