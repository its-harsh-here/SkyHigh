import React, { useState, useEffect } from 'react';
import WeatherDashboard from './components/WeatherDashboard';
import StationSearch from './components/StationSearch';
import './App.css';

function App() {
  const [selectedStation, setSelectedStation] = useState('KJFK');
  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    // Load user preferences
    const savedStation = localStorage.getItem('selectedStation');
    const savedDarkMode = localStorage.getItem('darkMode') === 'true';
    
    if (savedStation) setSelectedStation(savedStation);
    setDarkMode(savedDarkMode);
  }, []);

  const handleStationChange = (station) => {
    setSelectedStation(station);
    localStorage.setItem('selectedStation', station);
  };

  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    localStorage.setItem('darkMode', newDarkMode);
  };

  return (
    <div className={`App ${darkMode ? 'dark-mode' : ''}`}>
      <header className="app-header">
        <div className="header-content">
          <h1>Aviation Weather Briefing System</h1>
          <div className="header-controls">
            <StationSearch 
              onStationSelect={handleStationChange}
              currentStation={selectedStation}
            />
            <button 
              onClick={toggleDarkMode}
              className="theme-toggle"
              title="Toggle dark mode"
            >
              {darkMode ? '☀️' : '🌙'}
            </button>
          </div>
        </div>
      </header>

      <main className="app-main">
        <WeatherDashboard station={selectedStation} />
      </main>

      <footer className="app-footer">
        <p>
          Aviation Weather Data provided by aviationweather.gov | 
          Last updated: {new Date().toLocaleString()}
        </p>
      </footer>
    </div>
  );
}

export default App;
