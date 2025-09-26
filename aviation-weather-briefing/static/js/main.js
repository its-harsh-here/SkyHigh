// Aviation Weather Briefing System - Main JavaScript

// Global variables
let currentWeatherData = null;
let currentBriefing = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    loadSampleData();
});

function initializeEventListeners() {
    // Manual form submission
    document.getElementById('manualForm').addEventListener('submit', handleManualSubmit);
    
    // Individual weather form submission
    document.getElementById('individualForm').addEventListener('submit', handleIndividualSubmit);
    
    // File upload handling
    document.getElementById('flightPlanFile').addEventListener('change', handleFileUpload);
    
    // Input validation
    setupInputValidation();
}

function setupInputValidation() {
    // ICAO code validation
    const icaoInputs = document.querySelectorAll('#departure, #arrival, #airportCode');
    icaoInputs.forEach(input => {
        input.addEventListener('input', function() {
            this.value = this.value.toUpperCase().replace(/[^A-Z]/g, '');
        });
    });
    
    // Waypoints validation
    document.getElementById('waypoints').addEventListener('input', function() {
        this.value = this.value.toUpperCase();
    });
}

function handleManualSubmit(event) {
    event.preventDefault();
    
    const departure = document.getElementById('departure').value.trim().toUpperCase();
    const arrival = document.getElementById('arrival').value.trim().toUpperCase();
    const waypoints = document.getElementById('waypoints').value.trim();
    const departureTime = document.getElementById('departureTime').value;
    
    if (!validateICAOCode(departure) || !validateICAOCode(arrival)) {
        showError('Please enter valid 4-letter ICAO airport codes');
        return;
    }
    
    const waypointList = waypoints ? waypoints.split(',').map(w => w.trim()).filter(w => w) : [];
    
    // Validate waypoints
    for (let waypoint of waypointList) {
        if (!validateICAOCode(waypoint)) {
            showError(`Invalid waypoint: ${waypoint}. Please use 4-letter ICAO codes.`);
            return;
        }
    }
    
    analyzeRoute({
        departure: departure,
        arrival: arrival,
        waypoints: waypointList,
        departure_time: departureTime
    });
}

function handleIndividualSubmit(event) {
    event.preventDefault();
    
    const airportCode = document.getElementById('airportCode').value.trim();
    
    if (!validateICAOCode(airportCode)) {
        showError('Please enter a valid 4-letter ICAO airport code');
        return;
    }
    
    const reportTypes = [];
    if (document.getElementById('metarCheck').checked) reportTypes.push('METAR');
    if (document.getElementById('tafCheck').checked) reportTypes.push('TAF');
    if (document.getElementById('pirepCheck').checked) reportTypes.push('PIREP');
    
    if (reportTypes.length === 0) {
        showError('Please select at least one report type');
        return;
    }
    
    getIndividualWeather(airportCode, reportTypes);
}

function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        document.getElementById('flightPlanText').value = e.target.result;
    };
    reader.readAsText(file);
}

function analyzeFlightPlan() {
    const flightPlanText = document.getElementById('flightPlanText').value.trim();
    
    if (!flightPlanText) {
        showError('Please upload a flight plan file or paste flight plan text');
        return;
    }
    
    analyzeRoute({
        flight_plan_text: flightPlanText
    });
}

function analyzeRoute(routeData) {
    showLoading();
    hideResults();
    
    fetch('/api/flight-plan/analyze', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(routeData)
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        
        if (data.error) {
            showErrorMessage(data.error);
            return;
        }
        
        currentWeatherData = data.weather_data;
        currentBriefing = data.briefing;
        
        displayBriefingResults(data);
        updateQuickSummary(data);
    })
    .catch(error => {
        hideLoading();
        showError('Failed to fetch weather data: ' + error.message);
    });
}

