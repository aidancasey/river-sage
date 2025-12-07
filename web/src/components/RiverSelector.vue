<template>
  <div class="mb-8 flex justify-center">
    <div class="relative inline-block w-full max-w-md">
      <label for="river-select" class="block text-sm font-medium text-gray-700 mb-2 text-center">
        Select River
      </label>
      <select
        id="river-select"
        v-model="localSelectedRiver"
        @change="$emit('select-river', localSelectedRiver)"
        class="block w-full px-4 py-3 pr-10 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 rounded-lg shadow-sm bg-white cursor-pointer"
      >
        <option v-for="river in rivers" :key="river.id" :value="river.id">
          {{ river.icon }} {{ river.name }} ({{ river.stationCount }} station{{ river.stationCount > 1 ? 's' : '' }})
        </option>
      </select>
      <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 pt-7 text-gray-700">
        <svg class="fill-current h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
          <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" />
        </svg>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';

const props = defineProps({
  selectedRiver: {
    type: String,
    required: true,
  },
  rivers: {
    type: Array,
    required: true,
  },
});

const emit = defineEmits(['select-river']);

// Local state to track the selected river
const localSelectedRiver = ref(props.selectedRiver);

// Watch for external changes to selectedRiver prop
watch(() => props.selectedRiver, (newValue) => {
  localSelectedRiver.value = newValue;
});
</script>

<style scoped>
select {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
}
</style>
