import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

class WeatherAnalyzer:
    """Analyzes weather data and categorizes conditions for aviation"""
    
    def __init__(self):
        # Weather category thresholds
        self.vfr_minimums = {
            'visibility': 3.0,  # statute miles
            'ceiling': 1000     # feet AGL
        }
        
        self.mvfr_minimums = {
            'visibility': 1.0,  # statute miles  
            'ceiling': 500      # feet AGL
        }
        
        # Wind thresholds
        self.wind_thresholds = {
            'moderate': 15,     # knots
            'strong': 25,       # knots
            'severe': 35        # knots
        }
        
        # Turbulence keywords
        self.turbulence_keywords = {
            'light': ['LGT', 'LIGHT', 'SMOOTH', 'OCCASIONAL'],
            'moderate': ['MOD', 'MODERATE', 'CHOP'],
            'severe': ['SEV', 'SEVERE', 'EXTREME']
        }
    
    def analyze_metar(self, metar_data: Dict) -> Dict[str, Any]:
        """
        Analyze METAR data and categorize weather conditions
        
        Args:
            metar_data (Dict): Parsed METAR data
            
        Returns:
            Dict: Analysis results with category and details
        """
        try:
            analysis = {
                'category': 'CLEAR',
                'flight_category': metar_data.get('flight_category', 'UNKNOWN'),
                'summary': '',
                'key_factors': [],
                'hazards': [],
                'recommendations': [],
                'severity_score': 0
            }
            
            # Analyze visibility
            visibility = metar_data.get('visibility')
            if visibility is not None:
                vis_analysis = self._analyze_visibility(visibility)
                analysis['key_factors'].append(vis_analysis['factor'])
                analysis['severity_score'] += vis_analysis['score']
            
            # Analyze ceiling
            ceiling = metar_data.get('ceiling')
            if ceiling is not None:
                ceiling_analysis = self._analyze_ceiling(ceiling)
                analysis['key_factors'].append(ceiling_analysis['factor'])
                analysis['severity_score'] += ceiling_analysis['score']
            
            # Analyze winds
            wind_speed = metar_data.get('wind_speed')
            wind_gust = metar_data.get('wind_gust')
            if wind_speed is not None:
                wind_analysis = self._analyze_winds(wind_speed, wind_gust)
                analysis['key_factors'].append(wind_analysis['factor'])
                analysis['severity_score'] += wind_analysis['score']
                if wind_analysis['hazard']:
                    analysis['hazards'].append(wind_analysis['hazard'])
            
            # Analyze weather conditions
            weather_string = metar_data.get('weather_conditions', '')
            if weather_string:
                wx_analysis = self._analyze_weather_conditions(weather_string)
                analysis['key_factors'].extend(wx_analysis['factors'])
                analysis['severity_score'] += wx_analysis['score']
                analysis['hazards'].extend(wx_analysis['hazards'])
            
            # Determine overall category
            analysis['category'] = self._determine_category(analysis['severity_score'], metar_data)
            
            # Generate summary and recommendations
            analysis['summary'] = self._generate_summary(analysis, metar_data)
            analysis['recommendations'] = self._generate_recommendations(analysis, metar_data)
            
            return analysis
            
        except Exception as e:
            logging.error(f"Error analyzing METAR: {str(e)}")
            return {'category': 'UNKNOWN', 'error': str(e)}
    
    def _analyze_visibility(self, visibility: float) -> Dict[str, Any]:
        """Analyze visibility conditions"""
        if visibility >= self.vfr_minimums['visibility']:
            return {
                'factor': f'Visibility: {visibility} SM (Good)',
                'score': 0,
                'level': 'good'
            }
        elif visibility >= self.mvfr_minimums['visibility']:
            return {
                'factor': f'Visibility: {visibility} SM (Marginal)',
                'score': 2,
                'level': 'marginal'
            }
        else:
            return {
                'factor': f'Visibility: {visibility} SM (Poor)',
                'score': 4,
                'level': 'poor'
            }
    
    def _analyze_ceiling(self, ceiling: int) -> Dict[str, Any]:
        """Analyze ceiling conditions"""
        if ceiling >= self.vfr_minimums['ceiling']:
            return {
                'factor': f'Ceiling: {ceiling} ft (Good)',
                'score': 0,
                'level': 'good'
            }
        elif ceiling >= self.mvfr_minimums['ceiling']:
            return {
                'factor': f'Ceiling: {ceiling} ft (Marginal)',
                'score': 2,
                'level': 'marginal'
            }
        else:
            return {
                'factor': f'Ceiling: {ceiling} ft (Low)',
                'score': 4,
                'level': 'poor'
            }
    
    def _analyze_winds(self, wind_speed: int, wind_gust: Optional[int] = None) -> Dict[str, Any]:
        """Analyze wind conditions"""
        effective_wind = wind_gust if wind_gust else wind_speed
        
        if effective_wind < self.wind_thresholds['moderate']:
            return {
                'factor': f'Winds: {wind_speed} kt (Light)',
                'score': 0,
                'hazard': None,
                'level': 'light'
            }
        elif effective_wind < self.wind_thresholds['strong']:
            return {
                'factor': f'Winds: {wind_speed} kt{"G" + str(wind_gust) + " kt" if wind_gust else ""} (Moderate)',
                'score': 1,
                'hazard': 'Moderate winds - monitor crosswind components',
                'level': 'moderate'
            }
        elif effective_wind < self.wind_thresholds['severe']:
            return {
                'factor': f'Winds: {wind_speed} kt{"G" + str(wind_gust) + " kt" if wind_gust else ""} (Strong)',
                'score': 3,
                'hazard': 'Strong winds - significant crosswind risk',
                'level': 'strong'
            }
        else:
            return {
                'factor': f'Winds: {wind_speed} kt{"G" + str(wind_gust) + " kt" if wind_gust else ""} (Severe)',
                'score': 5,
                'hazard': 'Severe winds - extreme caution required',
                'level': 'severe'
            }
    
    def _analyze_weather_conditions(self, weather_string: str) -> Dict[str, Any]:
        """Analyze present weather conditions"""
        factors = []
        hazards = []
        score = 0
        
        weather_upper = weather_string.upper()
        
        # Precipitation
        if any(precip in weather_upper for precip in ['RA', 'SN', 'GR', 'GS']):
            if any(intensity in weather_upper for intensity in ['+RA', '+SN', 'TSRA']):
                factors.append('Heavy precipitation present')
                hazards.append('Heavy precipitation - reduced visibility and runway conditions')
                score += 3
            elif any(light in weather_upper for light in ['-RA', '-SN']):
                factors.append('Light precipitation present')
                score += 1
            else:
                factors.append('Moderate precipitation present')
                score += 2
        
        # Thunderstorms
        if 'TS' in weather_upper:
            factors.append('Thunderstorms present')
            hazards.append('Thunderstorms - severe turbulence, wind shear, and lightning risk')
            score += 4
        
        # Fog/Mist
        if any(obscuration in weather_upper for obscuration in ['FG', 'BR', 'HZ']):
            factors.append('Reduced visibility due to fog/mist/haze')
            hazards.append('Visibility restrictions - approach and taxi hazards')
            score += 2
        
        # Freezing conditions
        if 'FZ' in weather_upper:
            factors.append('Freezing conditions present')
            hazards.append('Icing conditions - aircraft and runway icing risk')
            score += 3
        
        return {
            'factors': factors,
            'hazards': hazards,
            'score': score
        }
    
    def _determine_category(self, severity_score: int, metar_data: Dict) -> str:
        """Determine overall weather category based on severity score and flight category"""
        flight_cat = metar_data.get('flight_category', 'UNKNOWN')
        
        # Use flight category as primary indicator with proper mapping
        if flight_cat == 'VFR' and severity_score <= 1:
            return 'CLEAR'
        elif flight_cat == 'MVFR' or (flight_cat == 'VFR' and severity_score > 1):
            return 'SIGNIFICANT'
        elif flight_cat in ['IFR', 'LIFR'] or severity_score >= 4:
            return 'SEVERE'
        else:
            return 'SIGNIFICANT'  # Default for uncertain cases
    
    def _generate_summary(self, analysis: Dict, metar_data: Dict) -> str:
        """Generate human-readable weather summary"""
        category = analysis['category']
        flight_cat = metar_data.get('flight_category', 'UNKNOWN')
        
        if category == 'CLEAR':
            return f"Good flying conditions. {flight_cat} conditions with minimal weather impact."
        elif category == 'SIGNIFICANT':
            return f"Marginal conditions requiring attention. {flight_cat} conditions with weather factors to monitor."
        else:
            return f"Poor conditions requiring careful consideration. Significant weather hazards present."
    
    def _generate_recommendations(self, analysis: Dict, metar_data: Dict) -> List[str]:
        """Generate flight recommendations based on analysis"""
        recommendations = []
        category = analysis['category']
        
        if category == 'CLEAR':
            recommendations.append("Conditions favorable for flight operations")
            recommendations.append("Monitor weather updates for any changes")
        
        elif category == 'SIGNIFICANT':
            recommendations.append("Review alternate airports and fuel requirements")
            recommendations.append("Monitor weather trends and updates closely")
            recommendations.append("Consider delaying departure if conditions are deteriorating")
            
            # Wind-specific recommendations
            wind_speed = metar_data.get('wind_speed', 0)
            if wind_speed > 15:
                recommendations.append("Calculate crosswind components for all runways")
        
        else:  # SEVERE
            recommendations.append("Consider delaying flight until conditions improve")
            recommendations.append("If proceeding, ensure alternate airports are available")
            recommendations.append("Review emergency procedures and diversion options")
            recommendations.append("Monitor weather radar and pilot reports")
        
        return recommendations
    
    def generate_flight_briefing(self, weather_data: Dict, airports: List[str]) -> Dict[str, Any]:
        """
        Generate consolidated flight briefing for entire route
        
        Args:
            weather_data (Dict): Weather data for all airports
            airports (List[str]): List of airports in route order
            
        Returns:
            Dict: Consolidated briefing with route analysis
        """
        try:
            briefing = {
                'route_summary': '',
                'overall_category': 'CLEAR',
                'critical_airports': [],
                'route_hazards': [],
                'recommendations': [],
                'weather_trend': 'STABLE'
            }
            
            # Analyze each airport
            airport_analyses = {}
            severity_scores = []
            
            for airport in airports:
                if airport in weather_data and weather_data[airport].get('metar'):
                    analysis = weather_data[airport].get('analysis', {})
                    airport_analyses[airport] = analysis
                    
                    category = analysis.get('category', 'UNKNOWN')
                    severity_score = analysis.get('severity_score', 0)
                    severity_scores.append(severity_score)
                    
                    # Track critical airports
                    if category in ['SIGNIFICANT', 'SEVERE']:
                        briefing['critical_airports'].append({
                            'airport': airport,
                            'category': category,
                            'issues': analysis.get('hazards', [])
                        })
            
            # Determine overall route category
            if severity_scores:
                max_severity = max(severity_scores)
                avg_severity = sum(severity_scores) / len(severity_scores)
                
                if max_severity >= 6 or avg_severity >= 4:
                    briefing['overall_category'] = 'SEVERE'
                elif max_severity >= 3 or avg_severity >= 2:
                    briefing['overall_category'] = 'SIGNIFICANT'
                else:
                    briefing['overall_category'] = 'CLEAR'
            
            # Generate route summary
            briefing['route_summary'] = self._generate_route_summary(
                airports, airport_analyses, briefing['overall_category']
            )
            
            # Compile route-wide hazards
            all_hazards = []
            for analysis in airport_analyses.values():
                all_hazards.extend(analysis.get('hazards', []))
            
            # Remove duplicates
            briefing['route_hazards'] = list(set(all_hazards))
            
            # Generate route recommendations
            briefing['recommendations'] = self._generate_route_recommendations(
                briefing['overall_category'], briefing['critical_airports']
            )
            
            return briefing
            
        except Exception as e:
            logging.error(f"Error generating flight briefing: {str(e)}")
            return {'error': str(e)}
    
    def _generate_route_summary(self, airports: List[str], analyses: Dict, category: str) -> str:
        """Generate summary text for the entire route"""
        if category == 'CLEAR':
            return f"Route from {airports[0]} to {airports[-1]} shows generally good conditions along the flight path."
        elif category == 'SIGNIFICANT':
            return f"Route from {airports[0]} to {airports[-1]} has marginal conditions requiring monitoring."
        else:
            return f"Route from {airports[0]} to {airports[-1]} has significant weather challenges requiring careful planning."
    
    def _generate_route_recommendations(self, category: str, critical_airports: List[Dict]) -> List[str]:
        """Generate recommendations for the entire route"""
        recommendations = []
        
        if category == 'SEVERE':
            recommendations.append("Consider delaying departure until weather improves")
            recommendations.append("File for multiple alternate airports")
            recommendations.append("Carry additional fuel for possible diversions")
        
        elif category == 'SIGNIFICANT':
            recommendations.append("Monitor weather updates throughout flight")
            recommendations.append("Review alternate airports at critical points")
        
        if critical_airports:
            airport_list = ', '.join([apt['airport'] for apt in critical_airports])
            recommendations.append(f"Pay special attention to conditions at: {airport_list}")
        
        recommendations.append("Check NOTAMs for all airports and waypoints")
        recommendations.append("Review current PIREPs for route conditions")
        
        return recommendations
    
    def analyze_combined_weather_data(self, airport_data: Dict) -> Dict[str, Any]:
        """
        Analyze combined weather data from METAR, TAF, and PIREP
        
        Args:
            airport_data (dict): All weather data for an airport
            
        Returns:
            dict: Combined analysis considering all data sources
        """
        analysis = {
            'category': 'CLEAR',
            'severity_score': 0,
            'sources_used': [],
            'combined_factors': [],
            'flight_category': 'UNKNOWN',
            'summary': '',
            'key_factors': [],
            'hazards': [],
            'recommendations': []
        }
        
        # Start with METAR analysis if available
        metar = airport_data.get('metar')
        if metar:
            metar_analysis = self.analyze_metar(metar)
            # Keep the original METAR analysis as base
            analysis.update(metar_analysis)
            analysis['sources_used'].append('METAR')
            # Store original category before modifications
            original_category = metar_analysis.get('category', 'CLEAR')
        
        # Enhance with TAF data if available
        taf = airport_data.get('taf')
        if taf:
            taf_factors = self._analyze_taf_data(taf)
            analysis['combined_factors'].extend(taf_factors)
            analysis['sources_used'].append('TAF')
            
            # Increase severity if TAF shows deteriorating conditions
            if any('deteriorating' in factor.lower() or 'thunderstorm' in factor.lower() for factor in taf_factors):
                analysis['severity_score'] += 2
            elif any('forecast' in factor.lower() for factor in taf_factors):
                analysis['severity_score'] += 1
        
        # Enhance with PIREP data if available
        pireps = airport_data.get('pirep', [])
        if pireps and len(pireps) > 0:
            pirep_factors = self._analyze_pirep_data(pireps)
            analysis['combined_factors'].extend(pirep_factors)
            analysis['sources_used'].append('PIREP')
            
            # Increase severity based on pilot reports
            if any('turbulence' in factor.lower() or 'icing' in factor.lower() for factor in pirep_factors):
                analysis['severity_score'] += 2
            elif any('smooth' in factor.lower() for factor in pirep_factors):
                analysis['severity_score'] -= 1  # Good pilot reports can reduce severity
        
        # Use time-appropriate conditions if available
        time_conditions = airport_data.get('time_appropriate_conditions')
        primary_source = airport_data.get('primary_source', 'METAR')
        
        if time_conditions and primary_source == 'TAF':
            analysis['combined_factors'].append(f"Using forecast data for planned departure time")
            analysis['time_aware'] = True
        
        # Recalculate category based on combined severity, but respect original METAR category
        if metar:
            # Don't downgrade from original METAR category unless we have strong evidence
            if analysis['severity_score'] >= 6:
                analysis['category'] = 'SEVERE'
            elif analysis['severity_score'] >= 3 or original_category == 'SIGNIFICANT':
                analysis['category'] = 'SIGNIFICANT'
            elif original_category == 'SEVERE':
                analysis['category'] = 'SEVERE'
            else:
                analysis['category'] = original_category
        else:
            # Fallback logic when no METAR
            if analysis['severity_score'] >= 6:
                analysis['category'] = 'SEVERE'
            elif analysis['severity_score'] >= 3:
                analysis['category'] = 'SIGNIFICANT'
            else:
                analysis['category'] = 'CLEAR'
        
        # Update summary to reflect all sources
        sources_str = ', '.join(analysis['sources_used']) if analysis['sources_used'] else 'Limited data'
        analysis['summary'] = f"{analysis['summary']} (Sources: {sources_str})"
        
        return analysis
    
    def _analyze_taf_data(self, taf):
        """Analyze TAF data for additional weather factors"""
        factors = []
        
        if not taf:
            return factors
        
        raw_text = taf.get('raw_text', '').upper()
        
        # Look for weather phenomena in TAF
        if 'TS' in raw_text:
            factors.append('Thunderstorms forecast')
        if 'FG' in raw_text or 'BR' in raw_text:
            factors.append('Fog/mist forecast')
        if 'RA' in raw_text or 'SN' in raw_text:
            factors.append('Precipitation forecast')
        if 'TEMPO' in raw_text:
            factors.append('Temporary conditions expected')
        if 'PROB' in raw_text:
            factors.append('Probability conditions forecast')
        if 'BECMG' in raw_text:
            factors.append('Conditions becoming different')
        if any(wind in raw_text for wind in ['G25', 'G30', 'G35']):
            factors.append('Strong wind gusts forecast')
        
        return factors
    
    def _analyze_pirep_data(self, pireps):
        """Analyze PIREP data for pilot-reported conditions"""
        factors = []
        
        for pirep in pireps:
            if not pirep:
                continue
                
            raw_text = pirep.get('raw_text', '').upper()
            
            if 'TURB' in raw_text or 'ROUGH' in raw_text:
                factors.append('Turbulence reported by pilots')
            if 'ICE' in raw_text or 'ICING' in raw_text:
                factors.append('Icing conditions reported')
            if 'SMOOTH' in raw_text:
                factors.append('Smooth conditions reported')
            if 'CLOUD' in raw_text or 'LAYER' in raw_text:
                factors.append('Cloud conditions reported by pilots')
            if 'CHOP' in raw_text:
                factors.append('Light chop reported')
            if 'RIDE' in raw_text:
                factors.append('Ride conditions reported by pilots')
        
        return factors
