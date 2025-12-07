<template>
  <div class="mb-8">
    <div class="flex flex-wrap gap-3 justify-center">
      <button
        v-for="river in rivers"
        :key="river.id"
        @click="$emit('select-river', river.id)"
        class="px-6 py-3 rounded-lg font-semibold transition-all duration-200 shadow-sm"
        :class="
          selectedRiver === river.id
            ? 'bg-blue-600 text-white shadow-md transform scale-105'
            : 'bg-white text-gray-700 hover:bg-gray-50 hover:shadow'
        "
      >
        <div class="flex items-center gap-2">
          <span class="text-2xl">{{ river.icon }}</span>
          <div class="text-left">
            <div class="text-sm font-bold">{{ river.name }}</div>
            <div class="text-xs opacity-75">{{ river.stationCount }} station{{ river.stationCount > 1 ? 's' : '' }}</div>
          </div>
        </div>
      </button>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue';

defineProps({
  selectedRiver: {
    type: String,
    required: true,
  },
  rivers: {
    type: Array,
    required: true,
  },
});

defineEmits(['select-river']);
</script>

<style scoped>
button {
  min-width: 140px;
}
</style>
