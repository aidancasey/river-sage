<template>
  <div class="card">
    <div class="mb-6">
      <h3 class="text-xl font-bold text-gray-800 mb-4">Historical Water Level & Temperature</h3>

      <!-- Time Range Selector -->
      <div class="flex flex-wrap gap-2 mb-4">
        <button
          v-for="range in timeRanges"
          :key="range.value"
          @click="selectTimeRange(range)"
          class="btn text-sm"
          :class="
            selectedRange === range.value
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          "
        >
          {{ range.label }}
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
      <p class="mt-4 text-gray-600">Loading chart data...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="text-center py-12">
      <div class="text-red-500 text-4xl mb-4">📊</div>
      <h4 class="text-lg font-semibold text-red-600 mb-2">Chart Error</h4>
      <p class="text-gray-600">{{ error }}</p>
      <button @click="fetchData" class="btn btn-primary mt-4">
        Retry
      </button>
    </div>

    <!-- Chart Display -->
    <div v-else>
      <!-- Water Level Chart -->
      <div class="mb-6">
        <h4 class="text-sm font-semibold text-gray-700 mb-3">Water Level (m)</h4>
        <div class="chart-container" style="position: relative; height: 250px">
          <Line :data="waterLevelChartData" :options="waterLevelChartOptions" />
        </div>
      </div>

      <!-- Temperature Chart -->
      <div>
        <h4 class="text-sm font-semibold text-gray-700 mb-3">Temperature (°C)</h4>
        <div class="chart-container" style="position: relative; height: 250px">
          <Line :data="temperatureChartData" :options="temperatureChartOptions" />
        </div>
      </div>

      <!-- Statistics -->
      <div v-if="waterLevelStats || temperatureStats" class="mt-6 pt-6 border-t border-gray-200">
        <!-- Water Level Stats -->
        <div v-if="waterLevelStats" class="mb-4">
          <h4 class="text-sm font-semibold text-gray-700 mb-3">Water Level Statistics</h4>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="text-center">
              <p class="text-sm text-gray-500">Min</p>
              <p class="text-xl font-bold text-blue-600">{{ waterLevelStats.min }}</p>
              <p class="text-xs text-gray-400">m</p>
            </div>
            <div class="text-center">
              <p class="text-sm text-gray-500">Max</p>
              <p class="text-xl font-bold text-blue-800">{{ waterLevelStats.max }}</p>
              <p class="text-xs text-gray-400">m</p>
            </div>
            <div class="text-center">
              <p class="text-sm text-gray-500">Average</p>
              <p class="text-xl font-bold text-blue-500">{{ waterLevelStats.average }}</p>
              <p class="text-xs text-gray-400">m</p>
            </div>
            <div class="text-center">
              <p class="text-sm text-gray-500">Range</p>
              <p class="text-xl font-bold text-gray-700">{{ waterLevelStats.range }}</p>
              <p class="text-xs text-gray-400">m</p>
            </div>
          </div>
        </div>

        <!-- Temperature Stats -->
        <div v-if="temperatureStats">
          <h4 class="text-sm font-semibold text-gray-700 mb-3">Temperature Statistics</h4>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="text-center">
              <p class="text-sm text-gray-500">Min</p>
              <p class="text-xl font-bold text-orange-600">{{ temperatureStats.min }}</p>
              <p class="text-xs text-gray-400">°C</p>
            </div>
            <div class="text-center">
              <p class="text-sm text-gray-500">Max</p>
              <p class="text-xl font-bold text-orange-800">{{ temperatureStats.max }}</p>
              <p class="text-xs text-gray-400">°C</p>
            </div>
            <div class="text-center">
              <p class="text-sm text-gray-500">Average</p>
              <p class="text-xl font-bold text-orange-500">{{ temperatureStats.average }}</p>
              <p class="text-xs text-gray-400">°C</p>
            </div>
            <div class="text-center">
              <p class="text-sm text-gray-500">Range</p>
              <p class="text-xl font-bold text-gray-700">{{ temperatureStats.range }}</p>
              <p class="text-xs text-gray-400">°C</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Data point count -->
      <div class="mt-4 text-center text-xs text-gray-400">
        {{ dataPointCount }} data points
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { Line } from 'vue-chartjs';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';
import { getHistoricalFlow } from '../services/api';
import { formatTimestamp } from '../utils/date';

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

// Props
const props = defineProps({
  stationId: {
    type: String,
    default: 'lee_waterworks',
  },
});

// Time range options
const timeRanges = [
  { label: '24 Hours', value: 24, hours: 24 },
  { label: '7 Days', value: 168, hours: 168 },
  { label: '30 Days', value: 720, hours: 720 },
];

