<script setup lang="ts">
import { computed } from 'vue'
import type { ReviewResult, TripPlan, TripRequest } from '@/types'
const props = defineProps<{ plan: TripPlan }>()
const attractionCount = computed(() => props.plan.days.reduce((sum, day) => sum + day.attractions.length, 0))
const money = (value?: number) => `¥${(value || 0).toLocaleString()}`
const reviewRaw = sessionStorage.getItem('tripReview')
const requestRaw = sessionStorage.getItem('tripRequest')
const review = reviewRaw ? JSON.parse(reviewRaw) as ReviewResult : null
const request = requestRaw ? JSON.parse(requestRaw) as Partial<TripRequest> : {}
const travelerCount = request.traveler_count || 1
const reviewClass = review?.level === 'A' ? 'review-good' : review?.level === 'B' ? 'review-warn' : 'review-danger'
</script>
<template>
  <section class="summary-card paper-card">
    <div class="eyebrow">YOUR NEXT ESCAPE</div><h1>{{ plan.city }} · 漫游计划</h1><p>{{ plan.start_date }} — {{ plan.end_date }}</p>
    <div class="summary-stats"><div><strong>{{ plan.days.length }}</strong><span>天行程</span></div><div><strong>{{ attractionCount }}</strong><span>个目的地</span></div><div><strong>{{ money(plan.budget?.total) }}</strong><span>预估预算</span></div></div>
    <div class="suggestion" v-if="plan.overall_suggestions"><span>✦</span>{{ plan.overall_suggestions }}</div>
    <div v-if="review" class="review-summary-box" :class="reviewClass"><div class="review-summary-heading"><div><div class="eyebrow">REQUEST REVIEW</div><h2>需求满足情况</h2></div><strong class="review-level">{{ review.level }} 级</strong></div><p class="review-summary-text">{{ review.summary }}</p><div class="review-chips"><span v-if="review.hard_rule_passed">✓ 硬约束已满足</span><span v-else>! 部分硬约束未满足</span><span v-if="review.semantic_rule_passed">✓ 偏好已检查</span><span>已审查 {{ review.retry_count }} 次</span><span>人均预算 {{ money(Math.round((plan.budget?.total || 0) / travelerCount)) }}</span><span v-if="request.budget_limit != null">上限 {{ money(request.budget_limit) }}</span></div><div v-if="review.issues.length" class="review-issues"><strong>需要注意</strong><span v-for="issue in review.issues" :key="issue">{{ issue }}</span></div><div v-if="review.suggestions.length" class="review-issues"><strong>调整建议</strong><span v-for="suggestion in review.suggestions" :key="suggestion">{{ suggestion }}</span></div></div>
  </section>
</template>
<style scoped>
.review-summary-box { border-top: 1px solid var(--line); margin-top: 22px; padding-top: 18px; }
.review-summary-box.review-good { color: var(--ink); }
.review-summary-box.review-warn { color: #88633d; }
.review-summary-box.review-danger { color: #9a594c; }
.review-summary-heading { display: flex; align-items: center; justify-content: space-between; }
.review-summary-heading h2 { font: 22px Georgia, serif; margin: 7px 0 0; }
.review-level { border: 1px solid currentColor; border-radius: 999px; padding: 6px 12px; font: 16px Georgia, serif; }
.review-summary-text { margin: 12px 0; font-size: 13px; line-height: 1.7; }
.review-chips { display: flex; flex-wrap: wrap; gap: 7px; }
.review-chips span { background: rgba(220,229,213,.65); border-radius: 999px; padding: 5px 9px; font-size: 11px; }
.review-issues { display: flex; flex-wrap: wrap; gap: 6px 12px; margin-top: 12px; font-size: 12px; line-height: 1.6; }
.review-issues strong { width: 100%; font-size: 11px; color: var(--muted); }
.review-issues span::before { content: '•'; color: var(--orange); margin-right: 5px; }
</style>
