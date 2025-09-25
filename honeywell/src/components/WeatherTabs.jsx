import React from 'react';
import MetarView from './weather-products/MetarView';
import TafView from './weather-products/TafView';
import PirepView from './weather-products/PirepView';
import HazardsView from './weather-products/HazardsView';
import RawDataView from './weather-products/RawDataView';
import './WeatherTabs.css';

const WeatherTabs = ({ weatherData, activeTab, onTabChange }) => {
  const tabs = [
    {
      id: 'summary',
      label: 'Smart Summary',
      icon: '🎯',
      count: null
    },
    {
      id: 'metar',
      label: 'METAR',
      icon: '🌡️',
      count: weatherData.metar_data ? 1 : 0,
      disabled: !weatherData.metar_data
    },
    {
      id: 'taf',
      label: 'TAF',
      icon: '📊',
      count: weatherData.taf_data ? 1 : 0,
      disabled: !weatherData.taf_data
    },
    {
      id: 'pireps',
      label: 'PIREPs',
      icon: '✈️',
      count: weatherData.pirep_data?.length || 0,
      disabled: !weatherData.pirep_data?.length
    },
    {
      id: 'hazards',
      label: 'Hazards',
      icon: '⚠️',
      count: weatherData.hazards?.length || 0,
      alert: weatherData.hazards?.length > 0
    },
    {
      id: 'raw',
      label: 'Raw Data',
      icon: '📄',
      count: null
    }
  ];

  const renderTabContent = () => {
    switch (activeTab) {
      case 'summary':
        return (
          <div className="summary-tab-content">
            <p>Smart summary is displayed above. Select other tabs to view detailed weather products.</p>
            <div className="available-products">
              <h4>Available Products:</h4>
              <ul>
                {weatherData.available_products.map(product => (
                  <li key={product}>✅ {product}</li>
                ))}
              </ul>
            </div>
          </div>
        );
        
      case 'metar':
        return <MetarView data={weatherData.metar_data} />;
        
      case 'taf':
        return <TafView data={weatherData.taf_data} />;
        
      case 'pireps':
        return <PirepView data={weatherData.pirep_data} />;
        
      case 'hazards':
        return (
          <HazardsView
            hazards={weatherData.hazards}
            sigmets={weatherData.sigmet_data}
            gairmets={weatherData.gairmet_data}
            airmets={weatherData.airmet_data}
            cwas={weatherData.cwa_data}
          />
        );
        
      case 'raw':
        return <RawDataView weatherData={weatherData} />;
        
      default:
        return <div>Select a tab to view weather data</div>;
    }
  };

  return (
    <div className="weather-tabs">
      {/* Tab Navigation */}
      <div className="tab-nav">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`tab-button ${activeTab === tab.id ? 'active' : ''} ${tab.disabled ? 'disabled' : ''} ${tab.alert ? 'alert' : ''}`}
            disabled={tab.disabled}
          >
            <span className="tab-icon">{tab.icon}</span>
            <span className="tab-label">{tab.label}</span>
            {tab.count !== null && (
              <span className="tab-count">({tab.count})</span>
            )}
            {tab.alert && <span className="alert-dot"></span>}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {renderTabContent()}
      </div>
    </div>
  );
};

export default WeatherTabs;
