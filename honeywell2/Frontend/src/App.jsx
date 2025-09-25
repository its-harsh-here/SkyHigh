import React, { useState } from 'react';
import WeatherDashboard from './components/WeatherDashboard';
import './App.css';  // Make sure this matches the file name exactly

function App() {
  const [selectedStation, setSelectedStation] = useState('KJFK');

  return (
    <div className="App">
      <header className="app-header">
        <h1>🛩️ Aviation Weather Briefing System</h1>
        <div className="station-selector">
          <input
            type="text"
            value={selectedStation}
            onChange={(e) => setSelectedStation(e.target.value.toUpperCase())}
            placeholder="Enter station (e.g., KJFK)"
            maxLength={4}
          />
          <button onClick={() => setSelectedStation(selectedStation)}>
            Get Weather
          </button>
        </div>
      </header>
      
      <main className="app-main">
        <WeatherDashboard station={selectedStation} />
      </main>
    </div>
  );
}

export default App;
