import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
apiClient.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Response Error:', error);
    
    // Handle specific error cases
    if (error.response?.status === 404) {
      throw new Error(`Weather data not found for the requested station`);
    } else if (error.response?.status >= 500) {
      throw new Error(`Weather service temporarily unavailable. Please try again later.`);
    } else if (error.code === 'ECONNABORTED') {
      throw new Error(`Request timeout. Please check your connection and try again.`);
    } else if (!error.response) {
      throw new Error(`Unable to connect to weather service. Please check your connection.`);
    }
    
    throw error;
  }
);

export const weatherAPI = {
  // Get comprehensive weather briefing
  async getComprehensiveBriefing(stationId, radiusNm = 50) {
    try {
      const response = await apiClient.get(`/weather/comprehensive/${stationId}`, {
        params: { radius_nm: radiusNm }
      });
      return response.data;
    } catch (error) {
      console.error('Comprehensive briefing error:', error);
      throw error;
    }
  },

  // Get pilot-focused summary
  async getPilotSummary(stationId) {
    try {
      const response = await apiClient.get(`/weather/summary/${stationId}`);
      return response.data;
    } catch (error) {
      console.error('Pilot summary error:', error);
      throw error;
    }
  },

  // Get individual weather products
  async getMetar(stationId) {
    try {
      const response = await apiClient.get(`/weather/products/${stationId}/metar`);
      return response.data;
    } catch (error) {
      console.error('METAR error:', error);
      throw error;
    }
  },

  async getTaf(stationId) {
    try {
      const response = await apiClient.get(`/weather/products/${stationId}/taf`);
      return response.data;
    } catch (error) {
      console.error('TAF error:', error);
      throw error;
    }
  },

  async getPireps(stationId, radiusNm = 50) {
    try {
      const response = await apiClient.get(`/weather/products/${stationId}/pireps`, {
        params: { radius_nm: radiusNm }
      });
      return response.data;
    } catch (error) {
      console.error('PIREPs error:', error);
      throw error;
    }
  },

  async getSigmets(stationId, radiusNm = 100) {
    try {
      const response = await apiClient.get(`/weather/products/${stationId}/sigmets`, {
        params: { radius_nm: radiusNm }
      });
      return response.data;
    } catch (error) {
      console.error('SIGMETs error:', error);
      throw error;
    }
  },

  async getGAirmets(stationId, radiusNm = 100) {
    try {
      const response = await apiClient.get(`/weather/products/${stationId}/gairmets`, {
        params: { radius_nm: radiusNm }
      });
      return response.data;
    } catch (error) {
      console.error('G-AIRMETs error:', error);
      throw error;
    }
  },

  async getAirmets(stationId, radiusNm = 100) {
    try {
      const response = await apiClient.get(`/weather/products/${stationId}/airmets`, {
        params: { radius_nm: radiusNm }
      });
      return response.data;
    } catch (error) {
      console.error('AIRMETs error:', error);
      throw error;
    }
  },

  async getCwas(stationId, radiusNm = 100) {
    try {
      const response = await apiClient.get(`/weather/products/${stationId}/cwas`, {
        params: { radius_nm: radiusNm }
      });
      return response.data;
    } catch (error) {
      console.error('CWAs error:', error);
      throw error;
    }
  },

  // Get weather hazards
  async getWeatherHazards(stationId, radiusNm = 100) {
    try {
      const response = await apiClient.get(`/weather/hazards/${stationId}`, {
        params: { radius_nm: radiusNm }
      });
      return response.data;
    } catch (error) {
      console.error('Weather hazards error:', error);
      throw error;
    }
  },

  // Get raw weather data
  async getRawWeatherData(stationId, productType) {
    try {
      const response = await apiClient.get(`/weather/raw/${stationId}/${productType}`);
      return response.data;
    } catch (error) {
      console.error('Raw weather data error:', error);
      throw error;
    }
  },

  // Health check
  async healthCheck() {
    try {
      const response = await apiClient.get('/health');
      return response.data;
    } catch (error) {
      console.error('Health check error:', error);
      throw error;
    }
  }
};

export default weatherAPI;
