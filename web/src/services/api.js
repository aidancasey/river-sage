/**
 * River Guru API Service
 *
 * Provides methods to interact with the River Flow Data API
 */

import axios from 'axios';

// API base URL - will be set via environment variable for production
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://3su2ubk6j2.execute-api.eu-west-1.amazonaws.com/production';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

/**
 * Fetch the latest data from all stations
 * @returns {Promise<Object>} Latest data from all stations
 */
export async function getLatestData() {
  try {
    const response = await apiClient.get('/api/flow/latest');
    return response.data;
  } catch (error) {
    throw new Error(`Failed to fetch latest data: ${error.message}`);
  }
}

/**
 * Fetch the latest flow data for a specific station
 * @param {string} stationId - Station ID (default: 'inniscarra')
 * @returns {Promise<Object>} Latest flow data
 */
export async function getLatestFlow(stationId = 'inniscarra') {
  try {
    const response = await apiClient.get('/api/flow/latest', {
      params: { station: stationId },
    });

    // Extract the station from the response
    const station = response.data.stations?.[0];
    if (!station) {
      throw new Error('No data available for station');
    }

    // Transform API response to match component expectations
    return {
      name: station.name,
      river: station.river,
      currentFlow: station.flowRate,
      unit: station.unit,
      status: station.status,
      timestamp: station.timestamp,
      dataAge: station.dataAge,
    };
  } catch (error) {
    throw new Error(`Failed to fetch latest flow: ${error.message}`);
  }
}

/**
 * Fetch historical flow data for a station
 * @param {string} stationId - Station ID (default: 'inniscarra')
 * @param {Object} options - Query options
 * @param {number} options.hours - Number of hours to look back
 * @param {number} options.days - Number of days to look back (overrides hours)
 * @returns {Promise<Object>} Historical flow data with statistics
 */
export async function getHistoricalFlow(stationId = 'inniscarra', options = {}) {
  try {
    const params = { station: stationId };

    if (options.days) {
      params.days = options.days;
    } else if (options.hours) {
      params.hours = options.hours;
    } else {
      params.hours = 24; // Default to 24 hours
    }

    const response = await apiClient.get('/api/flow/history', { params });
    return response.data;
  } catch (error) {
    throw new Error(`Failed to fetch historical flow: ${error.message}`);
  }
}

/**
 * Get flow status color based on status string
 * @param {string} status - Flow status ('low', 'normal', 'high', 'very-high')
 * @returns {Object} Color configuration for the status
 */
export function getFlowStatusColor(status) {
  const colors = {
    low: {
      bg: 'bg-flow-low',
      text: 'text-flow-low',
      border: 'border-flow-low',
      label: 'Low Flow',
    },
    normal: {
      bg: 'bg-flow-normal',
      text: 'text-flow-normal',
      border: 'border-flow-normal',
      label: 'Normal Flow',
    },
    high: {
      bg: 'bg-flow-high',
      text: 'text-flow-high',
      border: 'border-flow-high',
      label: 'High Flow',
    },
    'very-high': {
      bg: 'bg-flow-very-high',
      text: 'text-flow-very-high',
      border: 'border-flow-very-high',
      label: 'Very High Flow',
    },
  };

  return colors[status] || colors.normal;
}

export default {
  getLatestData,
  getLatestFlow,
  getHistoricalFlow,
  getFlowStatusColor,
};