function getIndividualWeather(airportCode, reportTypes) {
    showLoading();
    hideResults();
    
    fetch('/api/weather/individual', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            airport_code: airportCode,
            report_types: reportTypes
        })
    })
    .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.error) {
                showErrorMessage(data.error);
                return;
            }
            displayIndividualResults(data, airportCode);
        })
    .catch(error => {
        hideLoading();
        showErrorMessage('Failed to fetch weather data: ' + error.message);
    });
}

function displayBriefingResults(data) {
    const briefingResults = document.getElementById('briefingResults');
    const individualResults = document.getElementById('individualResults');
    
    // Hide individual results, show briefing
    individualResults.classList.add('d-none');
    briefingResults.classList.remove('d-none');
    
    // Update NLP analysis sections
    if (data.nlp_analysis) {
        displayNLPAnalysis(data.nlp_analysis);
    }
    
    // Traditional briefing section removed - no need to update category badge
    
    // Create visualizations
    if (data.visualizations) {
        createWindChart(data.visualizations.wind_chart);
        createVisibilityChart(data.visualizations.visibility_chart);
        createRouteMap(data.visualizations.route_map);
        createWeatherTimeline(data.visualizations.weather_timeline);
    }
    
    // Display detailed airport weather
    displayAirportDetails(data.weather_data, data.airports);
    
    // Display route information
    if (data.route_info) {
        displayRouteInfo(data.route_info);
    }
    
    // Scroll to results
    briefingResults.scrollIntoView({ behavior: 'smooth' });
}
function displayNLPAnalysis(nlpData) {
    // Display executive summary
    const executiveSummary = document.getElementById('executiveSummary');
    executiveSummary.innerHTML = `
        <div class="alert alert-info mb-3">
            <h6><i class="fas fa-lightbulb"></i> Executive Summary</h6>
            <p class="mb-0">${nlpData.executive_summary || 'No summary available'}</p>
        </div>
    `;
    
    // Display risk assessment
    const riskBadge = document.getElementById('riskAssessment');
    const riskLevel = nlpData.risk_assessment || 'UNKNOWN';
    riskBadge.textContent = `${riskLevel} RISK`;
    riskBadge.className = `badge ${getRiskBadgeClass(riskLevel)}`;
    
    // Display decision factors
    const decisionFactors = document.getElementById('decisionFactors');
    if (nlpData.decision_factors && nlpData.decision_factors.length > 0) {
        decisionFactors.innerHTML = `
            <h6><i class="fas fa-exclamation-triangle"></i> Key Decision Factors</h6>
            <ul class="list-group list-group-flush">
                ${nlpData.decision_factors.map(factor => `
                    <li class="list-group-item px-0 py-2">
                        <i class="fas fa-arrow-right text-warning me-2"></i>${factor}
                    </li>
                `).join('')}
            </ul>
        `;
    } else {
        decisionFactors.innerHTML = '<p class="text-muted">No critical decision factors identified.</p>';
    }
    
    // Display pilot recommendations
    const pilotRecommendations = document.getElementById('pilotRecommendations');
    if (nlpData.pilot_recommendations && nlpData.pilot_recommendations.length > 0) {
        pilotRecommendations.innerHTML = `
            <div class="row">
                ${nlpData.pilot_recommendations.map((rec, index) => `
                    <div class="col-md-6 mb-2">
                        <div class="d-flex align-items-start">
                            <div class="badge bg-primary me-2 mt-1">${index + 1}</div>
                            <div class="flex-grow-1">
                                <span class="recommendation-text">${rec}</span>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } else {
        pilotRecommendations.innerHTML = '<p class="text-muted">No specific recommendations at this time.</p>';
    }
    
    // Phase guidance removed as requested
}

function getRiskBadgeClass(riskLevel) {
    switch (riskLevel.toUpperCase()) {
        case 'HIGH':
            return 'bg-danger';
        case 'MODERATE':
            return 'bg-warning text-dark';
        case 'LOW':
            return 'bg-info';
        case 'MINIMAL':
            return 'bg-success';
        default:
            return 'bg-secondary';
    }
}

