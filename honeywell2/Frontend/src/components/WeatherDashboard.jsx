import React, { useState, useEffect } from 'react';
import { weatherAPI } from '../services/weatherAPI';
import WeatherSummary from './WeatherSummary';
import WeatherTabs from './WeatherTabs';

const WeatherDashboard = ({ station }) => {
  const [weatherData, setWeatherData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchWeatherData = async () => {
    if (!station) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const data = await weatherAPI.getComprehensiveBriefing(station);
      setWeatherData(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch weather data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWeatherData();
  }, [station]);

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>🔄</div>
        <p>Loading weather data for {station}...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#d32f2f' }}>
        <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>❌</div>
        <p>Error: {error}</p>
        <button onClick={fetchWeatherData} style={{ marginTop: '1rem', padding: '0.5rem 1rem' }}>
          Retry
        </button>
      </div>
    );
  }

  if (!weatherData) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>No weather data available</p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div style={{ 
        background: 'white', 
        borderRadius: '10px', 
        padding: '2rem',
        boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
        border: `3px solid ${getCategoryColor(weatherData.overall_category)}`
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h2>{station}</h2>
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', fontSize: '0.9rem', color: '#666' }}>
              <span className={`category-${weatherData.overall_category.toLowerCase()}`} style={{ 
                padding: '0.25rem 0.75rem', 
                borderRadius: '20px',
                fontWeight: 'bold'
              }}>
                {weatherData.overall_category}
              </span>
              <span>Confidence: {Math.round(weatherData.confidence_score * 100)}%</span>
              <span>Source: {weatherData.primary_source}</span>
            </div>
          </div>
          <button onClick={fetchWeatherData} style={{ padding: '0.5rem 1rem' }}>
            🔄 Refresh
          </button>
        </div>
      </div>

      <WeatherSummary weatherData={weatherData} />
      <WeatherTabs weatherData={weatherData} />
    </div>
  );
};

function getCategoryColor(category) {
  switch (category) {
    case 'SEVERE': return '#d32f2f';
    case 'SIGNIFICANT': return '#f57c00';
    case 'CLEAR': return '#388e3c';
    default: return '#666';
  }
}

export default WeatherDashboard;
