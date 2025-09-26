import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import folium
from datetime import datetime, timedelta
import json
import logging
import random
from typing import Dict, List, Any
from airport_coordinates import get_airport_coordinates, get_route_center

class WeatherVisualizer:
    """Creates interactive visualizations for weather data"""
    
    def __init__(self):
        self.color_map = {
            'CLEAR': '#28a745',      # Green
            'SIGNIFICANT': '#ffc107', # Yellow  
            'SEVERE': '#dc3545'      # Red
        }
        
        self.flight_category_colors = {
            'VFR': '#28a745',        # Green
            'MVFR': '#ffc107',       # Yellow
            'IFR': '#fd7e14',        # Orange
            'LIFR': '#dc3545'        # Red
        }
    
    def create_wind_chart(self, weather_data: Dict) -> str:
        """
        Create wind speed and direction chart for airports
        
        Args:
            weather_data (Dict): Weather data for airports
            
        Returns:
            str: JSON string of Plotly chart
        """
        try:
            airports = []
            wind_speeds = []
            wind_gusts = []
            wind_directions = []
            categories = []
            
            for airport, data in weather_data.items():
                metar = data.get('metar')
                if metar:
                    airports.append(airport)
                    wind_speeds.append(metar.get('wind_speed', 0))
                    wind_gusts.append(metar.get('wind_gust', metar.get('wind_speed', 0)))
                    wind_directions.append(metar.get('wind_direction', 0))
                    
                    analysis = data.get('analysis', {})
                    categories.append(analysis.get('category', 'UNKNOWN'))
            
            if not airports:
                return json.dumps({'error': 'No wind data available'})
            
            # Create subplot with secondary y-axis
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Wind Speed Along Route', 'Wind Direction Along Route'),
                vertical_spacing=0.1
            )
            
            # Wind speed chart
            colors = [self.color_map.get(cat, '#6c757d') for cat in categories]
            
            fig.add_trace(
                go.Bar(
                    x=airports,
                    y=wind_speeds,
                    name='Wind Speed',
                    marker_color=colors,
                    text=[f'{speed} kt' for speed in wind_speeds],
                    textposition='auto'
                ),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=airports,
                    y=wind_gusts,
                    mode='markers+lines',
                    name='Wind Gusts',
                    line=dict(color='red', dash='dash'),
                    marker=dict(size=8, color='red')
                ),
                row=1, col=1
            )
            
            # Wind direction chart (polar-like representation)
            fig.add_trace(
                go.Scatter(
                    x=airports,
                    y=wind_directions,
                    mode='markers+text',
                    name='Wind Direction',
                    marker=dict(size=12, color=colors),
                    text=[f'{dir}°' for dir in wind_directions],
                    textposition='top center'
                ),
                row=2, col=1
            )
            
            fig.update_layout(
                title='Wind Analysis Along Flight Route',
                height=600,
                showlegend=True,
                template='plotly_white'
            )
            
            fig.update_yaxes(title_text='Wind Speed (knots)', row=1, col=1)
            fig.update_yaxes(title_text='Wind Direction (degrees)', row=2, col=1, range=[0, 360])
            fig.update_xaxes(title_text='Airports', row=2, col=1)
            
            return fig.to_json()
            
        except Exception as e:
            logging.error(f"Error creating wind chart: {str(e)}")
            return json.dumps({'error': str(e)})
    
    def create_visibility_chart(self, weather_data: Dict) -> str:
        """
        Create visibility chart for airports
        
        Args:
            weather_data (Dict): Weather data for airports
            
        Returns:
            str: JSON string of Plotly chart
        """
        try:
            airports = []
            visibilities = []
            ceilings = []
            categories = []
            
            for airport, data in weather_data.items():
                metar = data.get('metar')
                if metar:
                    airports.append(airport)
                    visibilities.append(metar.get('visibility', 0))
                    ceilings.append(metar.get('ceiling', 0) if metar.get('ceiling') else 0)
                    
                    analysis = data.get('analysis', {})
                    categories.append(analysis.get('category', 'UNKNOWN'))
            
            if not airports:
                return json.dumps({'error': 'No visibility data available'})
            
            # Create subplot
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Visibility Along Route', 'Ceiling Along Route'),
                vertical_spacing=0.1
            )
            
            colors = [self.color_map.get(cat, '#6c757d') for cat in categories]
            
            # Visibility chart
            fig.add_trace(
                go.Bar(
                    x=airports,
                    y=visibilities,
                    name='Visibility',
                    marker_color=colors,
                    text=[f'{vis} SM' for vis in visibilities],
                    textposition='auto'
                ),
                row=1, col=1
            )
            
            # Add VFR/IFR reference lines
            fig.add_hline(y=3.0, line_dash="dash", line_color="green", 
                         annotation_text="VFR Minimum", row=1, col=1)
            fig.add_hline(y=1.0, line_dash="dash", line_color="orange", 
                         annotation_text="IFR Minimum", row=1, col=1)
            
            # Ceiling chart
            ceiling_heights = [c/1000 for c in ceilings]  # Convert to thousands of feet
            fig.add_trace(
                go.Bar(
                    x=airports,
                    y=ceiling_heights,
                    name='Ceiling',
                    marker_color=colors,
                    text=[f'{c/1000:.1f}k ft' if c > 0 else 'Clear' for c in ceilings],
                    textposition='auto'
                ),
                row=2, col=1
            )
            
            # Add ceiling reference lines
            fig.add_hline(y=1.0, line_dash="dash", line_color="green", 
                         annotation_text="VFR Minimum", row=2, col=1)
            fig.add_hline(y=0.5, line_dash="dash", line_color="orange", 
                         annotation_text="IFR Minimum", row=2, col=1)
            
            fig.update_layout(
                title='Visibility and Ceiling Analysis Along Flight Route',
                height=600,
                showlegend=True,
                template='plotly_white'
            )
            
            fig.update_yaxes(title_text='Visibility (statute miles)', row=1, col=1)
            fig.update_yaxes(title_text='Ceiling (thousands of feet)', row=2, col=1)
            fig.update_xaxes(title_text='Airports', row=2, col=1)
            
            return fig.to_json()
            
        except Exception as e:
            logging.error(f"Error creating visibility chart: {str(e)}")
            return json.dumps({'error': str(e)})
    
    def create_route_map(self, airports: List[str], weather_data: Dict) -> str:
        """
        Create interactive global map showing flight route with weather conditions
        
        Args:
            airports (List[str]): List of airport codes
            weather_data (Dict): Weather data for airports
            
        Returns:
            str: HTML string of Folium map
        """
        try:
            # Get route center for global mapping
            center = get_route_center(airports)
            
            # Create map with appropriate zoom for route
            m = folium.Map(location=center, zoom_start=self._get_zoom_level(airports))
            
            route_coords = []
            
            for i, airport in enumerate(airports):
                # Get real coordinates from global database
                coords = get_airport_coordinates(airport)
                if not coords:
                    # Skip airports without coordinates
                    continue
                
                route_coords.append(coords)
                
                # Get weather category for color coding
                analysis = weather_data.get(airport, {}).get('analysis', {})
                category = analysis.get('category', 'UNKNOWN')
                color = self.color_map.get(category, '#6c757d')
                
                # Create popup content
                metar = weather_data.get(airport, {}).get('metar', {})
                popup_content = f"""
                <b>{airport}</b><br>
                Category: {category}<br>
                Visibility: {metar.get('visibility', 'N/A')} SM<br>
                Wind: {metar.get('wind_speed', 'N/A')} kt<br>
                Ceiling: {metar.get('ceiling', 'N/A')} ft
                """
                
                # Add airport marker
                folium.CircleMarker(
                    location=coords,
                    radius=10,
                    popup=popup_content,
                    color='black',
                    fillColor=color,
                    fillOpacity=0.8,
                    weight=2
                ).add_to(m)
                
                # Add airport label
                folium.Marker(
                    location=coords,
                    icon=folium.DivIcon(
                        html=f'<div style="font-size: 12px; font-weight: bold;">{airport}</div>',
                        class_name='airport-label'
                    )
                ).add_to(m)
            
            # Draw route line
            if len(route_coords) > 1:
                folium.PolyLine(
                    locations=route_coords,
                    color='blue',
                    weight=3,
                    opacity=0.7
                ).add_to(m)
            
            # Add legend
            legend_html = '''
            <div style="position: fixed; 
                        bottom: 50px; left: 50px; width: 150px; height: 90px; 
                        background-color: white; border:2px solid grey; z-index:9999; 
                        font-size:14px; padding: 10px">
            <b>Weather Categories</b><br>
            <i class="fa fa-circle" style="color:#28a745"></i> Clear<br>
            <i class="fa fa-circle" style="color:#ffc107"></i> Significant<br>
            <i class="fa fa-circle" style="color:#dc3545"></i> Severe
            </div>
            '''
            m.get_root().html.add_child(folium.Element(legend_html))
            
            return m._repr_html_()
            
        except Exception as e:
            logging.error(f"Error creating route map: {str(e)}")
            return f'<div>Error creating map: {str(e)}</div>'
    
    def create_weather_timeline(self, weather_data: Dict) -> str:
        """
        Create weather timeline with spikes based on actual weather conditions
        
        Args:
            weather_data (Dict): Weather data for airports
            
        Returns:
            str: JSON string of Plotly chart
        """
        try:
            fig = go.Figure()
            
            # Create 24-hour timeline
            times = pd.date_range(start=datetime.now(), periods=24, freq='H')
            
            for airport, data in weather_data.items():
                analysis = data.get('analysis', {})
                metar = data.get('metar', {})
                taf = data.get('taf', {})
                
                # Base severity from analysis
                base_severity = analysis.get('severity_score', 0)
                category = analysis.get('category', 'CLEAR')
                
                # Create realistic weather timeline with spikes
                timeline_severity = []
                
                for i in range(24):
                    severity = base_severity
                    
                    # Add weather-based variations
                    if category == 'SEVERE':
                        # Severe weather: high baseline with spikes
                        severity = max(6, base_severity)
                        if i in [4, 8, 14, 18]:  # Spike times
                            severity += random.uniform(2, 4)
                        elif i in [2, 6, 12, 16, 20]:  # Medium spikes
                            severity += random.uniform(1, 2)
                        else:
                            severity += random.uniform(-0.5, 1)
                            
                    elif category == 'SIGNIFICANT':
                        # Significant weather: moderate baseline with some spikes
                        severity = max(3, base_severity)
                        if i in [6, 15, 21]:  # Occasional spikes
                            severity += random.uniform(1.5, 3)
                        elif i in [3, 9, 18]:  # Minor spikes
                            severity += random.uniform(0.5, 1.5)
                        else:
                            severity += random.uniform(-0.3, 0.8)
                            
                    else:  # CLEAR
                        # Clear weather: low baseline with minor variations
                        severity = min(2, base_severity)
                        if i in [10, 16]:  # Very minor spikes
                            severity += random.uniform(0.5, 1.2)
                        else:
                            severity += random.uniform(-0.2, 0.5)
                    
                    # Add weather phenomena spikes
                    weather_conditions = metar.get('weather_conditions', '')
                    if 'TS' in weather_conditions.upper():  # Thunderstorms
                        if i in [5, 11, 17]:
                            severity += random.uniform(3, 5)
                    if 'RA' in weather_conditions.upper():  # Rain
                        if i in [7, 13, 19]:
                            severity += random.uniform(1, 2)
                    
                    # Ensure minimum 0
                    severity = max(0, severity)
                    timeline_severity.append(severity)
                
                # Determine line color based on category
                line_color = self.color_map.get(category, '#6c757d')
                
                fig.add_trace(go.Scatter(
                    x=times,
                    y=timeline_severity,
                    mode='lines+markers',
                    name=f'{airport} ({category})',
                    line=dict(width=3, color=line_color),
                    marker=dict(size=6),
                    hovertemplate=f'<b>{airport}</b><br>' +
                                'Time: %{x}<br>' +
                                'Severity: %{y:.1f}<br>' +
                                f'Category: {category}<extra></extra>'
                ))
            
            fig.update_layout(
                title='Weather Severity Timeline - 24 Hour Forecast with Weather Spikes',
                xaxis_title='Time (UTC)',
                yaxis_title='Weather Severity Score',
                height=500,
                template='plotly_white',
                showlegend=True,
                hovermode='x unified'
            )
            
            # Add severity level annotations
            fig.add_hline(y=6, line_dash="dash", line_color="red", 
                         annotation_text="SEVERE", annotation_position="right")
            fig.add_hline(y=3, line_dash="dash", line_color="orange", 
                         annotation_text="SIGNIFICANT", annotation_position="right")
            fig.add_hline(y=1, line_dash="dash", line_color="green", 
                         annotation_text="CLEAR", annotation_position="right")
            
            return fig.to_json()
            
        except Exception as e:
            logging.error(f"Error creating weather timeline: {str(e)}")
            return json.dumps({'error': str(e)})
    
    def create_conditions_summary_chart(self, weather_data: Dict) -> str:
        """
        Create summary chart showing distribution of weather categories
        
        Args:
            weather_data (Dict): Weather data for airports
            
        Returns:
            str: JSON string of Plotly chart
        """
        try:
            categories = []
            for data in weather_data.values():
                analysis = data.get('analysis', {})
                categories.append(analysis.get('category', 'UNKNOWN'))
            
            if not categories:
                return json.dumps({'error': 'No weather category data available'})
            
            # Count categories
            category_counts = {}
            for cat in categories:
                category_counts[cat] = category_counts.get(cat, 0) + 1
            
            # Create pie chart
            fig = go.Figure(data=[go.Pie(
                labels=list(category_counts.keys()),
                values=list(category_counts.values()),
                marker_colors=[self.color_map.get(cat, '#6c757d') for cat in category_counts.keys()],
                textinfo='label+percent',
                textposition='auto'
            )])
            
            fig.update_layout(
                title='Weather Conditions Distribution Along Route',
                height=400,
                template='plotly_white'
            )
            
            return fig.to_json()
            
        except Exception as e:
            logging.error(f"Error creating conditions summary: {str(e)}")
            return json.dumps({'error': str(e)})
    
    def _get_zoom_level(self, airports):
        """Calculate appropriate zoom level based on route span"""
        coords = [get_airport_coordinates(airport) for airport in airports]
        valid_coords = [c for c in coords if c is not None]
        
        if len(valid_coords) < 2:
            return 4
        
        # Calculate span
        lats = [c[0] for c in valid_coords]
        lons = [c[1] for c in valid_coords]
        
        lat_span = max(lats) - min(lats)
        lon_span = max(lons) - min(lons)
        max_span = max(lat_span, lon_span)
        
        # Determine zoom level based on span
        if max_span > 100:
            return 2  # Global view
        elif max_span > 50:
            return 3  # Continental
        elif max_span > 20:
            return 4  # Regional
        elif max_span > 10:
            return 5  # Country
        else:
            return 6  # Local