function displayIndividualResults(data, airportCode) {
    const briefingResults = document.getElementById('briefingResults');
    const individualResults = document.getElementById('individualResults');
    
    // Hide briefing results, show individual
    briefingResults.classList.add('d-none');
    individualResults.classList.remove('d-none');
    
    const weatherDataDiv = document.getElementById('individualWeatherData');
    weatherDataDiv.innerHTML = generateIndividualWeatherHTML(data, airportCode);
    
    // Scroll to results
    individualResults.scrollIntoView({ behavior: 'smooth' });
}

function generateBriefingSummaryHTML(briefing) {
    let html = `
        <div class="row">
            <div class="col-md-8">
                <h6>Route Summary</h6>
                <p>${briefing.route_summary || 'No summary available'}</p>
                
                ${briefing.route_hazards && briefing.route_hazards.length > 0 ? `
                <h6>Route Hazards</h6>
                <div class="hazard-alert ${briefing.overall_category === 'SEVERE' ? 'severe' : ''}">
                    <i class="fas fa-exclamation-triangle"></i>
                    <ul class="mb-0">
                        ${briefing.route_hazards.map(hazard => `<li>${hazard}</li>`).join('')}
                    </ul>
                </div>
                ` : ''}
                
                ${briefing.recommendations && briefing.recommendations.length > 0 ? `
                <h6>Recommendations</h6>
                <ul class="recommendation-list">
                    ${briefing.recommendations.map(rec => `<li class="${getRecommendationClass(rec)}">${rec}</li>`).join('')}
                </ul>
                ` : ''}
            </div>
            <div class="col-md-4">
                ${briefing.critical_airports && briefing.critical_airports.length > 0 ? `
                <h6>Critical Airports</h6>
                ${briefing.critical_airports.map(airport => `
                    <div class="airport-card ${airport.category.toLowerCase()}">
                        <div class="card-body p-2">
                            <h6 class="card-title mb-1">${airport.airport}</h6>
                            <span class="badge badge-${airport.category.toLowerCase()}">${airport.category}</span>
                            ${airport.issues.map(issue => `<div class="small text-muted mt-1">${issue}</div>`).join('')}
                        </div>
                    </div>
                `).join('')}
                ` : '<p class="text-muted">No critical airports identified</p>'}
            </div>
        </div>
    `;
    
    return html;
}

function generateIndividualWeatherHTML(data, airportCode) {
    let html = `<h5>${airportCode} Weather Report</h5>`;
    
    if (data.metar) {
        html += generateMETARHTML(data.metar);
    }
    
    if (data.taf) {
        html += generateTAFHTML(data.taf);
    }
    
    if (data.pirep && data.pirep.length > 0) {
        html += generatePIREPHTML(data.pirep);
    } else {
        html += `
            <div class="card mb-3">
                <div class="card-header">
                    <h6><i class="fas fa-plane"></i> PIREPs (Pilot Reports)</h6>
                </div>
                <div class="card-body">
                    <div class="alert alert-warning py-2">
                        <i class="fas fa-info-circle me-2"></i>
                        No recent pilot reports available for this airport. PIREPs are voluntary reports from pilots and may not always be available.
                    </div>
                </div>
            </div>
        `;
    }
    
    if (data.analysis) {
        html += generateAnalysisHTML(data.analysis);
    }
    
    return html;
}

