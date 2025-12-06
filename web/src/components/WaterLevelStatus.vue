<template>
  <div class="card">
    <!-- Loading State -->
    <div v-if="loading" class="text-center py-8">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
      <p class="mt-4 text-gray-600">Loading water level data...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="text-center py-8">
      <div class="text-red-500 text-5xl mb-4">⚠️</div>
      <h3 class="text-xl font-semibold text-red-600 mb-2">Error Loading Data</h3>
      <p class="text-gray-600">{{ error }}</p>
      <button @click="fetchData" class="btn btn-primary mt-4">
        Try Again
      </button>
    </div>

    <!-- Data Display -->
    <div v-else-if="levelData" class="text-center">
      <!-- Station Info -->
      <div class="mb-6">
        <h2 class="text-2xl font-bold text-gray-800">{{ levelData.name }}</h2>
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
    loading.value = true;
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
  }
}

// Lifecycle hooks
onMounted(() => {
  fetchData();
});
</script>

<style scoped>
/* Component-specific styles can go here if needed */
</style>
