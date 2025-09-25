import React from 'react';
import { formatDistanceToNow } from 'date-fns';

const WeatherSummary = ({ weatherData }) => {
  return (
    <div style={{ 
      background: 'white', 
      borderRadius: '10px', 
      padding: '1.5rem',
      boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
    }}>
      <h3>📊 Weather Summary</h3>
      
      <div style={{ 
        background: '#f5f5f5', 
        padding: '1rem', 
        borderRadius: '8px', 
        marginBottom: '1rem',
        fontSize: '1.1rem'
      }}>
        {weatherData.pilot_summary}
      </div>

      {weatherData.recommendations.length > 0 && (
        <div style={{ marginBottom: '1rem' }}>
          <h4>💡 Recommendations</h4>
          <ul style={{ textAlign: 'left', paddingLeft: '1rem' }}>
            {weatherData.recommendations.map((rec, index) => (
              <li key={index} style={{ marginBottom: '0.5rem' }}>{rec}</li>
            ))}
          </ul>
        </div>
      )}

      {weatherData.hazards.length > 0 && (
        <div style={{ background: '#fff3cd', padding: '1rem', borderRadius: '8px', border: '1px solid #ffc107' }}>
          <h4 style={{ color: '#856404', margin: '0 0 1rem 0' }}>⚠️ Active Hazards ({weatherData.hazards.length})</h4>
          {weatherData.hazards.slice(0, 3).map((hazard, index) => (
            <div key={index} style={{ marginBottom: '0.5rem', fontSize: '0.9rem' }}>
              <strong>{hazard.type}:</strong> {hazard.phenomenon || hazard.hazard}
            </div>
          ))}
          {weatherData.hazards.length > 3 && (
            <p style={{ fontSize: '0.8rem', margin: 0 }}>
              +{weatherData.hazards.length - 3} more hazards
            </p>
          )}
        </div>
      )}

      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        fontSize: '0.8rem', 
        color: '#666',
        marginTop: '1rem'
      }}>
        <span>Updated: {formatDistanceToNow(new Date(weatherData.generated_at))} ago</span>
        <span>Products: {weatherData.available_products.length}</span>
      </div>
    </div>
  );
};

export default WeatherSummary;
