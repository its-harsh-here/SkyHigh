import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

export const weatherAPI = {
  async getComprehensiveBriefing(stationId) {
    const response = await apiClient.get(`/weather/comprehensive/${stationId}`);
    return response.data;
  },

  async getPilotSummary(stationId) {
    const response = await apiClient.get(`/weather/summary/${stationId}`);
    return response.data;
  },

  async getMetar(stationId) {
    const response = await apiClient.get(`/weather/metar/${stationId}`);
    return response.data;
  },

  async getTaf(stationId) {
    const response = await apiClient.get(`/weather/taf/${stationId}`);
    return response.data;
  },

  async getPireps(stationId) {
    const response = await apiClient.get(`/weather/pireps/${stationId}`);
    return response.data;
  },

  async getHazards(stationId) {
    const response = await apiClient.get(`/weather/hazards/${stationId}`);
    return response.data;
  }
};
