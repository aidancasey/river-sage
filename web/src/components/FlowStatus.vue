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

        <!-- Value skeleton -->
        <div class="h-20 bg-gray-200 rounded w-40 mx-auto animate-pulse mt-6"></div>
        <div class="h-6 bg-gray-200 rounded w-24 mx-auto animate-pulse"></div>

        <!-- Badge skeleton -->
        <div class="h-10 bg-gray-200 rounded-full w-32 mx-auto animate-pulse mt-4"></div>

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
    <div v-else-if="flowData" class="text-center animate-fade-in">
      <!-- Station Info -->
      <div class="mb-6">
        <div class="flex items-center justify-between mb-2">
          <div class="flex-1"></div>
          <h2 class="text-2xl font-bold text-gray-800 flex-1">{{ flowData.name }}</h2>
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
import { useAutoRefresh } from '../composables/useAutoRefresh';

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
const isRefreshing = ref(false);

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
    // Don't show full loading state on auto-refresh
    if (flowData.value) {
      isRefreshing.value = true;
    } else {
      loading.value = true;
    }
    error.value = null;
    flowData.value = await getLatestFlow(props.stationId);
  } catch (err) {
    error.value = err.message;
    console.error('Failed to fetch flow data:', err);
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
