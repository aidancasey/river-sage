<template>
  <div class="card">
    <div class="mb-6">
      <h3 class="text-xl font-bold text-gray-800 mb-2 text-center">Weather Forecast</h3>
      <p class="text-sm text-gray-600 text-center">{{ locationName }}</p>
    </div>

    <!-- Loading State with Skeleton -->
    <div v-if="loading" class="animate-fade-in">
      <div class="space-y-4">
        <!-- Current weather skeleton -->
        <div class="bg-blue-50 rounded-lg p-6">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-4">
              <div class="h-16 w-16 bg-gray-200 rounded-full animate-pulse"></div>
              <div>
                <div class="h-8 bg-gray-200 rounded w-24 animate-pulse mb-2"></div>
                <div class="h-4 bg-gray-200 rounded w-32 animate-pulse"></div>
              </div>
            </div>
            <div class="text-right">
              <div class="h-4 bg-gray-200 rounded w-20 animate-pulse mb-2"></div>
              <div class="h-4 bg-gray-200 rounded w-24 animate-pulse"></div>
            </div>
          </div>
        </div>

        <!-- Daily forecast skeleton -->
        <div class="grid grid-cols-3 md:grid-cols-7 gap-2">
          <div v-for="i in 7" :key="i" class="bg-gray-50 rounded-lg p-3">
            <div class="h-4 bg-gray-200 rounded w-12 mx-auto animate-pulse mb-2"></div>
            <div class="h-8 bg-gray-200 rounded w-8 mx-auto animate-pulse mb-2"></div>
            <div class="h-4 bg-gray-200 rounded w-16 mx-auto animate-pulse"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="text-center py-8 animate-fade-in">
      <div class="text-red-500 text-4xl mb-4">⚠️</div>
      <h4 class="text-lg font-semibold text-red-600 mb-2">Error Loading Weather</h4>
      <p class="text-gray-600 mb-4">{{ error }}</p>
      <button @click="fetchData" class="btn btn-primary">
        Try Again
      </button>
    </div>

    <!-- Data Display -->
    <div v-else-if="weatherData" class="animate-fade-in">
      <!-- Current Weather -->
      <div class="bg-blue-50 rounded-lg p-6 mb-6">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-4">
            <div class="text-5xl">{{ weatherData.current.weatherIcon }}</div>
            <div>
              <div class="text-4xl font-bold text-gray-800">
                {{ weatherData.current.temperature.toFixed(1) }}°C
              </div>
              <div class="text-sm text-gray-600">
                {{ weatherData.current.weatherDescription }}
              </div>
            </div>
          </div>
          <div class="text-right text-sm">
            <div class="flex items-center gap-2 mb-1">
              <span>💧</span>
              <span class="text-gray-700">{{ weatherData.current.precipitationProbability }}%</span>
            </div>
            <div class="flex items-center gap-2">
              <span>💨</span>
              <span class="text-gray-700">{{ weatherData.current.windSpeed.toFixed(0) }} km/h</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 7-Day Forecast -->
      <div>
        <h4 class="text-sm font-semibold text-gray-700 mb-3">7-Day Forecast</h4>
        <div class="grid grid-cols-3 md:grid-cols-7 gap-2">
          <div
            v-for="(day, index) in weatherData.daily"
            :key="index"
            class="bg-gray-50 rounded-lg p-3 text-center hover:bg-gray-100 transition-colors"
          >
            <div class="text-xs font-medium text-gray-600 mb-1">
              {{ index === 0 ? 'Today' : day.dayOfWeek }}
            </div>
            <div class="text-3xl my-2">{{ day.weatherIcon }}</div>
            <div class="text-sm font-bold text-gray-800 mb-1">
              {{ day.temperatureMax.toFixed(0) }}°
            </div>
            <div class="text-xs text-gray-500 mb-2">
              {{ day.temperatureMin.toFixed(0) }}°
            </div>
            <div class="flex items-center justify-center gap-1 text-xs text-blue-600">
              <span>💧</span>
              <span>{{ day.precipitationProbability }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Additional Details -->
      <div class="mt-6 pt-6 border-t border-gray-200">
        <div class="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p class="text-gray-500 mb-1">Today's Rainfall</p>
            <p class="font-medium text-gray-800">
              {{ weatherData.daily[0].precipitationSum.toFixed(1) }} mm
            </p>
          </div>
          <div>
            <p class="text-gray-500 mb-1">Rain Probability</p>
            <p class="font-medium text-gray-800">
              {{ weatherData.daily[0].precipitationProbability }}%
            </p>
          </div>
        </div>
      </div>

      <!-- Data Source Attribution -->
      <div class="mt-4 pt-4 border-t border-gray-200 text-center">
        <p class="text-xs text-gray-400">
          Weather data from <a href="https://open-meteo.com/" target="_blank" class="text-blue-500 hover:underline">Open-Meteo</a>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { getWeatherForecast } from '../services/weather';
import { useAutoRefresh } from '../composables/useAutoRefresh';

// Props
const props = defineProps({
  riverId: {
    type: String,
    required: true,
  },
});

// Reactive state
const weatherData = ref(null);
const loading = ref(true);
const error = ref(null);

// Computed properties
const locationName = computed(() => {
  if (!weatherData.value) return '';
  return weatherData.value.location || '';
});

// Methods
async function fetchData() {
  try {
    loading.value = true;
    error.value = null;

    weatherData.value = await getWeatherForecast(props.riverId);
  } catch (err) {
    error.value = err.message;
    console.error('Failed to fetch weather forecast:', err);
  } finally {
    loading.value = false;
  }
}

// Watch for river changes
watch(() => props.riverId, () => {
  fetchData();
});

// Auto-refresh every hour
const { lastRefreshTime } = useAutoRefresh(fetchData, 60 * 60 * 1000);

// Lifecycle hooks
onMounted(() => {
  fetchData();
});
</script>

<style scoped>
/* Component-specific styles can go here if needed */
</style>
