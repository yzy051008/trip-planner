<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import type { DayPlan } from '@/types'
import { configureAmapSecurity, createAmapLoaderOptions } from '@/utils/amapConfig'
const props = defineProps<{ days: DayPlan[] }>()
const mapHost = ref<HTMLElement | null>(null)
const mapReady = ref(false)
const mapFailed = ref(false)
const mapError = ref('')
const amapKey = import.meta.env.VITE_AMAP_WEB_JS_KEY || import.meta.env.VITE_AMAP_KEY || ''
const securityJsCode = import.meta.env.VITE_AMAP_SECURITY_JS_CODE || ''
function formatMapError(error: unknown): string {
  if (error instanceof Error) return error.message
  if (typeof error === 'string') return error
  if (error && typeof error === 'object') {
    const detail = error as { info?: unknown; infocode?: unknown }
    if (detail.info || detail.infocode) {
      return [detail.info, detail.infocode && `错误码 ${detail.infocode}`].filter(Boolean).join('，')
    }
  }
  return '未知加载错误，请查看浏览器控制台'
}
onMounted(async () => {
  if (!amapKey) return
  try {
    configureAmapSecurity(window as unknown as Record<string, unknown>, securityJsCode)
    const AMap = await AMapLoader.load(createAmapLoaderOptions(amapKey))
    await nextTick()
    if (!mapHost.value) throw new Error('地图容器不存在')
    const points = props.days.flatMap(day => day.attractions).map(item => [item.location.longitude, item.location.latitude])
    const map = new AMap.Map(mapHost.value, { zoom: 11, center: points[0] || [116.397, 39.916] })
    points.forEach((point, index) => new AMap.Marker({ position: point, label: { content: String(index + 1), direction: 'top' }, map }))
    if (points.length > 1) new AMap.Polyline({ path: points, strokeColor: '#e8894a', strokeWeight: 4, strokeOpacity: 0.75, map })
    mapReady.value = true
  } catch (error) {
    mapFailed.value = true
    mapError.value = formatMapError(error)
    console.error('AMap initialization failed', error)
  }
})
</script>
<template>
  <div class="map-panel">
    <div v-if="amapKey && !mapFailed" ref="mapHost" class="real-map" :class="{ ready: mapReady }"><span v-if="!mapReady">地图加载中…</span></div>
    <div v-else class="route-fallback"><div v-for="day in days" :key="day.day_index" class="route-day"><span class="route-dot">{{ day.day_index + 1 }}</span><div><strong>第{{ day.day_index + 1 }}天 · {{ day.date }}</strong><p v-for="(place, index) in day.attractions" :key="index">{{ place.name }} <small>{{ place.location.latitude.toFixed(3) }}, {{ place.location.longitude.toFixed(3) }}</small></p></div></div><p v-if="!amapKey" class="muted map-hint">配置 VITE_AMAP_KEY 后可切换真实地图</p><p v-else class="muted map-hint">高德地图加载失败，请检查 JS Key、安全密钥和域名白名单<span v-if="mapError">（{{ mapError }}）</span></p></div>
  </div>
</template>
<style scoped>
.real-map {
  position: relative;
  width: 100%;
  overflow: hidden;
}
</style>
