<template>
  <div class="statusbar">
    <b>{{ clock.text }}</b>
    <span class="sb-r">
      <svg width="17" height="11" viewBox="0 0 17 11" fill="currentColor" aria-hidden="true"><rect x="0" y="7" width="3" height="4" rx="1" /><rect x="4.5" y="5" width="3" height="6" rx="1" /><rect x="9" y="2.5" width="3" height="8.5" rx="1" /><rect x="13.5" y="0" width="3" height="11" rx="1" opacity=".35" /></svg>
      <svg width="16" height="11" viewBox="0 0 16 12" fill="none" aria-hidden="true"><path d="M1 4.2a10.5 10.5 0 0 1 14 0" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" /><path d="M3.9 7.1a6.4 6.4 0 0 1 8.2 0" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" /><circle cx="8" cy="10.2" r="1.2" fill="currentColor" /></svg>
      <svg width="26" height="12" viewBox="0 0 26 12" fill="none" aria-hidden="true"><rect x=".6" y=".6" width="21" height="10.8" rx="3.2" stroke="currentColor" stroke-opacity=".38" stroke-width="1.1" /><rect x="2.2" y="2.2" width="15.6" height="7.6" rx="2" fill="currentColor" /><path d="M23.4 4.3v3.4a2 2 0 0 0 0-3.4Z" fill="currentColor" fill-opacity=".4" /></svg>
    </span>
  </div>
</template>

<script setup>
import { useClock } from '../composables/useCove.js';
const clock = useClock();
</script>
