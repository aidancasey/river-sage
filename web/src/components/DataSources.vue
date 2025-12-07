<template>
  <div class="max-w-4xl mx-auto px-4 py-12">
    <h1 class="text-3xl font-bold text-gray-900 mb-8">Data Sources</h1>

    <div class="space-y-8">
      <!-- ESB Hydro -->
      <div class="card">
        <h2 class="text-xl font-semibold text-gray-800 mb-3">ESB Hydro</h2>
        <p class="text-gray-600 mb-3">
          Flow rate data for the River Lee at Inniscarra Dam is sourced from ESB (Electricity Supply Board) Hydro.
          ESB operates Ireland's hydroelectric power stations and provides real-time flow data from their dam releases.
        </p>
        <p class="text-sm text-gray-500">
          <strong>Data provided:</strong> Flow rates (m³/s)<br>
          <strong>Update frequency:</strong> Hourly<br>
          <strong>Source:</strong> <a href="https://www.esb.ie" target="_blank" rel="noopener" class="text-blue-600 hover:underline">www.esb.ie</a>
        </p>
      </div>

      <!-- waterlevel.ie (OPW) -->
      <div class="card">
        <h2 class="text-xl font-semibold text-gray-800 mb-3">waterlevel.ie (Office of Public Works)</h2>
        <p class="text-gray-600 mb-3">
          Water level and temperature data is sourced from the Office of Public Works (OPW) via waterlevel.ie.
          The OPW operates a network of monitoring stations across Ireland's rivers and waterways to track water levels
          and provide flood warning information.
        </p>
        <p class="text-sm text-gray-500 mb-3">
          <strong>Data provided:</strong> Water levels (m), Temperature (°C)<br>
          <strong>Update frequency:</strong> 15-minute intervals<br>
          <strong>Stations monitored:</strong>
        </p>
        <ul class="text-sm text-gray-600 mb-3 ml-6 list-disc">
          <li>River Lee - Waterworks Weir (Station ID: 19102)</li>
          <li>River Blackwater - Fermoy Town (Station ID: 30006)</li>
          <li>River Blackwater - Mallow Railway Bridge (Station ID: 30022)</li>
          <li>River Suir - New Bridge, Golden (Station ID: 16006)</li>
          <li>River Bandon - Curranure (Station ID: 19031)</li>
          <li>River Owenboy - Owenboy (Station ID: 19027)</li>
        </ul>
        <p class="text-sm text-gray-500">
          <strong>Source:</strong> <a href="https://waterlevel.ie" target="_blank" rel="noopener" class="text-blue-600 hover:underline">waterlevel.ie</a><br>
          <strong>License:</strong> <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener" class="text-blue-600 hover:underline">Creative Commons Attribution 4.0 International (CC BY 4.0)</a>
        </p>
      </div>

      <!-- Open-Meteo -->
      <div class="card">
        <h2 class="text-xl font-semibold text-gray-800 mb-3">Open-Meteo</h2>
        <p class="text-gray-600 mb-3">
          Weather forecast data is provided by Open-Meteo, a free weather API that aggregates data from national
          weather services including Met Éireann for Irish forecasts.
        </p>
        <p class="text-sm text-gray-500">
          <strong>Data provided:</strong> 7-day weather forecasts, temperature, precipitation, wind speed<br>
          <strong>Update frequency:</strong> Updated multiple times daily<br>
          <strong>Source:</strong> <a href="https://open-meteo.com" target="_blank" rel="noopener" class="text-blue-600 hover:underline">open-meteo.com</a>
        </p>
      </div>

      <!-- Sunrise-Sunset.org -->
      <div class="card">
        <h2 class="text-xl font-semibold text-gray-800 mb-3">Sunrise-Sunset.org</h2>
        <p class="text-gray-600 mb-3">
          Sun times (sunrise, sunset, dawn, dusk) and moon phase data is sourced from the Sunrise-Sunset.org API,
          calculated based on the geographic coordinates of each river monitoring location.
        </p>
        <p class="text-sm text-gray-500">
          <strong>Data provided:</strong> Sunrise, sunset, dawn, dusk times, moon phase<br>
          <strong>Source:</strong> <a href="https://sunrise-sunset.org" target="_blank" rel="noopener" class="text-blue-600 hover:underline">sunrise-sunset.org</a>
        </p>
      </div>

      <!-- Data Processing -->
      <div class="card bg-blue-50 border-blue-200">
        <h2 class="text-xl font-semibold text-gray-800 mb-3">Data Processing & Updates</h2>
        <p class="text-gray-600 mb-3">
          River Guru automatically fetches and processes data from these sources on an hourly basis.
          Historical data is stored and displayed in charts to help you track trends and patterns over time.
        </p>
        <p class="text-sm text-gray-600">
          <strong>Update schedule:</strong> Every hour on the hour<br>
          <strong>Historical data retention:</strong> Rolling 30-day window<br>
          <strong>Infrastructure:</strong> AWS Lambda, S3, CloudFront via Cloudflare
        </p>
      </div>

      <!-- Attribution & License -->
      <div class="card bg-amber-50 border-amber-200">
        <h2 class="text-xl font-semibold text-gray-800 mb-3">Attribution & License</h2>
        <p class="text-gray-600 mb-3">
          River Guru aggregates publicly available data from multiple sources. We are grateful to these organizations
          for making their data accessible. Where required by license terms (such as the OPW data under CC BY 4.0),
          we provide appropriate attribution.
        </p>
        <p class="text-sm text-gray-600">
          If you use or redistribute data from River Guru, please attribute the original data sources as listed above.
        </p>
      </div>

      <!-- Back button -->
      <div class="text-center pt-4">
        <button
          @click="$emit('close')"
          class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Back to Dashboard
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineEmits(['close']);
</script>
