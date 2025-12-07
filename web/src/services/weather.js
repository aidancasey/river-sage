/**
 * Service for fetching weather forecast data from Open-Meteo API
 * API is free and doesn't require authentication
 * https://open-meteo.com/
 */

// River coordinates (reusing from sunTimes)
const RIVER_COORDINATES = {
  lee: { lat: 51.9127, lng: -8.5707, location: 'Anglers Rest' },
  blackwater: { lat: 52.1187, lng: -8.7805, location: 'Lombardstown' },
  suir: { lat: 52.5000, lng: -7.9833, location: 'Golden' },
  bandon: { lat: 51.7461, lng: -8.7318, location: 'Bandon Town' },
  owenboy: { lat: 51.8179, lng: -8.3915, location: 'Carrigaline' }
};

/**
 * Fetch weather forecast for a specific river location
 * @param {string} riverId - River identifier (lee, blackwater, etc.)
 * @returns {Promise<Object>} Weather forecast data
 */
export async function getWeatherForecast(riverId) {
  const coords = RIVER_COORDINATES[riverId];

  if (!coords) {
    throw new Error(`Unknown river: ${riverId}`);
  }

  // Open-Meteo API endpoint for hourly forecast
  // timezone=auto ensures times are in local timezone
  const url = `https://api.open-meteo.com/v1/forecast?latitude=${coords.lat}&longitude=${coords.lng}&hourly=temperature_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,weather_code&timezone=auto&forecast_days=7`;

  try {
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json();

    return {
      location: coords.location,
      latitude: data.latitude,
      longitude: data.longitude,
      timezone: data.timezone,
      current: getCurrentWeather(data),
      hourly: formatHourlyForecast(data.hourly),
      daily: formatDailyForecast(data.daily)
    };
  } catch (error) {
    console.error('Failed to fetch weather forecast:', error);
    throw error;
  }
}

/**
 * Get current weather conditions (most recent hour)
 * @param {Object} data - API response data
 * @returns {Object} Current weather
 */
function getCurrentWeather(data) {
  const hourly = data.hourly;
  const currentIndex = 0; // First entry is current/most recent

  return {
    time: hourly.time[currentIndex],
    temperature: hourly.temperature_2m[currentIndex],
    precipitationProbability: hourly.precipitation_probability[currentIndex],
    precipitation: hourly.precipitation[currentIndex],
    weatherCode: hourly.weather_code[currentIndex],
    weatherDescription: getWeatherDescription(hourly.weather_code[currentIndex]),
    weatherIcon: getWeatherIcon(hourly.weather_code[currentIndex]),
    windSpeed: hourly.wind_speed_10m[currentIndex]
  };
}

/**
 * Format hourly forecast data (next 24 hours)
 * @param {Object} hourly - Hourly data from API
 * @returns {Array} Formatted hourly forecast
 */
function formatHourlyForecast(hourly) {
  const forecast = [];
  const hoursToShow = 24;

  for (let i = 0; i < Math.min(hoursToShow, hourly.time.length); i++) {
    forecast.push({
      time: hourly.time[i],
      hour: new Date(hourly.time[i]).getHours(),
      temperature: hourly.temperature_2m[i],
      precipitationProbability: hourly.precipitation_probability[i],
      precipitation: hourly.precipitation[i],
      weatherCode: hourly.weather_code[i],
      weatherIcon: getWeatherIcon(hourly.weather_code[i]),
      windSpeed: hourly.wind_speed_10m[i]
    });
  }

  return forecast;
}

/**
 * Format daily forecast data
 * @param {Object} daily - Daily data from API
 * @returns {Array} Formatted daily forecast
 */
function formatDailyForecast(daily) {
  const forecast = [];

  for (let i = 0; i < daily.time.length; i++) {
    const date = new Date(daily.time[i]);

    forecast.push({
      date: daily.time[i],
      dayOfWeek: date.toLocaleDateString('en-IE', { weekday: 'short' }),
      dayOfMonth: date.getDate(),
      temperatureMax: daily.temperature_2m_max[i],
      temperatureMin: daily.temperature_2m_min[i],
      precipitationSum: daily.precipitation_sum[i],
      precipitationProbability: daily.precipitation_probability_max[i],
      weatherCode: daily.weather_code[i],
      weatherDescription: getWeatherDescription(daily.weather_code[i]),
      weatherIcon: getWeatherIcon(daily.weather_code[i])
    });
  }

  return forecast;
}

/**
 * Get weather description from WMO weather code
 * @param {number} code - WMO weather code
 * @returns {string} Weather description
 */
function getWeatherDescription(code) {
  const descriptions = {
    0: 'Clear sky',
    1: 'Mainly clear',
    2: 'Partly cloudy',
    3: 'Overcast',
    45: 'Foggy',
    48: 'Foggy',
    51: 'Light drizzle',
    53: 'Moderate drizzle',
    55: 'Dense drizzle',
    61: 'Slight rain',
    63: 'Moderate rain',
    65: 'Heavy rain',
    71: 'Slight snow',
    73: 'Moderate snow',
    75: 'Heavy snow',
    77: 'Snow grains',
    80: 'Slight rain showers',
    81: 'Moderate rain showers',
    82: 'Violent rain showers',
    85: 'Slight snow showers',
    86: 'Heavy snow showers',
    95: 'Thunderstorm',
    96: 'Thunderstorm with hail',
    99: 'Thunderstorm with hail'
  };

  return descriptions[code] || 'Unknown';
}

/**
 * Get weather icon emoji from WMO weather code
 * @param {number} code - WMO weather code
 * @returns {string} Weather icon emoji
 */
function getWeatherIcon(code) {
  if (code === 0) return '☀️';
  if (code === 1) return '🌤️';
  if (code === 2) return '⛅';
  if (code === 3) return '☁️';
  if (code === 45 || code === 48) return '🌫️';
  if (code >= 51 && code <= 55) return '🌦️';
  if (code >= 61 && code <= 65) return '🌧️';
  if (code >= 71 && code <= 77) return '❄️';
  if (code >= 80 && code <= 82) return '🌧️';
  if (code >= 85 && code <= 86) return '🌨️';
  if (code >= 95 && code <= 99) return '⛈️';
  return '🌤️';
}

/**
 * Get the river coordinates for display
 * @param {string} riverId - River identifier
 * @returns {Object} Coordinates and location
 */
export function getRiverLocation(riverId) {
  return RIVER_COORDINATES[riverId];
}
