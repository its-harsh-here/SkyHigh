import React, { useState } from 'react';
import { formatDistanceToNow, parseISO, format } from 'date-fns';
import './WeatherProductViews.css';

const HazardsView = ({ hazards, sigmets, gairmets, airmets, cwas }) => {
  const [activeHazardType, setActiveHazardType] = useState('all');
  const [showExpired, setShowExpired] = useState(false);

  const allHazardProducts = [
    ...sigmets.map(s => ({ ...s, product_type: 'SIGMET' })),
    ...gairmets.map(g => ({ ...g, product_type: 'G-AIRMET' })),
    ...airmets.map(a => ({ ...a, product_type: 'AIRMET' })),
    ...cwas.map(c => ({ ...c, product_type: 'CWA' }))
  ];

  const now = new Date();
  const activeHazardProducts = allHazardProducts.filter(h => 
    showExpired || new Date(h.valid_until) > now
  );

  const filteredHazards = activeHazardType === 'all' 
    ? activeHazardProducts
    : activeHazardProducts.filter(h => h.product_type === activeHazardType);

  const getHazardIcon = (productType, phenomenon) => {
    if (productType === 'SIGMET') {
      if (phenomenon?.includes('TS')) return '⛈️';
      if (phenomenon?.includes('ICE')) return '🧊';
      if (phenomenon?.includes('TURB')) return '💨';
      return '⚠️';
    }
    
    switch (productType) {
      case 'G-AIRMET': return '🟨';
      case 'AIRMET': return '🟧';
      case 'CWA': return '🔵';
      default: return '⚪';
    }
  };

  const getSeverityClass = (productType) => {
    switch (productType) {
      case 'SIGMET': return 'severity-severe';
      case 'G-AIRMET': return 'severity-significant';
      case 'AIRMET': return 'severity-significant';
      case 'CWA': return 'severity-advisory';
      default: return '';
    }
  };

  const getTimeStatus = (validUntil) => {
    const timeLeft = new Date(validUntil) - now;
    const hoursLeft = timeLeft / (1000 * 60 * 60);
    
    if (hoursLeft < 0) return { text: 'EXPIRED', class: 'expired' };
    if (hoursLeft < 1) return { text: 'EXPIRING SOON', class: 'expiring' };
    if (hoursLeft < 6) return { text: 'ACTIVE', class: 'active' };
    return { text: 'VALID', class: 'valid' };
  };

  const hazardTypeCounts = {
    all: allHazardProducts.length,
    SIGMET: sigmets.length,
    'G-AIRMET': gairmets.length,
    AIRMET: airmets.length,
    CWA: cwas.length
  };

  if (allHazardProducts.length === 0) {
    return (
      <div className="no-data">
        <div className="good-news">
          <h3>🟢 No Active Weather Hazards</h3>
          <p>No SIGMETs, AIRMETs, G-AIRMETs, or Center Weather Advisories are currently active for this area.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="weather-product-view hazards-view">
      <div className="product-header">
        <h3>Weather Hazards ({allHazardProducts.length} total)</h3>
        <div className="product-controls">
          <label className="show-expired-toggle">
            <input
              type="checkbox"
              checked={showExpired}
              onChange={(e) => setShowExpired(e.target.checked)}
            />
            Show Expired
          </label>
        </div>
      </div>

      {/* Hazard Type Filters */}
      <div className="hazard-type-filters">
        {['all', 'SIGMET', 'G-AIRMET', 'AIRMET', 'CWA'].map(type => (
          <button
            key={type}
            onClick={() => setActiveHazardType(type)}
            className={`filter-button ${activeHazardType === type ? 'active' : ''} ${
              hazardTypeCounts[type] === 0 ? 'disabled' : ''
            }`}
            disabled={hazardTypeCounts[type] === 0}
          >
            {type === 'all' ? 'All Hazards' : type}
            <span className="count">({hazardTypeCounts[type]})</span>
          </button>
        ))}
      </div>

      {/* Quick Hazard Summary */}
      {hazards.length > 0 && (
        <div className="hazards-summary">
          <h4>Critical Summary</h4>
          <div className="summary-hazards">
            {hazards.slice(0, 5).map((hazard, index) => (
              <div key={index} className={`summary-hazard ${getSeverityClass(hazard.type)}`}>
                <span className="hazard-icon">
                  {getHazardIcon(hazard.type, hazard.phenomenon || hazard.hazard)}
                </span>
                <div className="hazard-info">
                  <strong>{hazard.type}</strong>
                  <span>{hazard.phenomenon || hazard.hazard}</span>
                  {hazard.valid_until && (
                    <small>Until {format(new Date(hazard.valid_until), 'HH:mm MMM dd')}</small>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Detailed Hazard List */}
      <div className="hazards-list">
        {filteredHazards.length === 0 ? (
          <div className="no-hazards-filtered">
            <p>No {activeHazardType === 'all' ? '' : activeHazardType} hazards {showExpired ? '' : 'currently active'}</p>
          </div>
        ) : (
          filteredHazards.map((hazard, index) => {
            const timeStatus = getTimeStatus(hazard.valid_until);
            
            return (
              <div key={index} className={`hazard-card ${getSeverityClass(hazard.product_type)} ${timeStatus.class}`}>
                <div className="hazard-header">
                  <div className="hazard-type-info">
                    {getHazardIcon(hazard.product_type, hazard.phenomenon || hazard.hazard_type)}
                    <strong>{hazard.product_type}</strong>
                    <span className="hazard-id">{hazard.identifier}</span>
                  </div>
                  <div className="time-info">
                    <span className={`time-status ${timeStatus.class}`}>
                      {timeStatus.text}
                    </span>
                  </div>
                </div>

                <div className="hazard-details">
                  <div className="hazard-phenomenon">
                    <h5>Hazard Type</h5>
                    <p>{hazard.phenomenon || hazard.hazard_type || 'Not specified'}</p>
                    {hazard.severity && (
                      <p className="severity">Severity: {hazard.severity}</p>
                    )}
                  </div>

                  <div className="hazard-timing">
                    <div className="timing-item">
                      <label>Issued:</label>
                      <span>{format(new Date(hazard.issue_time), 'HH:mm MMM dd, yyyy')}</span>
                    </div>
                    <div className="timing-item">
                      <label>Valid From:</label>
                      <span>{format(new Date(hazard.valid_from), 'HH:mm MMM dd')}</span>
                    </div>
                    <div className="timing-item">
                      <label>Valid Until:</label>
                      <span>{format(new Date(hazard.valid_until), 'HH:mm MMM dd')}</span>
                    </div>
                  </div>

                  {/* Product-specific details */}
                  {hazard.product_type === 'G-AIRMET' && (
                    <div className="altitude-info">
                      <label>Altitude:</label>
                      <span>
                        {hazard.base_altitude || 'SFC'} - {hazard.top_altitude || 'TOP'}
                      </span>
                    </div>
                  )}

                  {hazard.product_type === 'AIRMET' && hazard.series && (
                    <div className="airmet-series">
                      <label>Series:</label>
                      <span>{hazard.series}</span>
                    </div>
                  )}

                  {hazard.product_type === 'CWA' && hazard.center && (
                    <div className="cwa-center">
                      <label>Center:</label>
                      <span>{hazard.center}</span>
                    </div>
                  )}

                  {hazard.movement && (
                    <div className="movement-info">
                      <label>Movement:</label>
                      <span>{hazard.movement}</span>
                    </div>
                  )}

                  {hazard.area_description && (
                    <div className="area-info">
                      <label>Area:</label>
                      <span>{hazard.area_description}</span>
                    </div>
                  )}
                </div>

                {/* Raw Text */}
                <details className="hazard-raw-toggle">
                  <summary>View Raw {hazard.product_type}</summary>
                  <div className="raw-text">{hazard.raw_text}</div>
                </details>
              </div>
            );
          })
        )}
      </div>

      {/* Hazard Statistics */}
      <div className="hazard-stats">
        <h4>Hazard Statistics</h4>
        <div className="stats-grid">
          <div className="stat-item">
            <label>Active Hazards:</label>
            <span>{allHazardProducts.filter(h => new Date(h.valid_until) > now).length}</span>
          </div>
          <div className="stat-item">
            <label>SIGMETs (Severe):</label>
            <span>{sigmets.length}</span>
          </div>
          <div className="stat-item">
            <label>G-AIRMETs:</label>
            <span>{gairmets.length}</span>
          </div>
          <div className="stat-item">
            <label>AIRMETs:</label>
            <span>{airmets.length}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HazardsView;
