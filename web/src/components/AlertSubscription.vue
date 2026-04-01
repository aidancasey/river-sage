<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
    <div class="flex items-center gap-2 mb-4">
      <span class="text-2xl">📱</span>
      <h3 class="text-lg font-semibold text-gray-800">Flow Alerts</h3>
    </div>

    <!-- Coming soon banner -->
    <div class="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-4">
      <svg class="w-4 h-4 text-amber-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
      </svg>
      <p class="text-xs text-amber-800 font-medium">This feature is currently in development and will be released soon.</p>
    </div>

    <p class="text-sm text-gray-600 mb-4">
      Get a WhatsApp message when the Inniscarra flow changes by more than 2 m³/s.
      Opt in each day you plan to go fishing.
    </p>

    <!-- Phone number input -->
    <div v-if="!phoneStored" class="mb-4">
      <label class="block text-sm font-medium text-gray-700 mb-1">Irish mobile number</label>
      <div class="flex gap-2">
        <input
          v-model="phoneInput"
          type="tel"
          placeholder="083 123 4567"
          maxlength="15"
          class="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          @keyup.enter="savePhone"
        />
        <button
          @click="savePhone"
          :disabled="saving"
          class="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {{ saving ? 'Saving…' : 'Save' }}
        </button>
      </div>
      <p v-if="registerError" class="text-xs text-red-600 mt-1">{{ registerError }}</p>
    </div>

    <!-- Opt-in section (shown once phone is saved) -->
    <div v-if="phoneStored">
      <div class="flex items-center justify-between mb-3">
        <span class="text-sm text-gray-600">{{ maskedPhone }}</span>
        <button
          @click="changePhone"
          class="text-xs text-blue-600 hover:underline"
        >
          Change number
        </button>
      </div>

      <!-- Opt-in toggle -->
      <button
        @click="toggleOptIn"
        :disabled="toggling"
        :class="[
          'w-full py-3 rounded-lg font-medium text-sm transition-colors',
          optedInToday
            ? 'bg-green-100 text-green-800 border-2 border-green-400 hover:bg-green-200'
            : 'bg-blue-600 text-white hover:bg-blue-700'
        ]"
      >
        <span v-if="toggling">Updating…</span>
        <span v-else-if="optedInToday">Alerts active today ✓</span>
        <span v-else>Alert me today</span>
      </button>

      <p v-if="optedInToday" class="text-xs text-gray-500 mt-2 text-center">
        You'll receive a WhatsApp message if the flow changes by &gt;2 m³/s today.
        Opt-in resets at midnight.
      </p>

      <p v-if="optInError" class="text-xs text-red-600 mt-2 text-center">{{ optInError }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { registerPhone, optInToday, getAlertStatus } from '../services/api.js';

const STORAGE_KEY = 'river_guru_alert_phone';

const phoneInput = ref('');
const phoneStored = ref(false);
const storedPhone = ref('');
const optedInToday = ref(false);

const saving = ref(false);
const toggling = ref(false);
const registerError = ref('');
const optInError = ref('');

const maskedPhone = computed(() => {
  if (!storedPhone.value) return '';
  const p = storedPhone.value;
  return p.slice(0, 6) + '***' + p.slice(-3);
});

onMounted(async () => {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {
    storedPhone.value = saved;
    phoneStored.value = true;
    await checkStatus();
  }
});

async function checkStatus() {
  try {
    const result = await getAlertStatus(storedPhone.value);
    optedInToday.value = result.opted_in;
  } catch {
    // Not critical — status check failure shouldn't break the UI
    optedInToday.value = false;
  }
}

async function savePhone() {
  registerError.value = '';
  const raw = phoneInput.value.trim();
  if (!raw) return;

  saving.value = true;
  try {
    const result = await registerPhone(raw);
    localStorage.setItem(STORAGE_KEY, result.phone);
    storedPhone.value = result.phone;
    phoneStored.value = true;
    phoneInput.value = '';
    await checkStatus();
  } catch (err) {
    registerError.value = err.message || 'Could not register number. Use an Irish mobile (083–089).';
  } finally {
    saving.value = false;
  }
}

function changePhone() {
  phoneStored.value = false;
  storedPhone.value = '';
  optedInToday.value = false;
  localStorage.removeItem(STORAGE_KEY);
}

async function toggleOptIn() {
  if (optedInToday.value) return; // already opted in — nothing to undo
  optInError.value = '';
  toggling.value = true;
  try {
    await optInToday(storedPhone.value);
    optedInToday.value = true;
  } catch (err) {
    optInError.value = err.message || 'Could not opt in. Please try again.';
  } finally {
    toggling.value = false;
  }
}
</script>