function generateMETARHTML(metar) {
    return `
        <div class="card mb-3">
            <div class="card-header">
                <h6><i class="fas fa-thermometer-half"></i> METAR</h6>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <div class="weather-metric">
                            <span class="metric-label">Raw Text:</span>
                            <code class="metric-value">${metar.raw_text || 'N/A'}</code>
                        </div>
                        <div class="weather-metric">
                            <span class="metric-label">Observation Time:</span>
                            <span class="metric-value">${formatDateTime(metar.observation_time)}</span>
                        </div>
                        <div class="weather-metric">
                            <span class="metric-label">Flight Category:</span>
                            <span class="badge flight-category-${(metar.flight_category || 'unknown').toLowerCase()}">${metar.flight_category || 'UNKNOWN'}</span>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="weather-metric">
                            <span class="metric-label">Visibility:</span>
                            <span class="metric-value">${metar.visibility || 'N/A'} SM</span>
                        </div>
                        <div class="weather-metric">
                            <span class="metric-label">Wind:</span>
                            <span class="metric-value">${formatWind(metar)}</span>
                        </div>
                        <div class="weather-metric">
                            <span class="metric-label">Temperature:</span>
                            <span class="metric-value">${metar.temperature || 'N/A'}°C</span>
                        </div>
                        <div class="weather-metric">
                            <span class="metric-label">Altimeter:</span>
                            <span class="metric-value">${metar.altimeter || 'N/A'} inHg</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function generateTAFHTML(taf) {
    // Parse TAF for summary
    const summary = parseTAFSummary(taf.raw_text || '');
    
    return `
        <div class="card mb-3">
            <div class="card-header">
                <h6><i class="fas fa-calendar-alt"></i> TAF (Terminal Aerodrome Forecast)</h6>
            </div>
            <div class="card-body">
                <div class="weather-metric">
                    <span class="metric-label">Forecast Summary:</span>
                    <div class="metric-value">
                        <div class="alert alert-info py-2 mb-2">
                            ${summary}
                        </div>
                    </div>
                </div>
                <div class="weather-metric">
                    <span class="metric-label">Valid Period:</span>
                    <span class="metric-value">${formatDateTime(taf.valid_time_from)} - ${formatDateTime(taf.valid_time_to)}</span>
                </div>
                <div class="weather-metric">
                    <span class="metric-label">Raw Text:</span>
                    <code class="metric-value">${taf.raw_text || 'N/A'}</code>
                </div>
            </div>
        </div>
    `;
}

function parseTAFSummary(rawTAF) {
    if (!rawTAF) return 'No forecast data available';
    
    const taf = rawTAF.toUpperCase();
    let summary = [];
    
    // Check for weather phenomena
    if (taf.includes('TS')) {
        summary.push('⛈️ Thunderstorms forecast');
    }
    if (taf.includes('RA') || taf.includes('SN')) {
        summary.push('🌧️ Precipitation expected');
    }
    if (taf.includes('FG') || taf.includes('BR')) {
        summary.push('🌫️ Fog/mist conditions');
    }
    if (taf.includes('TEMPO')) {
        summary.push('⏱️ Temporary conditions expected');
    }
    if (taf.includes('PROB')) {
        summary.push('📊 Probability conditions forecast');
    }
    if (taf.includes('BECMG')) {
        summary.push('🔄 Changing conditions expected');
    }
    
    // Check for wind information
    const windMatch = taf.match(/(\d{3})(\d{2,3})(G\d{2,3})?KT/);
    if (windMatch) {
        const windDir = windMatch[1];
        const windSpeed = windMatch[2];
        const gust = windMatch[3] ? windMatch[3].replace('G', '') : null;
        
        if (gust && parseInt(gust) > 25) {
            summary.push(`💨 Strong wind gusts to ${gust} knots`);
        } else if (parseInt(windSpeed) > 20) {
            summary.push(`💨 Strong winds ${windSpeed} knots`);
        }
    }
    
    if (summary.length === 0) {
        summary.push('☀️ Generally favorable conditions forecast');
    }
    
    return summary.join('<br>');
}

function generatePIREPHTML(pireps) {
    let html = `
        <div class="card mb-3">
            <div class="card-header">
                <h6><i class="fas fa-plane"></i> PIREPs (Pilot Reports)</h6>
            </div>
            <div class="card-body">
    `;
    
    pireps.forEach((pirep, index) => {
        html += `
            <div class="mb-3 ${index < pireps.length - 1 ? 'border-bottom pb-3' : ''}">
                <div class="weather-metric">
                    <span class="metric-label">Report:</span>
                    <code class="metric-value">${pirep.raw_text || 'N/A'}</code>
                </div>
                <div class="weather-metric">
                    <span class="metric-label">Time:</span>
                    <span class="metric-value">${formatDateTime(pirep.observation_time)}</span>
                </div>
                ${pirep.aircraft_type ? `
                <div class="weather-metric">
                    <span class="metric-label">Aircraft:</span>
                    <span class="metric-value">${pirep.aircraft_type}</span>
                </div>
                ` : ''}
                ${pirep.altitude ? `
                <div class="weather-metric">
                    <span class="metric-label">Altitude:</span>
                    <span class="metric-value">${pirep.altitude} ft</span>
                </div>
                ` : ''}
            </div>
        `;
    });
    
    html += `
            </div>
        </div>
    `;
    
    return html;
}

function generateAnalysisHTML(analysis) {
    return `
        <div class="card mb-3">
            <div class="card-header">
                <h6><i class="fas fa-chart-bar"></i> Weather Analysis</h6>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <div class="weather-metric">
                            <span class="metric-label">Category:</span>
                            <span class="badge badge-${analysis.category.toLowerCase()}">${analysis.category}</span>
                        </div>
                        <div class="weather-metric">
                            <span class="metric-label">Summary:</span>
                            <span class="metric-value">${analysis.summary}</span>
                        </div>
                    </div>
                    <div class="col-md-6">
                        ${analysis.key_factors && analysis.key_factors.length > 0 ? `
                        <h6>Key Factors:</h6>
                        <ul class="small">
                            ${analysis.key_factors.map(factor => `<li>${factor}</li>`).join('')}
                        </ul>
                        ` : ''}
                    </div>
                </div>
                
                ${analysis.hazards && analysis.hazards.length > 0 ? `
                <div class="hazard-alert mt-3">
                    <i class="fas fa-exclamation-triangle"></i>
                    <strong>Hazards:</strong>
                    <ul class="mb-0 mt-2">
                        ${analysis.hazards.map(hazard => `<li>${hazard}</li>`).join('')}
                    </ul>
                </div>
                ` : ''}
                
                ${analysis.recommendations && analysis.recommendations.length > 0 ? `
                <h6 class="mt-3">Recommendations:</h6>
                <ul class="recommendation-list">
                    ${analysis.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                </ul>
                ` : ''}
            </div>
        </div>
    `;
}

function displayAirportDetails(weatherData, airports) {
    const detailsDiv = document.getElementById('airportDetails');
    let html = '';
    
    airports.forEach(airport => {
        const data = weatherData[airport];
        if (data && data.metar) {
            const analysis = data.analysis || {};
            html += `
                <div class="airport-card ${analysis.category ? analysis.category.toLowerCase() : ''}">
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-3">
                                <h6>${airport}</h6>
                                <span class="badge badge-${analysis.category ? analysis.category.toLowerCase() : 'secondary'}">${analysis.category || 'UNKNOWN'}</span>
                            </div>
                            <div class="col-md-9">
                                <div class="row">
                                    <div class="col-sm-6">
                                        <small class="text-muted">Visibility:</small> ${data.metar.visibility || 'N/A'} SM<br>
                                        <small class="text-muted">Wind:</small> ${formatWind(data.metar)}<br>
                                    </div>
                                    <div class="col-sm-6">
                                        <small class="text-muted">Ceiling:</small> ${data.metar.ceiling || 'N/A'} ft<br>
                                        <small class="text-muted">Flight Cat:</small> ${data.metar.flight_category || 'N/A'}<br>
                                    </div>
                                </div>
                                ${data.metar.raw_text ? `<small class="text-muted d-block mt-2"><code>${data.metar.raw_text}</code></small>` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
    });
    
    detailsDiv.innerHTML = html || '<p class="text-muted">No detailed weather data available</p>';
}

