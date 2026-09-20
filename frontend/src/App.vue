<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="app-shell">
    <header class="site-header">
      <RouterLink to="/" class="brand">
        <span class="brand-mark">漫</span>
        <span><strong>漫游计划</strong><small>AI JOURNEY STUDIO</small></span>
      </RouterLink>
      <nav class="site-nav">
        <RouterLink to="/">开始规划</RouterLink>
        <RouterLink to="/history">我的行程</RouterLink>
      </nav>
    </header>
    <RouterView />
  </div>
</template>
