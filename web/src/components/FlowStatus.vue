<template>
  <div class="card">
    <!-- Loading State -->
    <div v-if="loading" class="text-center py-8">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
      <p class="mt-4 text-gray-600">Loading flow data...</p>
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
    <div v-else-if="flowData" class="text-center">
      <!-- Station Info -->
      <div class="mb-6">
        <h2 class="text-2xl font-bold text-gray-800">{{ flowData.name }}</h2>
        <p class="text-gray-600">{{ flowData.river }}</p>
      </div>

      <!-- Current Flow Rate -->
      <div class="mb-6">
        <div class="text-6xl font-bold mb-2" :class="statusColor.text">
          {{ flowData.currentFlow.toFixed(1) }}
        </div>
        <div class="text-2xl text-gray-600 mb-4">{{ flowData.unit }}</div>

        <!-- Status Badge -->
        <div
          class="inline-block px-6 py-2 rounded-full text-white font-semibold text-lg"
          :class="statusColor.bg"
        >
          {{ statusColor.label }}
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
import { getLatestFlow, getFlowStatusColor } from '../services/api';
import { formatTimestamp, formatDataAge } from '../utils/date';

// Props
const props = defineProps({
  stationId: {
    type: String,
    default: 'inniscarra',
  },
});

// Reactive state
const flowData = ref(null);
const loading = ref(true);
const error = ref(null);

// Computed properties
const statusColor = computed(() => {
  if (!flowData.value) return getFlowStatusColor('normal');
  return getFlowStatusColor(flowData.value.status);
});

const formattedTimestamp = computed(() => {
  if (!flowData.value?.timestamp) return 'N/A';
  return formatTimestamp(flowData.value.timestamp, 'PPp');
});

const dataAgeText = computed(() => {
  if (!flowData.value?.dataAge) return 'N/A';
  return formatDataAge(flowData.value.dataAge);
});

// Methods
async function fetchData() {
  try {
    loading.value = true;
    error.value = null;
    flowData.value = await getLatestFlow(props.stationId);
  } catch (err) {
    error.value = err.message;
    console.error('Failed to fetch flow data:', err);
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
