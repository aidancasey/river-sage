<template>
  <div id="app" class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center">
            <div class="text-3xl mr-3">🌊</div>
            <div>
              <h1 class="text-2xl font-bold text-gray-900">River Guru</h1>
              <p class="text-sm text-gray-600">Irish Rivers Monitoring</p>
            </div>
          </div>
          <div class="hidden sm:block text-right">
            <p class="text-xs text-gray-500">Real-time data from</p>
            <p class="text-sm font-medium text-gray-700">ESB Hydro & waterlevel.ie</p>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- River Selector -->
      <RiverSelector
        :selected-river="selectedRiver"
        :rivers="rivers"
        @select-river="selectRiver"
      />

      <!-- River Title -->
      <div class="mb-8 text-center">
        <h2 class="text-2xl font-bold text-gray-800 mb-2">
          {{ currentRiverConfig.name }}
        </h2>
        <p class="text-gray-600 max-w-2xl mx-auto">
          {{ currentRiverConfig.description }}
        </p>
      </div>

      <!-- Station Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <!-- Flow Station (Inniscarra Dam only) -->
        <div v-for="station in flowStations" :key="station.id">
          <h3 class="text-lg font-semibold text-gray-800 mb-4">{{ station.name }} - Flow Rate</h3>
          <FlowStatus :station-id="station.id" />
          <div class="mt-4">
            <FlowChart :station-id="station.id" />
          </div>
        </div>

        <!-- Water Level Stations -->
        <div v-for="station in waterLevelStations" :key="station.id">
          <h3 class="text-lg font-semibold text-gray-800 mb-4">{{ station.name }} - Water Level & Temperature</h3>
          <WaterLevelStatus :station-id="station.id" />
          <div class="mt-4">
            <WaterLevelChart :station-id="station.id" />
          </div>
        </div>
      </div>

      <!-- Information Cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <!-- Dynamic Card 1: Flow or Water Level info -->
        <div class="card animate-fade-in">
          <div class="text-3xl mb-3">{{ hasFlowStation ? '📊' : '💧' }}</div>
          <h3 class="text-lg font-semibold text-gray-800 mb-2">
            {{ hasFlowStation ? 'Flow Levels' : 'Water Levels' }}
          </h3>
          <div v-if="hasFlowStation">
            <ul class="text-sm text-gray-600 space-y-1">
              <li><span class="text-blue-600 font-medium">Low:</span> &lt; 5 m³/s</li>
              <li><span class="text-green-600 font-medium">Normal:</span> 6-20 m³/s</li>
              <li><span class="text-amber-600 font-medium">High:</span> 30-60 m³/s</li>
              <li><span class="text-red-600 font-medium">Very High:</span> &gt; 100 m³/s</li>
            </ul>
          </div>
          <div v-else>
            <p class="text-sm text-gray-600">
              Water levels are measured in meters (m) and updated every 15 minutes. Temperature readings (°C) are recorded hourly.
            </p>
          </div>
        </div>

        <div class="card animate-fade-in" style="animation-delay: 0.1s">
          <div class="text-3xl mb-3">⏱️</div>
          <h3 class="text-lg font-semibold text-gray-800 mb-2">Data Updates</h3>
          <p class="text-sm text-gray-600">
            Data refreshes automatically every 15 minutes. Historical data is collected hourly. Click the refresh button on any station for the latest readings.
          </p>
        </div>

        <div class="card animate-fade-in" style="animation-delay: 0.2s">
          <div class="text-3xl mb-3">📍</div>
          <h3 class="text-lg font-semibold text-gray-800 mb-2">About {{ currentRiverConfig.name }}</h3>
          <p class="text-sm text-gray-600">
            {{ currentRiverConfig.info }}
          </p>
        </div>
      </div>
    </main>

    <!-- Footer -->
    <footer class="bg-white border-t border-gray-200 mt-12">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div class="text-center text-sm text-gray-500">
          <p class="mb-1">
            Data sourced from ESB Hydro and waterlevel.ie | Updates hourly
          </p>
          <p class="text-xs">
            Water level data from Office of Public Works (OPW) via waterlevel.ie (CC BY 4.0)
          </p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import FlowStatus from './components/FlowStatus.vue';