function createWindChart(chartData) {
    const container = document.getElementById('windChart');
    if (!container) {
        console.error('Wind chart container not found');
        return;
    }
    
    if (chartData && !chartData.error) {
        try {
            const plotData = JSON.parse(chartData);
            Plotly.newPlot('windChart', plotData.data, plotData.layout, {responsive: true});
            console.log('Wind chart created successfully');
        } catch (error) {
            console.error('Error creating wind chart:', error);
            container.innerHTML = '<div class="alert alert-warning">Error loading wind chart</div>';
        }
    } else {
        container.innerHTML = '<div class="alert alert-info">No wind data available</div>';
    }
}

function createVisibilityChart(chartData) {
    const container = document.getElementById('visibilityChart');
    if (!container) {
        console.error('Visibility chart container not found');
        return;
    }
    
    if (chartData && !chartData.error) {
        try {
            const plotData = JSON.parse(chartData);
            Plotly.newPlot('visibilityChart', plotData.data, plotData.layout, {responsive: true});
            console.log('Visibility chart created successfully');
        } catch (error) {
            console.error('Error creating visibility chart:', error);
            container.innerHTML = '<div class="alert alert-warning">Error loading visibility chart</div>';
        }
    } else {
        container.innerHTML = '<div class="alert alert-info">No visibility data available</div>';
    }
}

