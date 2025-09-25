import React, { useState } from 'react';
import { formatDistanceToNow, parseISO } from 'date-fns';
import './WeatherProductViews.css';

const PirepView = ({ data }) => {
  const [showRaw, setShowRaw] = useState(false);
  const [sortBy, setSortBy] = useState('time'); // time, altitude, aircraft

  if (!data || data.length === 0) {
    return (
      <div className="no-data">
        <p>No PIREP data available</p>
        <small>PIREPs are pilot reports of actual flight conditions experienced</small>
      </div>
    );
  }

  const sortedPireps = [...data].sort((a, b) => {
    switch (sortBy) {
      case 'time':
        return new Date(b.report_time) - new Date(a.report_time);
      case 'altitude':
        return (b.altitude || 0) - (a.altitude || 0);
      case 'aircraft':
        return (a.aircraft_type || '').localeCompare(b.aircraft_type || '');
      default:
        return 0;
    }
  });

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'SEVERE': return '🔴';
      case 'SIGNIFICANT': return '🟡';
      case 'CLEAR': return '🟢';
      default: return '⚪';
    }
  };

  return (
    <div className="weather-product-view pirep-view">
      <div className="product-header">
        <h3>PIREPs - Pilot Reports ({data.length})</h3>
        <div className="product-controls">
          <select 
            value={sortBy} 
            onChange={(e) => setSortBy(e.target.value)}
            className="sort-select"
          >
            <option value="time">Sort by Time</option>
            <option value="altitude">Sort by Altitude</option>
            <option value="aircraft">Sort by Aircraft</option>
          </select>
          <button
            onClick={() => setShowRaw(!showRaw)}
            className={`toggle-raw ${showRaw ? 'active' : ''}`}
          >
            {showRaw ? 'Parsed View' : 'Raw Data'}
          </button>
        </div>
      </div>

      {showRaw ? (
        <div className="raw-data-container">
          <h4>Raw PIREP Reports</h4>
          {sortedPireps.map((pirep, index) => (
            <div key={index} className="raw-pirep">
              <div className="raw-header">
                <strong>{pirep.station_id}</strong> - {new Date(pirep.report_time).toLocaleString()}
              </div>
              <div className="raw-text">{pirep.raw_text}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="parsed-data-container">
          <div className="pireps-list">
            {sortedPireps.map((pirep, index) => (
              <div key={index} className={`pirep-card category-${pirep.category.toLowerCase()}`}>
                <div className="pirep-header">
                  <div className="pirep-id">
                    {getCategoryIcon(pirep.category)}
                    <strong>{pirep.station_id}</strong>
                    <span className="reliability-score">
                      Reliability: {(pirep.reliability_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="pirep-time">
                    {formatDistanceToNow(parseISO(pirep.report_time))} ago
                  </div>
                </div>

                <div className="pirep-details">
                  <div className="pirep-flight-info">
                    {pirep.aircraft_type && (
                      <span className="aircraft-type">
                        ✈️ {pirep.aircraft_type}
                      </span>
                    )}
                    {pirep.altitude && (
                      <span className="altitude">
                        📈 FL{Math.floor(pirep.altitude / 100).toString().padStart(3, '0')}
                      </span>
                    )}
                    {pirep.location && (
                      <span className="location">
                        📍 {pirep.location}
                      </span>
                    )}
                  </div>

                  <div className="pirep-conditions">
                    {pirep.turbulence && (
                      <div className="condition-item">
                        <label>Turbulence:</label>
                        <span className="turbulence-report">{pirep.turbulence}</span>
                      </div>
                    )}
                    {pirep.icing && (
                      <div className="condition-item">
                        <label>Icing:</label>
                        <span className="icing-report">{pirep.icing}</span>
                      </div>
                    )}
                    {pirep.visibility && (
                      <div className="condition-item">
                        <label>Visibility:</label>
                        <span>{pirep.visibility}</span>
                      </div>
                    )}
                    {pirep.weather_conditions && (
                      <div className="condition-item">
                        <label>Weather:</label>
                        <span>{pirep.weather_conditions}</span>
                      </div>
                    )}
                    {pirep.wind && (
                      <div className="condition-item">
                        <label>Wind:</label>
                        <span>{pirep.wind}</span>
                      </div>
                    )}
                    {pirep.temperature !== null && (
                      <div className="condition-item">
                        <label>Temperature:</label>
                        <span>{pirep.temperature}°C</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Raw text in a collapsible section */}
                <details className="pirep-raw-toggle">
                  <summary>View Raw Report</summary>
                  <div className="raw-text">{pirep.raw_text}</div>
                </details>
              </div>
            ))}
          </div>

          {/* Summary Stats */}
          <div className="pirep-stats">
            <h4>PIREP Summary</h4>
            <div className="stats-grid">
              <div className="stat-item">
                <label>Total Reports:</label>
                <span>{data.length}</span>
              </div>
              <div className="stat-item">
                <label>With Turbulence:</label>
                <span>{data.filter(p => p.turbulence).length}</span>
              </div>
              <div className="stat-item">
                <label>With Icing:</label>
                <span>{data.filter(p => p.icing).length}</span>
              </div>
              <div className="stat-item">
                <label>Average Reliability:</label>
                <span>
                  {((data.reduce((sum, p) => sum + p.reliability_score, 0) / data.length) * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PirepView;
