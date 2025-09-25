import React, { useState, useEffect } from 'react';
import { weatherAPI } from '../services/weatherAPI';
import WeatherSummary from './WeatherSummary';
import WeatherTabs from './WeatherTabs';
import LoadingSpinner from './LoadingSpinner';
import ErrorBoundary from './ErrorBoundary';
import './WeatherDashboard.css';

const WeatherDashboard = ({ station }) => {
  const [weatherData, setWeatherData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('summary');
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Fetch comprehensive weather data
  const fetchWeatherData = async () => {
    if (!station) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const data = await weatherAPI.getComprehensiveBriefing(station);
      setWeatherData(data);
    } catch (err) {
      console.error('Weather fetch error:', err);
      setError(err.message || 'Failed to fetch weather data');
    } finally {
      setLoading(false);
    }
  };

  // Initial fetch and station change
  useEffect(() => {
    fetchWeatherData();
  }, [station]);

  // Auto-refresh every 5 minutes
  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(fetchWeatherData, 5 * 60 * 1000); // 5 minutes
    return () => clearInterval(interval);
  }, [autoRefresh, station]);

  const handleRefresh = () => {
    fetchWeatherData();
  };

  const getCategoryClass = (category) => {
    switch (category) {
      case 'SEVERE': return 'category-severe';
      case 'SIGNIFICANT': return 'category-significant';
      case 'CLEAR': return 'category-clear';
      default: return '';
    }
  };

  if (loading && !weatherData) {
    return <LoadingSpinner message="Fetching comprehensive weather data..." />;
  }

  if (error) {
    return (
      <div className="error-container">
        <h3>Weather Data Error</h3>
        <p>{error}</p>
        <button onClick={handleRefresh} className="retry-button">
          Retry
        </button>
      </div>
    );
  }

  if (!weatherData) {
    return (
      <div className="no-data-container">
        <p>No weather data available for {station}</p>
        <button onClick={handleRefresh} className="retry-button">
          Load Data
        </button>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div className="weather-dashboard">
        {/* Station Header */}
        <div className={`station-header ${getCategoryClass(weatherData.overall_category)}`}>
          <div className="station-info">
            <h2>{station}</h2>
            <div className="station-metadata">
              <span className="category-badge">
                {weatherData.overall_category}
              </span>
              <span className="confidence-score">
                Confidence: {(weatherData.confidence_score * 100).toFixed(0)}%
              </span>
              <span className="primary-source">
                Primary: {weatherData.primary_source}
              </span>
            </div>
          </div>
          
          <div className="header-controls">
            <button 
              onClick={handleRefresh}
              disabled={loading}
              className="refresh-button"
              title="Refresh data"
            >
              🔄 {loading ? 'Loading...' : 'Refresh'}
            </button>
            
            <label className="auto-refresh-toggle">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
              Auto-refresh
            </label>
          </div>
        </div>

        {/* Quick Summary */}
        <WeatherSummary weatherData={weatherData} />

        {/* Tabbed Weather Products */}
        <WeatherTabs
          weatherData={weatherData}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />
      </div>
    </ErrorBoundary>
  );
};

export default WeatherDashboard;