function createRouteMap(mapData) {
    const container = document.getElementById('routeMap');
    if (!container) {
        console.error('Route map container not found');
        return;
    }
    
    if (mapData && !mapData.includes('Error')) {
        container.innerHTML = mapData;
        console.log('Route map created successfully');
    } else {
        container.innerHTML = '<div class="alert alert-warning">Error loading route map</div>';
    }
}

function createWeatherTimeline(chartData) {
    const container = document.getElementById('weatherTimeline');
    if (!container) {
        console.error('Weather timeline container not found');
        return;
    }
    
    if (chartData && !chartData.error) {
        try {
            const plotData = JSON.parse(chartData);
            Plotly.newPlot('weatherTimeline', plotData.data, plotData.layout, {responsive: true});
            console.log('Weather timeline created successfully');
        } catch (error) {
            console.error('Error creating weather timeline:', error);
            container.innerHTML = '<div class="alert alert-warning">Error loading weather timeline</div>';
        }
    } else {
        container.innerHTML = '<div class="alert alert-info">No timeline data available</div>';
    }
}

function updateQuickSummary(data) {
    const summaryDiv = document.getElementById('quickSummary');
    const briefing = data.briefing;
    
    let html = `
        <div class="summary-item">
            <span>Overall Condition:</span>
            <span class="summary-category badge-${briefing.overall_category.toLowerCase()}">${briefing.overall_category}</span>
        </div>
        <div class="summary-item">
            <span>Airports:</span>
            <span>${data.airports.length}</span>
        </div>
    `;
    
    if (briefing.critical_airports && briefing.critical_airports.length > 0) {
        html += `
            <div class="summary-item">
                <span>Critical Airports:</span>
                <span class="text-warning">${briefing.critical_airports.length}</span>
            </div>
        `;
    }
    
    summaryDiv.innerHTML = html;
}

// Utility functions
function validateICAOCode(code) {
    return /^[A-Z]{4}$/.test(code);
}

function formatWind(metar) {
    if (!metar.wind_speed) return 'Calm';
    
    let windStr = `${metar.wind_direction || 'VRB'}° at ${metar.wind_speed} kt`;
    if (metar.wind_gust) {
        windStr += ` G${metar.wind_gust} kt`;
    }
    return windStr;
}

