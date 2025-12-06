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
              <p class="text-sm text-gray-600">Irish Rivers Flow Monitoring</p>
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
      <!-- Introduction -->
      <div class="mb-8 text-center">
        <h2 class="text-xl font-semibold text-gray-800 mb-2">
          River Lee Monitoring
        </h2>
        <p class="text-gray-600 max-w-2xl mx-auto">
          Monitor real-time water flow, water level, and temperature data from multiple stations on the River Lee, Cork, Ireland.
        </p>
      </div>

      <!-- Station Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <!-- Inniscarra Dam Flow -->
        <div>
          <h3 class="text-lg font-semibold text-gray-800 mb-4">Inniscarra Dam - Flow Rate</h3>
          <FlowStatus station-id="inniscarra" />
          <div class="mt-4">
            <FlowChart station-id="inniscarra" />
          </div>
        </div>

        <!-- Waterworks Weir - Water Level & Temperature -->
        <div>
          <h3 class="text-lg font-semibold text-gray-800 mb-4">Waterworks Weir - Water Level & Temperature</h3>
          <WaterLevelStatus station-id="lee_waterworks" />
          <div class="mt-4">
            <WaterLevelChart station-id="lee_waterworks" />
          </div>
        </div>
      </div>

      <!-- Information Cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div class="card">
          <div class="text-3xl mb-3">📊</div>
          <h3 class="text-lg font-semibold text-gray-800 mb-2">Flow Levels</h3>
          <ul class="text-sm text-gray-600 space-y-1">
            <li><span class="text-blue-600 font-medium">Low:</span> &lt; 5 m³/s</li>
            <li><span class="text-green-600 font-medium">Normal:</span> 6-20 m³/s</li>
            <li><span class="text-amber-600 font-medium">High:</span> 30-60 m³/s</li>
            <li><span class="text-red-600 font-medium">Very High:</span> &gt; 100 m³/s</li>
          </ul>
        </div>

        <div class="card">
          <div class="text-3xl mb-3">⏱️</div>
          <h3 class="text-lg font-semibold text-gray-800 mb-2">Data Updates</h3>
          <p class="text-sm text-gray-600">
            Flow data is collected automatically every hour at 30 minutes past the hour from ESB Hydro. Refresh the page to see the latest data.
          </p>
        </div>

        <div class="card">
          <div class="text-3xl mb-3">📍</div>
          <h3 class="text-lg font-semibold text-gray-800 mb-2">Location</h3>
          <p class="text-sm text-gray-600">
            Inniscarra Dam is located on the River Lee, approximately 10km west of Cork City. It's a key hydroelectric facility in Ireland.
          </p>
        </div>
      </div>
    </main>

    <!-- Footer -->
    <footer class="bg-white border-t border-gray-200 mt-12">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div class="text-center text-sm text-gray-500">
          <p class="mb-1">
            Data sourced from ESB Hydro and waterlevel.ie | Updates hourly at 30 minutes past the hour
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
import FlowStatus from './components/FlowStatus.vue';
import FlowChart from './components/FlowChart.vue';
import WaterLevelStatus from './components/WaterLevelStatus.vue';
import WaterLevelChart from './components/WaterLevelChart.vue';
</script>

<style>
/* Global styles are imported from style.css */
</style>
