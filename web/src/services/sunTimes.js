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
 * Get sun times for today and tomorrow with moon phase
 * @param {string} riverId - River identifier
 * @returns {Promise<Object>} Object with today and tomorrow sun times plus moon phase
 */
export async function getSunTimesTodayAndTomorrow(riverId) {
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);

  try {
    const [todayData, tomorrowData, moonPhase] = await Promise.all([
      getSunTimes(riverId, today),
      getSunTimes(riverId, tomorrow),
      getMoonPhase(today)
    ]);

    return {
      today: todayData,
      tomorrow: tomorrowData,
      moonPhase: moonPhase
    };
  } catch (error) {
    console.error('Failed to fetch sun times for today/tomorrow:', error);
    throw error;
  }
}

/**
 * Calculate moon phase for a given date
 * Uses astronomical calculations to determine current moon phase
 * @param {Date} date - Date to calculate moon phase for
 * @returns {Promise<Object>} Moon phase information
 */
export async function getMoonPhase(date = new Date()) {
  // Calculate moon phase using astronomical formula
  const year = date.getFullYear();
  const month = date.getMonth() + 1;
  const day = date.getDate();

  // Calculate Julian date
  let jd = 367 * year - Math.floor(7 * (year + Math.floor((month + 9) / 12)) / 4) +
           Math.floor(275 * month / 9) + day + 1721013.5;

  // Days since known new moon (January 6, 2000)
  const daysSinceNew = jd - 2451549.5;

  // Moon cycle is approximately 29.53 days
  const lunarCycle = 29.53058867;
  const phase = ((daysSinceNew % lunarCycle) / lunarCycle);

  // Calculate illumination percentage
  const illumination = (1 - Math.cos(phase * 2 * Math.PI)) / 2;

  return {
    phase: phase,
    illumination: illumination * 100,
    phaseName: getMoonPhaseName(phase),
    phaseIcon: getMoonPhaseIcon(phase),
    phaseDescription: getMoonPhaseDescription(phase)
  };
}

/**
 * Get moon phase name from phase value
 * @param {number} phase - Phase value (0-1)
 * @returns {string} Phase name
 */
function getMoonPhaseName(phase) {
  if (phase < 0.033 || phase > 0.967) return 'New Moon';
  if (phase < 0.216) return 'Waxing Crescent';
  if (phase < 0.283) return 'First Quarter';
  if (phase < 0.466) return 'Waxing Gibbous';
  if (phase < 0.533) return 'Full Moon';
  if (phase < 0.716) return 'Waning Gibbous';
  if (phase < 0.783) return 'Last Quarter';
  return 'Waning Crescent';
}

/**
 * Get moon phase icon emoji
 * @param {number} phase - Phase value (0-1)
 * @returns {string} Moon emoji
 */
function getMoonPhaseIcon(phase) {
  if (phase < 0.033 || phase > 0.967) return '🌑'; // New Moon
  if (phase < 0.216) return '🌒'; // Waxing Crescent
  if (phase < 0.283) return '🌓'; // First Quarter
  if (phase < 0.466) return '🌔'; // Waxing Gibbous
  if (phase < 0.533) return '🌕'; // Full Moon
  if (phase < 0.716) return '🌖'; // Waning Gibbous
  if (phase < 0.783) return '🌗'; // Last Quarter
  return '🌘'; // Waning Crescent
}

/**
 * Get moon phase description
 * @param {number} phase - Phase value (0-1)
 * @returns {string} Phase description
 */
function getMoonPhaseDescription(phase) {
  if (phase < 0.033 || phase > 0.967) return 'Dark night sky, best for stargazing';
  if (phase < 0.216) return 'Thin crescent visible after sunset';
  if (phase < 0.283) return 'Half moon visible in evening';
  if (phase < 0.466) return 'More than half illuminated, bright evening';
  if (phase < 0.533) return 'Fully illuminated, bright all night';
  if (phase < 0.716) return 'More than half illuminated, visible late night';
  if (phase < 0.783) return 'Half moon visible in morning';
  return 'Thin crescent visible before sunrise';
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
