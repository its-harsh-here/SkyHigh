import React, { useState } from 'react';
import { formatDistanceToNow, parseISO } from 'date-fns';
import './WeatherProductViews.css';

const MetarView = ({ data }) => {
  const [showRaw, setShowRaw] = useState(false);

  if (!data) {
    return (
      <div className="no-data">
        <p>No METAR data available</p>
      </div>
    );
  }

  const getWindDescription = () => {
    if (!data.wind) return 'Calm';
    
    if (data.wind.speed === 0) return 'Calm';
    
    let desc = `${data.wind.direction}° at ${data.wind.speed} knots`;
    if (data.wind.gust) {
      desc += ` gusting to ${data.wind.gust} knots`;
    }
    if (data.wind.variable) {
      desc = `Variable at ${data.wind.speed} knots`;
    }
    
    return desc;
  };

  const getCloudDescription = () => {
    if (!data.clouds || data.clouds.length === 0) return 'Clear skies';
    
    return data.clouds.map(cloud => {
      let desc = cloud.coverage;
      if (cloud.base) {
        desc += ` at ${cloud.base.toLocaleString()} ft`;
      }
      return desc;
    }).join(', ');
  };

  const getWeatherDescription = () => {
    if (!data.weather_conditions || data.weather_conditions.length === 0) {
      return 'No significant weather';
    }
    
    return data.weather_conditions.map(condition => {
      let desc = '';
      if (condition.intensity) desc += condition.intensity + ' ';
      if (condition.descriptor) desc += condition.descriptor + ' ';
      desc += condition.precipitation.join(', ');
      desc += condition.obscuration.join(', ');
      return desc;
    }).join('; ');
  };

  return (
    <div className="weather-product-view metar-view">
      <div className="product-header">
        <h3>METAR - Current Observations</h3>
        <div className="product-controls">
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
          <h4>Raw METAR</h4>
          <div className="raw-text">{data.raw_text}</div>
        </div>
      ) : (
        <div className="parsed-data-container">
          {/* Observation Info */}
          <div className="info-section">
            <h4>Observation Details</h4>
            <div className="info-grid">
              <div className="info-item">
                <label>Station:</label>
                <span>{data.station_id}</span>
              </div>
              <div className="info-item">
                <label>Time:</label>
                <span>
                  {new Date(data.observation_time).toLocaleString()} 
                  ({formatDistanceToNow(parseISO(data.observation_time))} ago)
                </span>
              </div>
              <div className="info-item">
                <label>Category:</label>
                <span className={`category-badge category-${data.category.toLowerCase()}`}>
                  {data.category}
                </span>
              </div>
              <div className="info-item">
                <label>Flight Category:</label>
                <span>{data.flight_category || 'N/A'}</span>
              </div>
            </div>
          </div>

          {/* Weather Elements */}
          <div className="weather-elements">
            <div className="element-card">
              <h5>Wind</h5>
              <p>{getWindDescription()}</p>
            </div>

            <div className="element-card">
              <h5>Visibility</h5>
              <p>
                {data.visibility?.distance 
                  ? `${data.visibility.distance} ${data.visibility.unit}` 
                  : 'Not reported'
                }
              </p>
            </div>

            <div className="element-card">
              <h5>Clouds</h5>
              <p>{getCloudDescription()}</p>
            </div>

            <div className="element-card">
              <h5>Weather</h5>
              <p>{getWeatherDescription()}</p>
            </div>

            <div className="element-card">
              <h5>Temperature</h5>
              <p>
                {data.temperature !== null ? `${data.temperature}°C` : 'N/A'}
                {data.dewpoint !== null && ` / ${data.dewpoint}°C dew point`}
              </p>
            </div>

            <div className="element-card">
              <h5>Pressure</h5>
              <p>
                {data.altimeter 
                  ? `${data.altimeter} inHg` 
                  : 'Not reported'
                }
              </p>
            </div>
          </div>

          {/* Additional Information */}
          <div className="additional-info">
            <div className="flags">
              {data.auto && <span className="flag auto">AUTO</span>}
              {data.corrected && <span className="flag corrected">COR</span>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MetarView;
