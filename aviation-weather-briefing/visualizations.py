import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import folium
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Any

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
        Create interactive map showing flight route with weather conditions
        
        Args:
            airports (List[str]): List of airport codes
            weather_data (Dict): Weather data for airports
            
        Returns:
            str: HTML string of Folium map
        """
        try:
            # This is a simplified version - in production, you'd need airport coordinates
            # For now, create a basic map structure
            
            # Center map on approximate route center (placeholder coordinates)
            m = folium.Map(location=[39.8283, -98.5795], zoom_start=4)
            
            # Sample coordinates for demonstration (in production, use airport database)
            sample_coords = {
                'KJFK': [40.6413, -73.7781],
                'KORD': [41.9742, -87.9073],
                'KDEN': [39.8561, -104.6737],
                'KLAX': [34.0522, -118.2437],
                'KATL': [33.6407, -84.4277],
                'KDFW': [32.8998, -97.0403],
                'KPHX': [33.4484, -112.0740],
                'KLAS': [36.0840, -115.1537]
            }
            
            route_coords = []
            
            for i, airport in enumerate(airports):
                # Use sample coordinates or default location
                if airport in sample_coords:
                    coords = sample_coords[airport]
                else:
                    # Default to approximate US center with offset
                    coords = [39.8283 + (i * 2), -98.5795 + (i * 3)]
                
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
        Create timeline showing weather trends (using TAF data if available)
        
        Args:
            weather_data (Dict): Weather data for airports
            
        Returns:
            str: JSON string of Plotly chart
        """
        try:
            # This is a simplified version - would need TAF parsing for full timeline
            airports = list(weather_data.keys())
            current_time = datetime.utcnow()
            
            # Create sample timeline data
            times = [current_time + timedelta(hours=i) for i in range(0, 13, 3)]
            
            fig = go.Figure()
            
            for airport in airports[:3]:  # Limit to first 3 airports for clarity
                analysis = weather_data.get(airport, {}).get('analysis', {})
                category = analysis.get('category', 'UNKNOWN')
                
                # Create sample trend data (in production, parse TAF forecasts)
                severity_scores = [analysis.get('severity_score', 0)] * len(times)
                
                fig.add_trace(go.Scatter(
                    x=times,
                    y=severity_scores,
                    mode='lines+markers',
                    name=airport,
                    line=dict(width=3),
                    marker=dict(size=8)
                ))
            
            fig.update_layout(
                title='Weather Severity Timeline (Next 12 Hours)',
                xaxis_title='Time (UTC)',
                yaxis_title='Severity Score',
                height=400,
                template='plotly_white',
                showlegend=True
            )
            
            # Add severity level reference lines
            fig.add_hline(y=2, line_dash="dash", line_color="green", 
                         annotation_text="Clear/Significant Threshold")
            fig.add_hline(y=5, line_dash="dash", line_color="orange", 
                         annotation_text="Significant/Severe Threshold")
            
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
