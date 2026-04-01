import flagsmith from '@flagsmith/flagsmith';
import { ref } from 'vue';

const isReady = ref(false);

export async function initFlagsmith() {
  const environmentID = import.meta.env.VITE_FLAGSMITH_ENVIRONMENT_ID;
  if (!environmentID) {
    console.warn('Flagsmith: VITE_FLAGSMITH_ENVIRONMENT_ID not set, all flags will use defaults');
    return;
  }
  try {
    await flagsmith.init({ environmentID });
    isReady.value = true;
  } catch (err) {
    console.warn('Flagsmith: failed to initialise, all flags will use defaults', err);
  }
}

export function isFeatureEnabled(flagName, fallback = true) {
  if (!isReady.value) return fallback;
  return flagsmith.hasFeature(flagName, { fallback });
}
