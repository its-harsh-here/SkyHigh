# Aviation Weather Briefing System

A comprehensive solution that simplifies, automates, and optimizes the process of gathering and analyzing pre-flight briefings for pilots. This tool provides weather information, NOTAMs, and relevant flight briefings using live data from aviationweather.gov.

## Features

### 🧠 **AI-Powered Weather Analysis**
- **Intelligent Executive Summaries**: 2-3 line concise summaries prioritizing critical weather factors
- **NLP-Based Pilot Recommendations**: Smart action items with emoji indicators for quick recognition
- **Risk Assessment**: Automated risk categorization (Minimal/Low/Moderate/High)
- **Decision Factor Analysis**: Key weather elements extracted for pilot decision-making
- **Time-Aware Analysis**: Considers planned departure time for relevant weather forecasting

### 🌦️ **Comprehensive Weather Data**
- **Live Weather Integration**: Real-time METAR, TAF, PIREPs, and SIGMET data from aviationweather.gov
- **Airport Validation**: Live API validation of ICAO airport codes from global database
- **Flight Plan Analysis**: Automatically extracts weather data along flight routes
- **Weather Categorization**: Conditions categorized as Clear, Significant, or Severe
- **Individual Reports**: Complete METAR, TAF, and PIREP data display for any airport

### 📊 **Interactive Visualizations**
- **Wind Analysis Charts**: Wind speed and direction graphs along route
- **Visibility & Ceiling Charts**: Visual representation of flight conditions
- **Color-Coded Route Maps**: Interactive maps showing weather severity
- **Weather Timeline**: Forecast trends and changes over time

### ✈️ **Pilot-Centric Interface**
- **Individual Report Requests**: Get specific reports (METAR, TAF, PIREP) for any airport
- **Flight Route Input**: Manual entry with departure time selection or flight plan upload
- **Airport Code Validation**: Real-time validation of ICAO codes with error feedback
- **Mobile-Friendly Design**: Optimized for use during pre-flight and in-flight operations
- **Priority-Based Display**: Most critical information presented first with clean, focused layout

## Installation

1. Clone or download this repository
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python run.py
   ```
4. Open your browser to `http://localhost:5001`

## Quick Start

### Option 1: Using the Web Interface
1. Navigate to `http://localhost:5001`
2. Enter departure and arrival airports (ICAO codes like KJFK, KLAX)
3. Add waypoints if needed
4. Click "Get Route Briefing" for comprehensive analysis

### Option 2: Testing the API
```bash
# Test the complete system
python final_demo.py

# Test individual components
python test_app.py
```

## Usage

### Flight Plan Input
- Upload a flight plan file, or
- Enter departure airport, arrival airport, and waypoints in ICAO format (e.g., KJFK, EGLL, KORD)

### Weather Briefing
The system will automatically:
1. Extract airports and waypoints from your flight plan
2. Fetch current and forecast weather data from aviationweather.gov
3. Analyze and categorize weather conditions using AI
4. Generate intelligent executive summaries and pilot recommendations
5. Provide phase-specific guidance (pre-flight, departure, en route, arrival)
6. Create interactive visualizations and route maps
7. Assess overall flight risk level

### AI-Powered Analysis
The system provides:
- **Executive Summary**: 2-3 line intelligent summary prioritizing critical weather factors
- **Risk Assessment**: Automated categorization (Minimal → Low → Moderate → High)
- **Pilot Recommendations**: Specific action items with emojis for quick recognition
- **Decision Factors**: Key weather elements affecting flight safety
- **Phase Guidance**: Tailored advice for each flight phase

## Data Sources

- **Primary**: aviationweather.gov API (live data)
- **Weather Products**: METAR, TAF, PIREPs, SIGMETs, G-AIRMETs
- **Coverage**: Global aviation weather data
- **Update Frequency**: Real-time data updated every few minutes
- **API Documentation**: https://aviationweather.gov/data/api/#schema

## System Requirements

- Windows laptop with internet connection
- Python 3.8 or higher
- Modern web browser
- Minimum 4GB RAM recommended

## Weather Severity Categories

- **Clear**: VFR conditions, minimal weather impact
- **Significant**: MVFR conditions, moderate weather impact requiring attention
- **Severe**: IFR conditions, significant weather hazards requiring careful consideration