import FlowChart from './components/FlowChart.vue';
import WaterLevelStatus from './components/WaterLevelStatus.vue';
import WaterLevelChart from './components/WaterLevelChart.vue';
import RiverSelector from './components/RiverSelector.vue';

// River configurations
const riverConfigs = {
  lee: {
    name: 'River Lee',
    description: 'Monitor water flow, levels, and temperature from multiple stations on the River Lee, Cork, Ireland.',
    info: 'The River Lee flows through Cork City and is monitored at Inniscarra Dam and Waterworks Weir.',
    stations: [
      { id: 'inniscarra', name: 'Inniscarra Dam', type: 'flow' },
      { id: 'lee_waterworks', name: 'Waterworks Weir', type: 'water_level' }
    ]
  },
  blackwater: {
    name: 'River Blackwater',
    description: 'Real-time water level and temperature monitoring at Fermoy and Mallow on the River Blackwater.',
    info: 'The Blackwater is one of Ireland\'s premier salmon rivers, flowing through Counties Cork and Waterford.',
    stations: [
      { id: 'blackwater_fermoy', name: 'Fermoy Town', type: 'water_level' },
      { id: 'blackwater_mallow', name: 'Mallow Railway Bridge', type: 'water_level' }
    ]
  },
  suir: {
    name: 'River Suir',
    description: 'Water level and temperature data from the New Bridge monitoring station near Golden, Co. Tipperary.',
    info: 'The River Suir flows through the Golden Vale, one of Ireland\'s most fertile agricultural regions.',
    stations: [
      { id: 'suir_golden', name: 'New Bridge (Golden)', type: 'water_level' }
    ]
  },
  bandon: {
    name: 'River Bandon',
    description: 'Monitor water levels and temperature at Curranure on the River Bandon, West Cork.',
    info: 'The River Bandon flows through West Cork to Kinsale harbour, supporting diverse wildlife habitats.',
    stations: [
      { id: 'bandon_curranure', name: 'Curranure', type: 'water_level' }
    ]
  },
  owenboy: {
    name: 'River Owenboy',
    description: 'Real-time water level and temperature monitoring on the River Owenboy.',
    info: 'The River Owenboy is a tributary river system in County Cork.',
    stations: [
      { id: 'owenboy', name: 'Owenboy', type: 'water_level' }
    ]
  }
};

// River list for selector
const rivers = [
  { id: 'lee', name: 'River Lee', icon: '🌊', stationCount: 2 },
  { id: 'blackwater', name: 'River Blackwater', icon: '🏞️', stationCount: 2 },
  { id: 'suir', name: 'River Suir', icon: '⛰️', stationCount: 1 },
  { id: 'bandon', name: 'River Bandon', icon: '🌲', stationCount: 1 },
  { id: 'owenboy', name: 'River Owenboy', icon: '💧', stationCount: 1 }
];

// Initialize selected river from URL or default to 'lee'
const getInitialRiver = () => {
  const params = new URLSearchParams(window.location.search);
  const riverParam = params.get('river');
  // Validate river exists in config
  return riverParam && riverConfigs[riverParam] ? riverParam : 'lee';
};

// Selected river state
const selectedRiver = ref(getInitialRiver());

// Computed properties
const currentRiverConfig = computed(() => riverConfigs[selectedRiver.value]);

const flowStations = computed(() =>
  currentRiverConfig.value.stations.filter(s => s.type === 'flow')
);

const waterLevelStations = computed(() =>
  currentRiverConfig.value.stations.filter(s => s.type === 'water_level')
);

const hasFlowStation = computed(() => flowStations.value.length > 0);

// Methods
function selectRiver(riverId) {
  selectedRiver.value = riverId;

  // Update URL without page reload
  const url = new URL(window.location);
  url.searchParams.set('river', riverId);
  window.history.pushState({}, '', url);

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Handle browser back/forward buttons
window.addEventListener('popstate', () => {
  selectedRiver.value = getInitialRiver();
});
</script>

<style>
/* Global styles are imported from style.css */
</style>
