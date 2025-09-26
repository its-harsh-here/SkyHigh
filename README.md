# SkyHigh

A comprehensive flight planning application that provides real-time aviation weather analysis, NOTAMs processing, and AI-powered risk assessment for pilots and aviation professionals.

## Features

### Core Functionality
- Real-time aviation weather data integration (METAR, TAF, PIREPs, SIGMETs, G-AIRMETs, CWAs)
- Flight route planning with waypoint support
- Timeline-based weather analysis along flight paths
- NOTAMs (Notice to Air Missions) integration and processing
- AI-powered risk assessment and recommendations

### Advanced Capabilities
- Natural Language Processing for flight plan extraction
- METAR code translation to plain English
- Historical weather simulation for departure times up to 15 days past
- Interactive weather timeline visualization
- Comprehensive weather data source aggregation

### User Interface
- Dual input methods: Manual form input and natural language processing
- Interactive charts and visualizations
- Responsive web design
- Real-time UTC clock display
- Tabbed interface for different input modes

## Technology Stack

### Backend
- **Framework**: Flask (Python)
- **APIs**: Aviation Weather Center API (aviationweather.gov)
- **Processing**: Concurrent data fetching, regex-based NLP
- **Data Sources**: METAR, TAF, PIREP, SIGMET, G-AIRMET, CWA, NOTAMs

### Frontend
- **Languages**: HTML5, CSS3, JavaScript
- **Visualization**: Chart.js for timeline graphs
- **Styling**: Custom CSS with CSS Grid and Flexbox
- **Architecture**: Single Page Application (SPA)

## Installation

### Prerequisites
- Python 3.7 or higher
- pip package manager

### Setup Instructions

1. Clone or download the project files
2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Start the Flask application:
   ```
   python app.py
   ```
4. Open your web browser and navigate to:
   ```
   http://localhost:5000
   ```

## Usage

### Manual Flight Planning
1. Enter departure and destination airport codes (ICAO format)
2. Optionally add waypoints and adjust cruise speed
3. Select departure date and time
4. Click "Analyze with AI & NLP" to generate comprehensive weather briefing

### Natural Language Input
1. Switch to "Natural Language" tab
2. Describe your flight plan in plain English
3. Click "Process with NLP" to extract flight details
4. Review extracted information and proceed with analysis

### Weather Timeline Analysis
The system provides:
- 15-minute interval weather analysis along the entire flight path
- Severity categorization (Clear, Significant, Severe)
- Risk percentage calculation and recommendations
- Interactive timeline chart visualization
- Detailed conditions with nearest weather station data

## Data Sources

### Real-time Weather Data
- **Source**: Aviation Weather Center (aviationweather.gov)
- **Coverage**: Worldwide aviation weather information
- **Update Frequency**: Real-time to 3-hour intervals depending on product
- **Historical Range**: Up to 15 days past data available

### NOTAMs Information
- **Current Implementation**: Demo data with time-based simulation
- **Purpose**: Demonstrates NOTAM processing and integration capabilities
- **Data Characteristics**: Realistic formatting, time-sensitive generation, severity classification

### Production NOTAM Integration Options
For production deployment, consider integrating with:
- FAA NOTAM Search API (notams.aim.faa.gov)
- Aviation Edge NOTAM API (commercial)
- ICAO NOTAM Data Service
- SWIM (System Wide Information Management) services

## API Integration Notes

### Current NOTAM Implementation
The system currently uses simulated NOTAMs labeled as "Demo Data (Time-Based)" for demonstration purposes. This approach was chosen because:

- Real NOTAM APIs require authentication and often paid subscriptions
- FAA services require complex registration processes
- Commercial APIs have usage limits and costs
- The demo system provides realistic data for development and testing

### Upgrading to Real NOTAM APIs
To integrate real NOTAM data:

1. **FAA NOTAM Search API**
   - Register at: https://notams.aim.faa.gov/notamWFS/
   - Implement SOAP/REST client integration
   - Handle authentication and rate limiting

2. **Commercial APIs**
   - Aviation Edge NOTAM API (paid service)
   - Provides global NOTAM coverage
   - JSON/XML response formats

3. **SWIM Services**
   - Enterprise-level integration
   - Requires FAA certification process
   - Real-time NOTAM streaming

## Configuration

### Time Zones
- All times displayed and processed in UTC
- Departure time input automatically converted to UTC
- Timeline analysis shows UTC timestamps

### Data Limits
- Weather data: 15 days historical, 4 hours future
- Flight path analysis: Up to 200 nautical mile search radius
- Timeline intervals: 15-minute segments for detailed analysis

## Architecture

### Request Flow
1. User input validation and processing
2. Airport coordinate lookup via Aviation Weather API
3. Flight path calculation with haversine distance formula
4. Concurrent weather data fetching from multiple endpoints
5. Timeline generation with weather condition simulation
6. Risk assessment calculation and natural language summary generation

### Data Processing
- Real-time API calls for current weather conditions
- Historical weather simulation for past departure times
- Weather categorization using aviation-standard criteria
- Natural language processing using regex pattern matching

## Development

### Project Structure
```
├── app.py              # Flask backend application
├── index.html          # Frontend single-page application
├── requirements.txt    # Python dependencies
└── README.md          # Documentation
```

### Key Classes
- `SimpleNLPProcessor`: Handles natural language processing and METAR decoding
- `WeatherProcessor`: Manages API calls, data processing, and timeline generation

### Extending Functionality
The modular architecture supports easy integration of:
- Additional weather data sources
- Enhanced natural language processing capabilities
- Machine learning models for weather prediction
- Real-time NOTAM feeds

## Browser Compatibility

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## Rate Limiting

The application implements responsible API usage:
- Maximum 100 requests per minute to weather APIs
- Concurrent request limiting with timeout handling
- Graceful error handling for rate limit exceeded scenarios

## License

This project is developed for educational and demonstration purposes. Weather data is provided by the Aviation Weather Center. Users should verify all information through official sources before making flight-related decisions.

## Disclaimer

This application is for informational purposes only. All weather information should be verified through official aviation weather sources. Do not use this application as the sole source for flight planning decisions. Always consult official NOTAMs, weather briefings, and follow appropriate aviation regulations and procedures.
