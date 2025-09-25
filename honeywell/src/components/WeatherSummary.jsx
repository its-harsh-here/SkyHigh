import React from 'react';
import { formatDistanceToNow, parseISO } from 'date-fns';
import './WeatherSummary.css';

const WeatherSummary = ({ weatherData }) => {
  const getRecommendationIcon = (recommendation) => {
    if (recommendation.includes('WARNING') || recommendation.includes('AVOID')) {
      return '⚠️';
    } else if (recommendation.includes('CAUTION')) {
      return '🔶';
    } else if (recommendation.includes('INFO')) {
      return 'ℹ️';
    }
    return '💡';
  };

  return (
    <div className="weather-summary">
      {/* Main Summary */}
      <div className="main-summary">
        <h3>Pilot Summary</h3>
        <p className="summary-text">{weatherData.pilot_summary}</p>
        <div className="summary-metadata">
          <span>Updated: {formatDistanceToNow(parseISO(weatherData.generated_at))} ago</span>
          <span>Products: {weatherData.available_products.length}</span>
          {weatherData.hazards.length > 0 && (
            <span className="hazard-indicator">
              ⚠️ {weatherData.hazards.length} hazard{weatherData.hazards.length > 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      {/* Current Conditions */}
      {weatherData.current_conditions && Object.keys(weatherData.current_conditions).length > 0 && (
        <div className="current-conditions">
          <h4>Current Conditions</h4>
          <div className="conditions-grid">
            {weatherData.current_conditions.source && (
              <div className="condition-item">
                <label>Source:</label>
                <span>{weatherData.current_conditions.source}</span>
              </div>
            )}
            {weatherData.current_conditions.wind_speed && (
              <div className="condition-item">
                <label>Wind:</label>
                <span>
                  {weatherData.current_conditions.wind_direction}°/
                  {weatherData.current_conditions.wind_speed}kt
                  {weatherData.current_conditions.wind_gust && 
                    ` G${weatherData.current_conditions.wind_gust}kt`
                  }
                </span>
              </div>
            )}
            {weatherData.current_conditions.visibility && (
              <div className="condition-item">
                <label>Visibility:</label>
                <span>{weatherData.current_conditions.visibility} SM</span>
              </div>
            )}
            {weatherData.current_conditions.temperature !== null && (
              <div className="condition-item">
                <label>Temperature:</label>
                <span>{weatherData.current_conditions.temperature}°C</span>
              </div>
            )}
            {weatherData.current_conditions.turbulence && (
              <div className="condition-item">
                <label>Turbulence:</label>
                <span>{weatherData.current_conditions.turbulence}</span>
              </div>
            )}
            {weatherData.current_conditions.icing && (
              <div className="condition-item">
                <label>Icing:</label>
                <span>{weatherData.current_conditions.icing}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {weatherData.recommendations && weatherData.recommendations.length > 0 && (
        <div className="recommendations">
          <h4>Recommendations</h4>
          <ul>
            {weatherData.recommendations.map((rec, index) => (
              <li key={index} className="recommendation-item">
                <span className="rec-icon">{getRecommendationIcon(rec)}</span>
                <span className="rec-text">{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Critical Hazards */}
      {weatherData.hazards && weatherData.hazards.length > 0 && (
        <div className="hazards-summary">
          <h4>Active Hazards</h4>
          <div className="hazards-grid">
            {weatherData.hazards.slice(0, 3).map((hazard, index) => (
              <div key={index} className={`hazard-card hazard-${hazard.severity?.toLowerCase()}`}>
                <div className="hazard-type">{hazard.type}</div>
                <div className="hazard-details">
                  {hazard.phenomenon || hazard.hazard}
                </div>
                {hazard.valid_until && (
                  <div className="hazard-expires">
                    Until: {new Date(hazard.valid_until).toLocaleString()}
                  </div>
                )}
              </div>
            ))}
          </div>
          {weatherData.hazards.length > 3 && (
            <p className="more-hazards">
              +{weatherData.hazards.length - 3} more hazards (view in Hazards tab)
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default WeatherSummary;
