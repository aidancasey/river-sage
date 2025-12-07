<template>
  <div class="card">
    <div class="mb-6">
      <h3 class="text-xl font-bold text-gray-800 mb-2 text-center">Sun Times</h3>
      <p class="text-sm text-gray-600 text-center">{{ locationName }}</p>
    </div>

    <!-- Loading State with Skeleton -->
    <div v-if="loading" class="animate-fade-in">
      <div class="space-y-4">
        <!-- Day toggle skeleton -->
        <div class="flex gap-2 justify-center mb-6">
          <div class="h-10 bg-gray-200 rounded-lg w-24 animate-pulse"></div>
          <div class="h-10 bg-gray-200 rounded-lg w-24 animate-pulse"></div>
        </div>

        <!-- Sun times grid skeleton -->
        <div class="grid grid-cols-2 gap-4">
          <div v-for="i in 4" :key="i" class="text-center">
            <div class="h-8 bg-gray-200 rounded w-16 mx-auto animate-pulse mb-2"></div>
            <div class="h-6 bg-gray-200 rounded w-20 mx-auto animate-pulse"></div>
            <div class="h-4 bg-gray-200 rounded w-12 mx-auto animate-pulse mt-1"></div>
          </div>
        </div>

        <!-- Day length skeleton -->
        <div class="pt-4 border-t border-gray-200 mt-6">
          <div class="h-4 bg-gray-200 rounded w-24 mx-auto animate-pulse mb-2"></div>
          <div class="h-6 bg-gray-200 rounded w-32 mx-auto animate-pulse"></div>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="text-center py-8 animate-fade-in">
      <div class="text-red-500 text-4xl mb-4">⚠️</div>
      <h4 class="text-lg font-semibold text-red-600 mb-2">Error Loading Sun Times</h4>
      <p class="text-gray-600 mb-4">{{ error }}</p>
      <button @click="fetchData" class="btn btn-primary">
        Try Again
      </button>
    </div>

    <!-- Data Display -->
    <div v-else-if="sunData" class="animate-fade-in">
      <!-- Day Toggle -->
      <div class="flex gap-2 justify-center mb-6">
        <button
          @click="selectedDay = 'today'"
          class="btn text-sm px-6"
          :class="
            selectedDay === 'today'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          "
        >
          Today
        </button>
        <button
          @click="selectedDay = 'tomorrow'"
          class="btn text-sm px-6"
          :class="
            selectedDay === 'tomorrow'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          "
        >
          Tomorrow
        </button>
      </div>

      <!-- Sun Times Grid -->
      <div class="grid grid-cols-2 gap-4 mb-6">
        <!-- Dawn -->
        <div class="text-center">
          <div class="text-3xl mb-2">🌄</div>
          <div class="text-xl font-bold text-gray-800">{{ currentData.dawn }}</div>
          <div class="text-xs text-gray-500 mt-1">Dawn</div>
        </div>

        <!-- Sunrise -->
        <div class="text-center">
          <div class="text-3xl mb-2">🌅</div>
          <div class="text-xl font-bold text-orange-600">{{ currentData.sunrise }}</div>
          <div class="text-xs text-gray-500 mt-1">Sunrise</div>
        </div>

        <!-- Sunset -->
        <div class="text-center">
          <div class="text-3xl mb-2">🌆</div>
          <div class="text-xl font-bold text-orange-600">{{ currentData.sunset }}</div>
          <div class="text-xs text-gray-500 mt-1">Sunset</div>
        </div>

        <!-- Dusk -->
        <div class="text-center">
          <div class="text-3xl mb-2">🌇</div>
          <div class="text-xl font-bold text-gray-800">{{ currentData.dusk }}</div>
          <div class="text-xs text-gray-500 mt-1">Dusk</div>
        </div>
      </div>

      <!-- Day Length -->
      <div class="pt-4 border-t border-gray-200 mt-6 text-center">
        <p class="text-sm text-gray-500 mb-1">Day Length</p>
        <p class="text-lg font-bold text-blue-600">{{ currentData.dayLength }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { getSunTimesTodayAndTomorrow } from '../services/sunTimes';
import { useAutoRefresh } from '../composables/useAutoRefresh';

// Props
const props = defineProps({
  riverId: {
    type: String,
    required: true,
  },
});

// Reactive state
const sunData = ref(null);
const loading = ref(true);
const error = ref(null);
const selectedDay = ref('today');

// Computed properties
const locationName = computed(() => {
  if (!sunData.value) return '';
  return sunData.value.today?.location || '';
});

const currentData = computed(() => {
  if (!sunData.value) return null;
  return selectedDay.value === 'today' ? sunData.value.today : sunData.value.tomorrow;
});

// Methods
async function fetchData() {
  try {
    loading.value = true;
    error.value = null;

    sunData.value = await getSunTimesTodayAndTomorrow(props.riverId);
  } catch (err) {
    error.value = err.message;
    console.error('Failed to fetch sun times:', err);
  } finally {
    loading.value = false;
  }
}

// Watch for river changes
watch(() => props.riverId, () => {
  fetchData();
});

// Auto-refresh once per day (24 hours)
const { lastRefreshTime } = useAutoRefresh(fetchData, 24 * 60 * 60 * 1000);

// Lifecycle hooks
onMounted(() => {
  fetchData();
});
</script>

<style scoped>
/* Component-specific styles can go here if needed */
</style>