// Reactive state
const selectedRange = ref(24);
const loading = ref(true);
const error = ref(null);
const historicalData = ref(null);

// Computed properties
const waterLevelChartData = computed(() => {
  if (!historicalData.value?.readings) return { labels: [], datasets: [] };

  const readings = historicalData.value.readings.filter(r => r.water_level_m !== null && r.water_level_m !== undefined);

  return {
    labels: readings.map(r => formatTimestamp(r.timestamp, 'MMM d, HH:mm')),
    datasets: [
      {
        label: 'Water Level (m)',
        data: readings.map(r => r.water_level_m),
        borderColor: 'rgb(37, 99, 235)',
        backgroundColor: 'rgba(37, 99, 235, 0.1)',
        tension: 0.3,
        fill: true,
        pointRadius: 2,
        pointHoverRadius: 5,
      },
    ],
  };
});

const temperatureChartData = computed(() => {
  if (!historicalData.value?.readings) return { labels: [], datasets: [] };

  const readings = historicalData.value.readings.filter(r => r.temperature_c !== null && r.temperature_c !== undefined);

  return {
    labels: readings.map(r => formatTimestamp(r.timestamp, 'MMM d, HH:mm')),
    datasets: [
      {
        label: 'Temperature (°C)',
        data: readings.map(r => r.temperature_c),
        borderColor: 'rgb(249, 115, 22)',
        backgroundColor: 'rgba(249, 115, 22, 0.1)',
        tension: 0.3,
        fill: true,
        pointRadius: 2,
        pointHoverRadius: 5,
      },
    ],
  };
});

const waterLevelChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false,
    },
    tooltip: {
      mode: 'index',
      intersect: false,
      callbacks: {
        label: (context) => `${context.parsed.y.toFixed(2)} m`,
      },
    },
  },
  scales: {
    y: {
      beginAtZero: false,
      ticks: {
        callback: (value) => `${value.toFixed(2)} m`,
      },
    },
    x: {
      ticks: {
        maxRotation: 45,
        minRotation: 45,
      },
    },
  },
}));

const temperatureChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false,
    },
    tooltip: {
      mode: 'index',
      intersect: false,
      callbacks: {
        label: (context) => `${context.parsed.y.toFixed(1)} °C`,
      },
    },
  },
  scales: {
    y: {
      beginAtZero: false,
      ticks: {
        callback: (value) => `${value.toFixed(1)} °C`,
      },
    },
    x: {
      ticks: {
        maxRotation: 45,
        minRotation: 45,
      },
    },
  },
}));

const waterLevelStats = computed(() => {
  if (!historicalData.value?.readings) return null;

  const readings = historicalData.value.readings
    .map(r => r.water_level_m)
    .filter(v => v !== null && v !== undefined);

  if (readings.length === 0) return null;

  const min = Math.min(...readings);
  const max = Math.max(...readings);
  const average = readings.reduce((sum, v) => sum + v, 0) / readings.length;
  const range = max - min;

  return {
    min: min.toFixed(2),
    max: max.toFixed(2),
    average: average.toFixed(2),
    range: range.toFixed(2),
  };
});

const temperatureStats = computed(() => {
  if (!historicalData.value?.readings) return null;

  const readings = historicalData.value.readings
    .map(r => r.temperature_c)
    .filter(v => v !== null && v !== undefined);

  if (readings.length === 0) return null;

  const min = Math.min(...readings);
  const max = Math.max(...readings);
  const average = readings.reduce((sum, v) => sum + v, 0) / readings.length;
  const range = max - min;

  return {
    min: min.toFixed(1),
    max: max.toFixed(1),
    average: average.toFixed(1),
    range: range.toFixed(1),
  };
});

const dataPointCount = computed(() => {
  return historicalData.value?.readings?.length || 0;
});

// Methods
function selectTimeRange(range) {
  selectedRange.value = range.value;
  fetchData();
}

async function fetchData() {
  try {
    loading.value = true;
    error.value = null;

    const response = await getHistoricalFlow(props.stationId, {
      hours: selectedRange.value,
    });

    // Transform the data structure from new API format
    // API returns: dataPoints with waterLevel and temperature fields
    historicalData.value = {
      readings: (response.dataPoints || []).map(point => ({
        timestamp: point.timestamp,
        water_level_m: point.waterLevel,
        temperature_c: point.temperature
      })),
    };
  } catch (err) {
    error.value = err.message;
    console.error('Failed to fetch historical data:', err);
  } finally {
    loading.value = false;
  }
}

// Lifecycle hooks
onMounted(() => {
  fetchData();
});

// Watch for station changes
watch(() => props.stationId, () => {
  fetchData();
});
</script>

<style scoped>
.chart-container {
  position: relative;
}
</style>
