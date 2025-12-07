<template>
  <div class="card relative">
    <!-- Refresh indicator -->
    <div
      v-if="isRefreshing"
      class="absolute top-4 right-4 flex items-center gap-2 text-sm text-blue-600 animate-fade-in"
    >
      <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
      <span>Updating...</span>
    </div>

    <!-- Loading State with Skeleton -->
    <div v-if="loading" class="animate-fade-in">
      <div class="text-center py-8 space-y-4">
        <!-- Station name skeleton -->
        <div class="h-8 bg-gray-200 rounded w-48 mx-auto animate-pulse"></div>
        <div class="h-4 bg-gray-200 rounded w-32 mx-auto animate-pulse"></div>

        <!-- Water level and temp grid skeleton -->
        <div class="grid grid-cols-2 gap-6 mt-6">
          <div class="bg-gray-100 rounded-lg p-6">
            <div class="h-4 bg-gray-200 rounded w-24 mx-auto animate-pulse mb-4"></div>
            <div class="h-16 bg-gray-200 rounded w-32 mx-auto animate-pulse"></div>
            <div class="h-4 bg-gray-200 rounded w-16 mx-auto animate-pulse mt-2"></div>
          </div>
          <div class="bg-gray-100 rounded-lg p-6">
            <div class="h-4 bg-gray-200 rounded w-24 mx-auto animate-pulse mb-4"></div>
            <div class="h-16 bg-gray-200 rounded w-32 mx-auto animate-pulse"></div>
            <div class="h-4 bg-gray-200 rounded w-16 mx-auto animate-pulse mt-2"></div>
          </div>
        </div>

        <!-- Timestamp skeleton -->
        <div class="pt-6 border-t border-gray-200 mt-6">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <div class="h-4 bg-gray-200 rounded w-24 mx-auto animate-pulse mb-2"></div>
              <div class="h-5 bg-gray-200 rounded w-32 mx-auto animate-pulse"></div>
            </div>
            <div>
              <div class="h-4 bg-gray-200 rounded w-24 mx-auto animate-pulse mb-2"></div>
              <div class="h-5 bg-gray-200 rounded w-32 mx-auto animate-pulse"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="text-center py-8 animate-fade-in">
      <div class="text-red-500 text-5xl mb-4">⚠️</div>
      <h3 class="text-xl font-semibold text-red-600 mb-2">Error Loading Data</h3>
      <p class="text-gray-600 mb-4">{{ error }}</p>
      <button @click="fetchData" class="btn btn-primary">
        Try Again
      </button>
    </div>

    <!-- Data Display -->
    <div v-else-if="levelData" class="text-center animate-fade-in">
      <!-- Station Info -->
      <div class="mb-6">
        <div class="flex items-center justify-between mb-2">
          <div class="flex-1"></div>
          <h2 class="text-2xl font-bold text-gray-800 flex-1">{{ levelData.name }}</h2>
          <div class="flex-1 flex justify-end">
            <button
              @click="fetchData"
              class="p-2 hover:bg-gray-100 rounded-full transition-colors"
              title="Refresh data"
            >
              <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>
        <p class="text-gray-600">{{ levelData.river }}</p>
      </div>

      <!-- Water Level and Temperature Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <!-- Water Level -->
        <div class="bg-blue-50 rounded-lg p-6">
          <p class="text-sm text-blue-600 font-semibold mb-2">Water Level</p>
          <div class="text-5xl font-bold text-blue-600 mb-2">
            {{ formatValue(levelData.waterLevel) }}
          </div>
          <div class="text-lg text-blue-500">{{ levelData.waterLevelUnit || 'm' }}</div>
        </div>

        <!-- Temperature -->
        <div class="bg-orange-50 rounded-lg p-6">
          <p class="text-sm text-orange-600 font-semibold mb-2">Temperature</p>
          <div class="text-5xl font-bold text-orange-600 mb-2">
            {{ formatValue(levelData.temperature) }}
          </div>
          <div class="text-lg text-orange-500">{{ levelData.temperatureUnit || '°C' }}</div>
        </div>
      </div>

      <!-- Timestamp Info -->
      <div class="mt-6 pt-6 border-t border-gray-200">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <p class="text-gray-500">Last Updated</p>
            <p class="font-medium text-gray-800">{{ formattedTimestamp }}</p>
          </div>
          <div>
            <p class="text-gray-500">Data Age</p>
            <p class="font-medium text-gray-800">{{ dataAgeText }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { getLatestData } from '../services/api';
import { formatTimestamp, formatDataAge } from '../utils/date';
import { useAutoRefresh } from '../composables/useAutoRefresh';

// Props
const props = defineProps({
  stationId: {
    type: String,
    default: 'lee_waterworks',
  },
});

// Reactive state
const levelData = ref(null);
const loading = ref(true);
const error = ref(null);
const isRefreshing = ref(false);

// Computed properties
const formattedTimestamp = computed(() => {
  if (!levelData.value?.timestamp) return 'N/A';
  return formatTimestamp(levelData.value.timestamp, 'PPp');
});

const dataAgeText = computed(() => {
  if (!levelData.value?.dataAge) return 'N/A';
  return formatDataAge(levelData.value.dataAge);
});

// Methods
function formatValue(value) {
  if (value === null || value === undefined) return 'N/A';
  return typeof value === 'number' ? value.toFixed(2) : value;
}

async function fetchData() {
  try {
    // Don't show full loading state on auto-refresh
    if (levelData.value) {
      isRefreshing.value = true;
    } else {
      loading.value = true;
    }
    error.value = null;

    // Fetch all stations data and find the water level station
    const response = await getLatestData();
    const station = response.stations?.find(s => s.stationId === props.stationId);

    if (!station) {
      throw new Error(`Station ${props.stationId} not found`);
    }

    levelData.value = station;
  } catch (err) {
    error.value = err.message;
    console.error('Failed to fetch water level data:', err);
  } finally {
    loading.value = false;
    isRefreshing.value = false;
  }
}

// Auto-refresh every 15 minutes
const { lastRefreshTime } = useAutoRefresh(fetchData, 15 * 60 * 1000);

// Lifecycle hooks
onMounted(() => {
  fetchData();
});
</script>

<style scoped>
/* Component-specific styles can go here if needed */
</style>
