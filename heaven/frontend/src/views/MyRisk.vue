<template>
  <div class="disabled-view">
    <p>Redirecting to HRMS Desk…</p>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'

onMounted(() => {
  // Employee-facing views are disabled — redirect immediately to HRMS Desk
  window.location.href = '/app'
})
</script>
