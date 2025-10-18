import axios from 'axios';
import { DashboardResponse, HistoricalResponse } from '../types';

// Configure axios instance with base URL
const API = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:5001/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Error handler
const handleApiError = (error: any): never => {
  if (error.response) {
    // Server responded with error
    console.error('API Error:', error.response.data);
    throw new Error(error.response.data.message || 'API request failed');
  } else if (error.request) {
    // Request made but no response
    console.error('Network Error:', error.message);
    throw new Error('Network error - server may be down');
  } else {
    // Something else happened
    console.error('Error:', error.message);
    throw new Error('An unexpected error occurred');
  }
};

// API Methods
export const api = {
  // Get dashboard data
  getDashboard: async (): Promise<DashboardResponse> => {
    try {
      const response = await API.get<DashboardResponse>('/dashboard');
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },

  // Get historical data
  getHistorical: async (period: '1d' | '1w' | '1m' | 'all' = '1d'): Promise<HistoricalResponse> => {
    try {
      const response = await API.get<HistoricalResponse>(`/historical/${period}`);
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },

  // Health check
  getHealth: async (): Promise<boolean> => {
    try {
      const response = await API.get('/health');
      return response.status === 200;
    } catch (error) {
      console.error('Health check failed:', error);
      return false;
    }
  }
};

// Polling utility
export class PollingService {
  private intervalId: NodeJS.Timeout | null = null;
  
  start(callback: () => void, intervalMs: number = 5000): void {
    // Clear any existing interval
    this.stop();
    
    // Execute immediately
    callback();
    
    // Then poll at interval
    this.intervalId = setInterval(callback, intervalMs);
  }
  
  stop(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }
}
