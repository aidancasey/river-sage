<template>
  <div class="card">
    <div class="mb-6">
      <h3 class="text-xl font-bold text-gray-800 mb-4">Historical Flow Data</h3>

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
      <div class="chart-container" style="position: relative; height: 300px">
        <Line :data="chartData" :options="chartOptions" />
      </div>

      <!-- Statistics -->
      <div v-if="statistics" class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t border-gray-200">
        <div class="text-center">
          <p class="text-sm text-gray-500">Minimum</p>
          <p class="text-xl font-bold text-blue-600">{{ statistics.min }}</p>
          <p class="text-xs text-gray-400">m³/s</p>
        </div>
        <div class="text-center">
          <p class="text-sm text-gray-500">Maximum</p>
          <p class="text-xl font-bold text-red-600">{{ statistics.max }}</p>
          <p class="text-xs text-gray-400">m³/s</p>
        </div>
        <div class="text-center">
          <p class="text-sm text-gray-500">Average</p>
          <p class="text-xl font-bold text-green-600">{{ statistics.average }}</p>
          <p class="text-xs text-gray-400">m³/s</p>
        </div>
        <div class="text-center">
          <p class="text-sm text-gray-500">Trend</p>
          <p class="text-xl font-bold text-gray-700">
            <span v-if="statistics.trend === 'increasing'">📈</span>
            <span v-else-if="statistics.trend === 'decreasing'">📉</span>
            <span v-else>➡️</span>
          </p>
          <p class="text-xs text-gray-400 capitalize">{{ statistics.trend }}</p>
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
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { getHistoricalFlow } from '../services/api';
import { format, parseISO } from 'date-fns';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

// Props
const props = defineProps({
  stationId: {
    type: String,
    default: 'inniscarra',
  },
});

// Reactive state
const historicalData = ref(null);
const loading = ref(true);
const error = ref(null);
const selectedRange = ref(24); // hours

// Time range options
const timeRanges = [
  { label: '24 Hours', value: 24, unit: 'hours' },
  { label: '7 Days', value: 7, unit: 'days' },
  { label: '30 Days', value: 30, unit: 'days' },
  { label: '90 Days', value: 90, unit: 'days' },
];

// Computed properties
const statistics = computed(() => historicalData.value?.statistics || null);

const dataPointCount = computed(() => historicalData.value?.count || 0);

const chartData = computed(() => {
  if (!historicalData.value?.dataPoints) {
    return {
      labels: [],
      datasets: [],
    };
  }

  const dataPoints = historicalData.value.dataPoints;

  return {
    labels: dataPoints.map((point) => {
      const date = parseISO(point.timestamp);
      // Format based on time range
      if (selectedRange.value <= 24) {
        return format(date, 'HH:mm'); // Show time for 24h view
      } else if (selectedRange.value <= 7) {
        return format(date, 'MMM d HH:mm'); // Show date and time for week view
      } else {
        return format(date, 'MMM d'); // Show just date for longer ranges
      }
    }),
    datasets: [
      {
        label: 'Flow Rate (m³/s)',
        data: dataPoints.map((point) => point.flow),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 2,
        pointHoverRadius: 5,
      },
    ],
  };
});

const chartOptions = computed(() => ({
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
        label: (context) => `Flow: ${context.parsed.y.toFixed(1)} m³/s`,
      },
    },
  },
  scales: {
    x: {
      ticks: {
        maxRotation: 45,
        minRotation: 45,
        autoSkip: true,
        maxTicksLimit: 12,
      },
      grid: {
        display: false,
      },
    },
    y: {
      beginAtZero: false,
      ticks: {
        callback: (value) => `${value} m³/s`,
      },
      grid: {
        color: 'rgba(0, 0, 0, 0.05)',
      },
    },
  },
  interaction: {
    mode: 'nearest',
    axis: 'x',
    intersect: false,
  },
}));

// Methods
async function fetchData() {
  try {
    loading.value = true;
    error.value = null;

    const currentRange = timeRanges.find((r) => r.value === selectedRange.value);
    const options = currentRange.unit === 'days'
      ? { days: currentRange.value }
      : { hours: currentRange.value };

    historicalData.value = await getHistoricalFlow(props.stationId, options);
  } catch (err) {
    error.value = err.message;
    console.error('Failed to fetch historical data:', err);
  } finally {
    loading.value = false;
  }
}

function selectTimeRange(range) {
  selectedRange.value = range.value;
  fetchData();
}

// Watch for station changes
watch(() => props.stationId, fetchData);

// Lifecycle
onMounted(() => {
  fetchData();
});
</script>

<style scoped>
.chart-container {
  width: 100%;
}
</style>