function formatDateTime(dateTimeStr) {
    if (!dateTimeStr) return 'N/A';
    
    try {
        const date = new Date(dateTimeStr);
        return date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            timeZone: 'UTC',
            timeZoneName: 'short'
        });
    } catch (e) {
        return dateTimeStr;
    }
}

function getRecommendationClass(recommendation) {
    const lower = recommendation.toLowerCase();
    if (lower.includes('delay') || lower.includes('caution') || lower.includes('emergency')) {
        return 'critical';
    } else if (lower.includes('monitor') || lower.includes('consider')) {
        return 'warning';
    }
    return '';
}

function showLoading() {
    document.getElementById('loadingSpinner').classList.remove('d-none');
}

function hideLoading() {
    document.getElementById('loadingSpinner').classList.add('d-none');
}

function showErrorMessage(message) {
    // Remove any existing error messages
    const existingError = document.querySelector('.error-alert');
    if (existingError) {
        existingError.remove();
    }
    
    // Create error message
    const errorHTML = `
        <div class="alert alert-danger alert-dismissible fade show error-alert" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>
            <strong>Error:</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    // Insert error message at the top of the main content
    const mainContent = document.querySelector('.container-fluid');
    if (mainContent) {
        mainContent.insertAdjacentHTML('afterbegin', errorHTML);
        
        // Scroll to error message
        document.querySelector('.error-alert').scrollIntoView({ behavior: 'smooth' });
    }
}

function hideResults() {
    document.getElementById('briefingResults').classList.add('d-none');
    document.getElementById('individualResults').classList.add('d-none');
}

function showError(message) {
    // Create or update error message
    let errorDiv = document.getElementById('errorMessage');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.id = 'errorMessage';
        errorDiv.className = 'error-message';
        document.querySelector('.col-md-8').insertBefore(errorDiv, document.querySelector('.col-md-8').firstChild);
    }
    
    errorDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`;
    errorDiv.scrollIntoView({ behavior: 'smooth' });
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        if (errorDiv) {
            errorDiv.remove();
        }
    }, 5000);
}

function loadSampleData() {
    // Optionally load some sample data or tips for first-time users
    const quickSummary = document.getElementById('quickSummary');
    quickSummary.innerHTML = `
        <div class="text-center">
            <i class="fas fa-info-circle text-primary mb-2" style="font-size: 2rem;"></i>
            <p class="mb-1"><strong>Welcome to Aviation Weather Briefing</strong></p>
            <p class="small text-muted mb-0">Enter your flight details to get comprehensive weather analysis</p>
        </div>
    `;
}

function displayRouteInfo(routeInfo) {
    // Find a good place to display route info - let's add it to the NLP section
    const executiveSummary = document.getElementById('executiveSummary');
    if (executiveSummary) {
        // Remove any existing route info first
        const existingRouteInfo = document.querySelector('.route-info-alert');
        if (existingRouteInfo) {
            existingRouteInfo.remove();
        }
        
        const routeInfoHTML = `
            <div class="alert alert-success mb-3 route-info-alert">
                <h6><i class="fas fa-route"></i> Route Information</h6>
                <div class="row">
                    <div class="col-md-6">
                        <strong>Distance:</strong> ${routeInfo.total_distance_nm} nautical miles<br>
                        <strong>Route:</strong> ${routeInfo.departure_airport} → ${routeInfo.arrival_airport}
                        ${routeInfo.waypoints_count > 0 ? ` (${routeInfo.waypoints_count} waypoints)` : ''}
                    </div>
                    <div class="col-md-6">
                        <strong>Current Time (UTC):</strong> ${routeInfo.current_utc_time}<br>
                        <strong>Analysis Generated:</strong> Just now
                    </div>
                </div>
            </div>
        `;
        
        // Insert route info before the executive summary
        executiveSummary.insertAdjacentHTML('beforebegin', routeInfoHTML);
    }
}
