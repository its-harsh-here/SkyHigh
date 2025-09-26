"""
Natural Language Processing module for aviation weather analysis
Provides intelligent summaries and pilot recommendations
"""
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import logging

class AviationNLPAnalyzer:
    """NLP-based analyzer for aviation weather data and pilot recommendations"""
    
    def __init__(self):
        # Weather priority weights for analysis
        self.priority_weights = {
            'thunderstorms': 10,
            'severe_turbulence': 9,
            'icing': 8,
            'low_visibility': 7,
            'low_ceiling': 7,
            'strong_winds': 6,
            'crosswinds': 5,
            'moderate_turbulence': 4,
            'precipitation': 3,
            'temperature_extremes': 2,
            'normal_conditions': 1
        }
        
        # Weather condition patterns for NLP analysis
        self.weather_patterns = {
            'thunderstorms': [r'\bTS\b', r'THUNDERSTORM', r'CONVECTIVE', r'CUMULONIMBUS'],
            'severe_weather': [r'\+TS\b', r'\+RA\b', r'\+SN\b', r'TORNADO', r'HAIL'],
            'icing': [r'\bFZ\b', r'ICING', r'FREEZING', r'ICE PELLETS'],
            'turbulence': [r'TURB', r'TURBULENCE', r'ROUGH', r'BUMPY'],
            'visibility': [r'\bFG\b', r'\bBR\b', r'\bHZ\b', r'MIST', r'FOG'],
            'precipitation': [r'\bRA\b', r'\bSN\b', r'\bDZ\b', r'RAIN', r'SNOW']
        }
        
        # Flight phase considerations
        self.flight_phases = {
            'departure': ['takeoff', 'climb', 'initial'],
            'enroute': ['cruise', 'navigation', 'waypoint'],
            'arrival': ['descent', 'approach', 'landing']
        }
    
    def generate_comprehensive_summary(self, weather_data: Dict, airports: List[str], 
                                     briefing: Dict) -> Dict[str, str]:
        """
        Generate comprehensive weather summary with NLP analysis
        
        Args:
            weather_data: Weather data for all airports
            airports: List of airports in route order
            briefing: Flight briefing data
            
        Returns:
            Dict containing summary and recommendations
        """
        try:
            # Analyze weather conditions across route
            conditions_analysis = self._analyze_route_conditions(weather_data, airports)
            
            # Generate priority-based summary
            summary = self._generate_priority_summary(conditions_analysis, airports, briefing)
            
            # Generate intelligent pilot recommendations
            recommendations = self._generate_pilot_recommendations(
                conditions_analysis, airports, briefing
            )
            
            # Generate phase-specific guidance
            phase_guidance = self._generate_phase_guidance(conditions_analysis, airports)
            
            return {
                'executive_summary': summary,
                'pilot_recommendations': recommendations,
                'phase_guidance': phase_guidance,
                'risk_assessment': self._assess_flight_risk(conditions_analysis),
                'decision_factors': self._extract_decision_factors(conditions_analysis)
            }
            
        except Exception as e:
            logging.error(f"Error generating NLP summary: {str(e)}")
            return {
                'executive_summary': "Weather analysis unavailable due to processing error.",
                'pilot_recommendations': ["Contact flight operations for manual weather briefing."],
                'phase_guidance': {},
                'risk_assessment': 'UNKNOWN',
                'decision_factors': []
            }
    
    def _analyze_route_conditions(self, weather_data: Dict, airports: List[str]) -> Dict:
        """Analyze weather conditions across the entire route"""
        analysis = {
            'critical_conditions': [],
            'moderate_conditions': [],
            'normal_conditions': [],
            'airports_by_severity': {'severe': [], 'significant': [], 'clear': []},
            'dominant_hazards': [],
            'weather_trends': {},
            'route_statistics': {}
        }
        
        hazard_counts = {}
        severity_scores = []
        
        for airport in airports:
            airport_data = weather_data.get(airport, {})
            metar = airport_data.get('metar', {})
            airport_analysis = airport_data.get('analysis', {})
            
            if not metar:
                continue
                
            # Categorize airport by severity
            category = airport_analysis.get('category', 'UNKNOWN').lower()
            if category in analysis['airports_by_severity']:
                analysis['airports_by_severity'][category].append(airport)
            
            # Extract weather conditions
            conditions = self._extract_weather_conditions(metar, airport_analysis)
            severity_scores.append(airport_analysis.get('severity_score', 0))
            
            # Count hazards
            for hazard in conditions['hazards']:
                hazard_type = hazard['type']
                hazard_counts[hazard_type] = hazard_counts.get(hazard_type, 0) + 1
                
                if hazard['severity'] == 'critical':
                    analysis['critical_conditions'].append({
                        'airport': airport,
                        'condition': hazard
                    })
                elif hazard['severity'] == 'moderate':
                    analysis['moderate_conditions'].append({
                        'airport': airport,
                        'condition': hazard
                    })
        
        # Determine dominant hazards
        analysis['dominant_hazards'] = sorted(
            hazard_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:3]
        
        # Calculate route statistics
        analysis['route_statistics'] = {
            'avg_severity': sum(severity_scores) / len(severity_scores) if severity_scores else 0,
            'max_severity': max(severity_scores) if severity_scores else 0,
            'critical_airport_count': len(analysis['airports_by_severity']['severe']),
            'total_airports': len(airports)
        }
        
        return analysis
    
    def _extract_weather_conditions(self, metar: Dict, analysis: Dict) -> Dict:
        """Extract and categorize weather conditions from METAR data"""
        conditions = {
            'hazards': [],
            'factors': [],
            'visibility_issues': False,
            'wind_issues': False,
            'precipitation': False
        }
        
        # Analyze visibility
        visibility = metar.get('visibility', 10)
        if visibility is not None and visibility < 3:
            severity = 'critical' if visibility < 1 else 'moderate'
            conditions['hazards'].append({
                'type': 'low_visibility',
                'severity': severity,
                'value': visibility,
                'description': f"Visibility {visibility} SM"
            })
            conditions['visibility_issues'] = True
        
        # Analyze ceiling
        ceiling = metar.get('ceiling')
        if ceiling and ceiling < 1000:
            severity = 'critical' if ceiling < 500 else 'moderate'
            conditions['hazards'].append({
                'type': 'low_ceiling',
                'severity': severity,
                'value': ceiling,
                'description': f"Ceiling {ceiling} ft"
            })
        
        # Analyze winds
        wind_speed = metar.get('wind_speed', 0) or 0
        wind_gust = metar.get('wind_gust', wind_speed) or wind_speed
        
        if wind_speed > 15 or wind_gust > 20:
            severity = 'critical' if wind_gust > 35 else 'moderate'
            conditions['hazards'].append({
                'type': 'strong_winds',
                'severity': severity,
                'value': wind_gust,
                'description': f"Winds {wind_speed}G{wind_gust} kt" if wind_gust > wind_speed else f"Winds {wind_speed} kt"
            })
            conditions['wind_issues'] = True
        
        # Analyze weather phenomena
        wx_string = metar.get('weather_conditions', '').upper()
        if wx_string:
            if any(pattern in wx_string for pattern in ['TS', 'THUNDERSTORM']):
                conditions['hazards'].append({
                    'type': 'thunderstorms',
                    'severity': 'critical',
                    'description': 'Thunderstorms present'
                })
            
            if any(pattern in wx_string for pattern in ['FZ', 'FREEZING']):
                conditions['hazards'].append({
                    'type': 'icing',
                    'severity': 'critical',
                    'description': 'Icing conditions'
                })
            
            if any(pattern in wx_string for pattern in ['RA', 'SN', 'DZ']):
                conditions['precipitation'] = True
                conditions['factors'].append('Precipitation present')
        
        return conditions
    
    def _generate_priority_summary(self, analysis: Dict, airports: List[str], 
                                 briefing: Dict) -> str:
        """Generate priority-based executive summary"""
        route_str = f"{airports[0]} to {airports[-1]}"
        if len(airports) > 2:
            route_str += f" via {len(airports)-2} waypoint(s)"
        
        overall_category = briefing.get('overall_category', 'UNKNOWN')
        critical_count = len(analysis['critical_conditions'])
        severe_airports = len(analysis['airports_by_severity']['severe'])
        
        # Start with route and overall assessment
        if overall_category == 'SEVERE' or critical_count > 0:
            summary = f"⚠️ CAUTION: Route {route_str} presents significant weather challenges. "
            
            if critical_count > 0:
                hazards = [cond['condition']['description'] for cond in analysis['critical_conditions'][:2]]
                summary += f"Critical conditions include {', '.join(hazards)}. "
            
            if severe_airports > 0:
                severe_list = ', '.join(analysis['airports_by_severity']['severe'][:3])
                summary += f"Airports requiring special attention: {severe_list}. "
            
            summary += "Consider alternate routing or delaying departure until conditions improve."
            
        elif overall_category == 'SIGNIFICANT':
            summary = f"⚡ MONITOR: Route {route_str} has marginal conditions requiring careful monitoring. "
            
            if analysis['dominant_hazards']:
                primary_hazard = analysis['dominant_hazards'][0][0].replace('_', ' ').title()
                summary += f"Primary concern is {primary_hazard.lower()} affecting multiple airports. "
            
            moderate_count = len(analysis['moderate_conditions'])
            if moderate_count > 0:
                summary += f"Monitor {moderate_count} weather factor(s) that may impact flight operations. "
            
            summary += "Flight feasible with increased vigilance and contingency planning."
            
        else:
            summary = f"✅ FAVORABLE: Route {route_str} shows generally good flying conditions. "
            
            if analysis['moderate_conditions']:
                summary += f"Minor weather factors noted at {len(analysis['moderate_conditions'])} location(s). "
            
            avg_severity = analysis['route_statistics'].get('avg_severity', 0)
            if avg_severity < 1:
                summary += "Excellent conditions for VFR flight operations."
            else:
                summary += "Good conditions with standard weather monitoring recommended."
        
        return summary
    
    def _generate_pilot_recommendations(self, analysis: Dict, airports: List[str], 
                                      briefing: Dict) -> List[str]:
        """Generate intelligent pilot recommendations based on conditions"""
        recommendations = []
        
        # Critical condition recommendations
        for condition in analysis['critical_conditions']:
            airport = condition['airport']
            hazard = condition['condition']
            
            if hazard['type'] == 'thunderstorms':
                recommendations.append(f"🌩️ AVOID: Thunderstorms at {airport} - consider alternate airport or delay until storms pass")
                recommendations.append("📡 Monitor weather radar continuously and maintain communication with ATC")
                
            elif hazard['type'] == 'low_visibility':
                recommendations.append(f"👁️ VISIBILITY: {airport} reporting {hazard['value']} SM - ensure IFR proficiency and consider alternate")
                recommendations.append("🛬 Brief instrument approach procedures and minimums")
                
            elif hazard['type'] == 'low_ceiling':
                recommendations.append(f"☁️ CEILING: {airport} ceiling {hazard['value']} ft - verify approach minimums and alternate requirements")
                
            elif hazard['type'] == 'strong_winds':
                recommendations.append(f"💨 WINDS: {airport} winds {hazard['description']} - calculate crosswind components for all runways")
                recommendations.append("🛬 Consider airports with more favorable runway orientations")
        
        # Route-specific recommendations
        severe_airports = analysis['airports_by_severity']['severe']
        if severe_airports:
            if len(severe_airports) == 1:
                recommendations.append(f"🎯 FOCUS: Pay special attention to conditions at {severe_airports[0]}")
            else:
                recommendations.append(f"🎯 CRITICAL AIRPORTS: Enhanced monitoring required for {', '.join(severe_airports)}")
        
        # Fuel and alternate recommendations
        if analysis['route_statistics']['avg_severity'] > 3:
            recommendations.append("⛽ FUEL: Carry additional fuel for possible diversions or holding")
            recommendations.append("🛩️ ALTERNATES: File multiple alternate airports along route")
        
        # Equipment and preparation recommendations
        if any('icing' in str(cond) for cond in analysis['critical_conditions']):
            recommendations.append("🧊 EQUIPMENT: Verify anti-ice/de-ice systems operational")
            recommendations.append("📊 PIREPS: Monitor pilot reports for icing conditions")
        
        # Communication recommendations
        if analysis['route_statistics']['critical_airport_count'] > 0:
            recommendations.append("📞 COMMUNICATION: Establish contact with flight operations for real-time updates")
            recommendations.append("🔄 UPDATES: Request weather updates every 30 minutes during flight")
        
        # Default recommendations if conditions are good
        if not recommendations:
            recommendations.extend([
                "✅ CONDITIONS: Weather favorable for planned flight operations",
                "📱 MONITORING: Continue standard weather monitoring procedures",
                "🛩️ EXECUTION: Proceed with normal flight planning and execution"
            ])
        
        return recommendations[:8]  # Limit to most important recommendations
    
    def _generate_phase_guidance(self, analysis: Dict, airports: List[str]) -> Dict:
        """Generate phase-specific flight guidance"""
        guidance = {
            'pre_flight': [],
            'departure': [],
            'enroute': [],
            'arrival': []
        }
        
        # Pre-flight guidance
        if analysis['critical_conditions']:
            guidance['pre_flight'].append("Complete thorough weather briefing with flight operations")
            guidance['pre_flight'].append("Review emergency procedures and alternate airports")
        
        guidance['pre_flight'].append("Verify aircraft equipment operational for expected conditions")
        guidance['pre_flight'].append("Calculate performance data for current weather conditions")
        
        # Departure guidance
        departure_airport = airports[0] if airports else None
        if departure_airport:
            dep_conditions = next((c for c in analysis['critical_conditions'] 
                                 if c['airport'] == departure_airport), None)
            if dep_conditions:
                hazard = dep_conditions['condition']
                if hazard['type'] == 'strong_winds':
                    guidance['departure'].append("Use maximum performance takeoff technique")
                    guidance['departure'].append("Be prepared for wind shear during initial climb")
                elif hazard['type'] == 'low_visibility':
                    guidance['departure'].append("Use instrument departure procedures")
                    guidance['departure'].append("Maintain precise heading and altitude control")
        
        # Enroute guidance
        if len(analysis['moderate_conditions']) > 2:
            guidance['enroute'].append("Monitor weather radar and pilot reports continuously")
            guidance['enroute'].append("Be prepared to deviate around weather systems")
        
        if analysis['dominant_hazards']:
            primary_hazard = analysis['dominant_hazards'][0][0]
            if primary_hazard == 'turbulence':
                guidance['enroute'].append("Maintain turbulence penetration speed when encountering rough air")
            elif primary_hazard == 'icing':
                guidance['enroute'].append("Request altitude changes to avoid icing layers")
        
        # Arrival guidance
        arrival_airport = airports[-1] if airports else None
        if arrival_airport:
            arr_conditions = next((c for c in analysis['critical_conditions'] 
                                 if c['airport'] == arrival_airport), None)
            if arr_conditions:
                hazard = arr_conditions['condition']
                if hazard['type'] == 'low_ceiling':
                    guidance['arrival'].append("Brief instrument approach procedures and minimums")
                    guidance['arrival'].append("Ensure adequate fuel for missed approach and alternate")
                elif hazard['type'] == 'strong_winds':
                    guidance['arrival'].append("Request runway with most favorable wind component")
                    guidance['arrival'].append("Be prepared for go-around if approach becomes unstable")
        
        return guidance
    
    def _assess_flight_risk(self, analysis: Dict) -> str:
        """Assess overall flight risk level"""
        critical_count = len(analysis['critical_conditions'])
        avg_severity = analysis['route_statistics'].get('avg_severity', 0)
        
        if critical_count >= 2 or avg_severity >= 6:
            return 'HIGH'
        elif critical_count >= 1 or avg_severity >= 3:
            return 'MODERATE'
        elif avg_severity >= 1:
            return 'LOW'
        else:
            return 'MINIMAL'
    
    def _extract_decision_factors(self, analysis: Dict) -> List[str]:
        """Extract key decision factors for pilot consideration"""
        factors = []
        
        # Critical factors
        for condition in analysis['critical_conditions']:
            factors.append(f"{condition['airport']}: {condition['condition']['description']}")
        
        # Route statistics
        stats = analysis['route_statistics']
        if stats['critical_airport_count'] > 0:
            factors.append(f"{stats['critical_airport_count']} airport(s) with severe conditions")
        
        # Dominant hazards
        if analysis['dominant_hazards']:
            hazard_name = analysis['dominant_hazards'][0][0].replace('_', ' ').title()
            hazard_count = analysis['dominant_hazards'][0][1]
            factors.append(f"{hazard_name} affecting {hazard_count} location(s)")
        
        return factors[:5]  # Top 5 decision factors
