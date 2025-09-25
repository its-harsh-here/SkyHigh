import React, { useState } from 'react';
import ProductViews from './ProductViews';

const WeatherTabs = ({ weatherData }) => {
  const [activeTab, setActiveTab] = useState('metar');

  const tabs = [
    { id: 'metar', label: 'METAR', icon: '🌡️', data: weatherData.metar_data },
    { id: 'taf', label: 'TAF', icon: '📊', data: weatherData.taf_data },
    { id: 'pireps', label: 'PIREPs', icon: '✈️', data: weatherData.pirep_data, count: weatherData.pirep_data?.length },
    { id: 'hazards', label: 'Hazards', icon: '⚠️', data: weatherData.hazards, count: weatherData.hazards?.length, alert: weatherData.hazards?.length > 0 },
    { id: 'raw', label: 'Raw Data', icon: '📄', data: true }
  ];

  return (
    <div style={{ 
      background: 'white', 
      borderRadius: '10px', 
      boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
      overflow: 'hidden'
    }}>
      {/* Tab Navigation */}
      <div style={{ 
        display: 'flex', 
        borderBottom: '2px solid #f0f0f0',
        overflowX: 'auto'
      }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '1rem',
              border: 'none',
              background: activeTab === tab.id ? '#f8f9fa' : 'transparent',
              borderBottom: activeTab === tab.id ? '3px solid #007bff' : 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.9rem',
              fontWeight: activeTab === tab.id ? 'bold' : 'normal',
              opacity: (!tab.data || (Array.isArray(tab.data) && tab.data.length === 0)) ? 0.5 : 1,
              position: 'relative'
            }}
            disabled={!tab.data || (Array.isArray(tab.data) && tab.data.length === 0)}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
            {tab.count > 0 && (
              <span style={{ 
                background: tab.alert ? '#dc3545' : '#6c757d', 
                color: 'white', 
                borderRadius: '10px', 
                padding: '0.2rem 0.5rem', 
                fontSize: '0.7rem' 
              }}>
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div style={{ padding: '1.5rem' }}>
        <ProductViews 
          activeTab={activeTab} 
          weatherData={weatherData} 
        />
      </div>
    </div>
  );
};

export default WeatherTabs;
