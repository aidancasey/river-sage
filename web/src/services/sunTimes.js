/**
 * Service for fetching sunrise/sunset times from sunrise-sunset.org API
 * API is free and doesn't require authentication
 */

// River coordinates
const RIVER_COORDINATES = {
  lee: { lat: 51.9127, lng: -8.5707, location: 'Anglers Rest' },
  blackwater: { lat: 52.1187, lng: -8.7805, location: 'Lombardstown' },
  suir: { lat: 52.5000, lng: -7.9833, location: 'Golden' },
  bandon: { lat: 51.7461, lng: -8.7318, location: 'Bandon Town' },
  owenboy: { lat: 51.8179, lng: -8.3915, location: 'Carrigaline' }
};

/**
 * Fetch sun times for a specific date and river
 * @param {string} riverId - River identifier (lee, blackwater, etc.)
 * @param {Date} date - Date to fetch sun times for
 * @returns {Promise<Object>} Sun times data
 */
export async function getSunTimes(riverId, date = new Date()) {
  const coords = RIVER_COORDINATES[riverId];

  if (!coords) {
    throw new Error(`Unknown river: ${riverId}`);
  }

  // Format date as YYYY-MM-DD
  const dateStr = date.toISOString().split('T')[0];

  const url = `https://api.sunrise-sunset.org/json?lat=${coords.lat}&lng=${coords.lng}&date=${dateStr}&formatted=0`;

  try {
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json();

    if (data.status !== 'OK') {
      throw new Error('API returned error status');
    }

    // Convert UTC times to local Irish time
    const results = data.results;

    return {
      sunrise: formatTimeLocal(results.sunrise),
      sunset: formatTimeLocal(results.sunset),
      dawn: formatTimeLocal(results.civil_twilight_begin),
      dusk: formatTimeLocal(results.civil_twilight_end),
      dayLength: formatDuration(results.day_length),
      location: coords.location,
      date: dateStr
    };
  } catch (error) {
    console.error('Failed to fetch sun times:', error);
    throw error;
  }
}

/**
 * Get sun times for today and tomorrow
 * @param {string} riverId - River identifier
 * @returns {Promise<Object>} Object with today and tomorrow sun times
 */
export async function getSunTimesTodayAndTomorrow(riverId) {
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);

  try {
    const [todayData, tomorrowData] = await Promise.all([
      getSunTimes(riverId, today),
      getSunTimes(riverId, tomorrow)
    ]);

    return {
      today: todayData,
      tomorrow: tomorrowData
    };
  } catch (error) {
    console.error('Failed to fetch sun times for today/tomorrow:', error);
    throw error;
  }
}

/**
 * Convert UTC time string to local time string (HH:MM format)
 * @param {string} utcTimeStr - ISO 8601 time string
 * @returns {string} Local time in HH:MM format
 */
function formatTimeLocal(utcTimeStr) {
  const date = new Date(utcTimeStr);
  return date.toLocaleTimeString('en-IE', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'Europe/Dublin'
  });
}

/**
 * Format duration in seconds to readable format
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted duration (e.g., "14h 32m")
 */
function formatDuration(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}

/**
 * Get the river coordinates for display
 * @param {string} riverId - River identifier
 * @returns {Object} Coordinates and location
 */
export function getRiverLocation(riverId) {
  return RIVER_COORDINATES[riverId];
}
