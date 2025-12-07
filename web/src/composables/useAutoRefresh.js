import { onMounted, onUnmounted, ref } from 'vue';

/**
 * Composable for automatic data refresh
 * @param {Function} callback - Function to call on refresh
 * @param {number} intervalMs - Refresh interval in milliseconds (default: 15 minutes)
 * @returns {Object} - Object with pause/resume controls and last refresh time
 */
export function useAutoRefresh(callback, intervalMs = 15 * 60 * 1000) {
  const intervalId = ref(null);
  const isPaused = ref(false);
  const lastRefreshTime = ref(new Date());

  const start = () => {
    if (intervalId.value) return;

    intervalId.value = setInterval(async () => {
      if (!isPaused.value) {
        await callback();
        lastRefreshTime.value = new Date();
      }
    }, intervalMs);
  };

  const stop = () => {
    if (intervalId.value) {
      clearInterval(intervalId.value);
      intervalId.value = null;
    }
  };

  const pause = () => {
    isPaused.value = true;
  };

  const resume = () => {
    isPaused.value = false;
  };

  const restart = () => {
    stop();
    start();
  };

  onMounted(() => {
    start();
  });

  onUnmounted(() => {
    stop();
  });

  return {
    pause,
    resume,
    restart,
    lastRefreshTime,
    isPaused,
  };
}
