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

      <!-- Sun Times and Weather Section -->
      <div class="mb-8">
        <h2 class="text-xl font-bold text-gray-800 mb-6 text-center">Local Conditions</h2>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-5xl mx-auto">
          <SunTimes :river-id="selectedRiver" />
          <WeatherForecast :river-id="selectedRiver" />
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
        <div class="text-center">
          <div class="mb-4">
            <button
              @click="openContactForm"
              class="inline-flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              Contact Us
            </button>
          </div>

          <!-- Disclaimer -->
          <div class="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4 max-w-3xl mx-auto">
            <div class="flex items-start gap-2">
              <svg class="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
              <div class="text-left">
                <h3 class="text-sm font-semibold text-amber-900 mb-1">Disclaimer</h3>
                <p class="text-xs text-amber-800 leading-relaxed">
                  This site has user generated content. No guarantee can be made for the accuracy or completeness of content. Your use of this content is AT YOUR OWN RISK. River conditions (such as Gauge Height, Flow Rate, Precipitation, and Temperature) can change without warning, and may be incorrect.
                </p>
              </div>
            </div>
          </div>

          <div class="text-sm text-gray-500">
            <p class="mb-1">
              Data sourced from ESB Hydro and waterlevel.ie | Updates hourly
            </p>
            <p class="text-xs">
              Water level data from Office of Public Works (OPW) via waterlevel.ie (CC BY 4.0)
            </p>
          </div>
        </div>
      </div>
    </footer>

    <!-- Contact Form Modal -->
    <div
      v-if="showContactForm"
      class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
      @click.self="closeContactForm"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden animate-fade-in">
        <div class="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 class="text-xl font-bold text-gray-800">Contact Us</h2>
          <button
            @click="closeContactForm"
            class="p-2 hover:bg-gray-100 rounded-full transition-colors"
            title="Close"
          >
            <svg class="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="overflow-y-auto" style="height: calc(90vh - 80px)">
          <iframe
            src="https://form.jotform.com/210906718558362"
            frameborder="0"
            style="width: 100%; height: 100%; min-height: 600px; border: none;"
            scrolling="yes"
          ></iframe>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import FlowStatus from './components/FlowStatus.vue';
import FlowChart from './components/FlowChart.vue';
import WaterLevelStatus from './components/WaterLevelStatus.vue';
import WaterLevelChart from './components/WaterLevelChart.vue';
import RiverSelector from './components/RiverSelector.vue';
import SunTimes from './components/SunTimes.vue';
import WeatherForecast from './components/WeatherForecast.vue';

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

// Contact form modal state
const showContactForm = ref(false);

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

function openContactForm() {
  showContactForm.value = true;
  // Prevent body scroll when modal is open
  document.body.style.overflow = 'hidden';
}

function closeContactForm() {
  showContactForm.value = false;
  // Restore body scroll
  document.body.style.overflow = '';
}

// Handle browser back/forward buttons
window.addEventListener('popstate', () => {
  selectedRiver.value = getInitialRiver();
});
</script>

<style>
/* Global styles are imported from style.css */
</style>
