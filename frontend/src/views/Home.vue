<script setup lang="ts">
import { onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import TripForm from '@/components/TripForm.vue'
import { createPlanningSession } from '@/services/api'
import type { TripRequest } from '@/types'
import { getProgressForElapsed, PROGRESS_STAGES, type ProgressStage } from '@/utils/progress'
const router = useRouter(); const loading = ref(false)
const progress = ref(8); const progressStage = ref<ProgressStage>(PROGRESS_STAGES[0]); let progressTimer: ReturnType<typeof setInterval> | undefined; let progressStartedAt = 0
const startProgress = () => { progressStartedAt = Date.now(); progress.value = 8; progressStage.value = PROGRESS_STAGES[0]; progressTimer = setInterval(() => { const current = getProgressForElapsed(Date.now() - progressStartedAt); progress.value = current.percent; progressStage.value = current.stage }, 500) }
const stopProgress = () => { if (progressTimer) clearInterval(progressTimer); progressTimer = undefined }
const submit = async (request: TripRequest) => { loading.value = true; startProgress(); try { const response = await createPlanningSession(request); progress.value = 100; if (!response.data) throw new Error(response.message || '没有返回临时计划'); sessionStorage.setItem('tripPlan', JSON.stringify(response.data)); sessionStorage.setItem('tripReview', JSON.stringify(response.review || null)); sessionStorage.setItem('tripRequest', JSON.stringify(request)); sessionStorage.setItem('tripSessionId', response.session_id); sessionStorage.setItem('tripDraftVersion', String(response.draft_version)); sessionStorage.setItem('tripSessionStatus', response.status); sessionStorage.removeItem('tripPlanId'); await new Promise(resolve => setTimeout(resolve, 220)); await router.push('/result') } catch (error: any) { message.error(error.message || '生成临时计划失败') } finally { stopProgress(); loading.value = false } }
onUnmounted(stopProgress)
</script>
<template>
  <main class="home-page page-container"><section class="hero-copy"><div class="eyebrow">A LITTLE MORE WANDERLUST</div><h1>把下一段旅程，<em>交给风。</em></h1><p>告诉我你想去哪里，剩下的交给 AI。把零散的愿望，变成一条刚刚好的路线。</p><div class="hero-stamp">✦ <span>你的专属漫游策划师</span></div></section><section class="form-card paper-card"><div class="form-intro"><span class="step-pill">01 / 规划出发</span><h2>这一次，想去哪里？</h2><p>填入偏好，我们会为你编排一份有节奏的旅程。</p></div><TripForm @submit="submit" /><div v-if="loading" class="loading-overlay"><div class="progress-orbit"><a-spin size="large" /><strong>{{ progress }}%</strong></div><div class="progress-track"><span :style="{ width: `${progress}%` }"></span></div><strong class="progress-label">{{ progressStage.label }}</strong><small>AI 正在为你整理一段刚刚好的旅程</small></div></section></main>
</template>
<style scoped>
.progress-orbit{position:relative;display:grid;place-items:center;width:76px;height:76px;color:var(--orange)}
.progress-orbit strong{position:absolute;font:16px Georgia,serif}
.progress-track{width:min(320px,82%);height:7px;background:#e8e1d4;border-radius:10px;overflow:hidden;margin-top:4px}
.progress-track span{display:block;height:100%;background:var(--orange);border-radius:inherit;transition:width .45s ease}
.progress-label{font-size:15px;color:var(--ink);margin-top:2px}
.loading-overlay small{color:var(--muted);font-size:11px}
</style>
