<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import type { PlanningMessage, ReviewResult, TripPlan } from '@/types'
import { confirmPlanningSession, fetchPlanningSession, sendPlanningMessage, updateHistory } from '@/services/api'
import TripSummary from '@/components/TripSummary.vue'
import DayItinerary from '@/components/DayItinerary.vue'
import MapPanel from '@/components/MapPanel.vue'

const router = useRouter()
const raw = sessionStorage.getItem('tripPlan')
const sessionId = ref(sessionStorage.getItem('tripSessionId') || '')
const draftVersion = ref(Number(sessionStorage.getItem('tripDraftVersion') || 1))
const sessionStatus = ref(sessionStorage.getItem('tripSessionStatus') || 'waiting_confirmation')
const recordId = ref(Number(sessionStorage.getItem('tripPlanId') || 0))
const plan = ref<TripPlan | null>(raw ? JSON.parse(raw) : null)
const review = ref<ReviewResult | null>(sessionStorage.getItem('tripReview') ? JSON.parse(sessionStorage.getItem('tripReview')!) : null)
const messages = ref<PlanningMessage[]>([
  { role: 'assistant', content: '这是一份临时计划。你可以继续告诉我想调整的地方，满意后再确认保存。' },
])
const changes = ref<string[]>([])
const chatInput = ref('')
const chatLoading = ref(false)
const editMode = ref(false)
const saving = ref(false)
const snapshot = ref<TripPlan | null>(null)

const isDraft = computed(() => Boolean(sessionId.value) && sessionStatus.value !== 'confirmed')
const statusLabel = computed(() => sessionStatus.value === 'confirmed' ? '已正式保存' : sessionStatus.value === 'replanning' ? '正在重新规划' : sessionStatus.value === 'failed' ? '本轮调整失败，仍保留旧计划' : '临时计划 · 等待确认')
const budget = computed(() => plan.value?.budget)

const persistDraft = () => {
  if (!plan.value) return
  sessionStorage.setItem('tripPlan', JSON.stringify(plan.value))
  sessionStorage.setItem('tripReview', JSON.stringify(review.value))
  sessionStorage.setItem('tripDraftVersion', String(draftVersion.value))
  sessionStorage.setItem('tripSessionStatus', sessionStatus.value)
}

onMounted(async () => {
  if (!sessionId.value) return
  try {
    const response = await fetchPlanningSession(sessionId.value)
    if (response.data) plan.value = response.data
    draftVersion.value = response.draft_version
    sessionStatus.value = response.status
    review.value = response.review || null
    changes.value = response.changes || []
    if (response.messages?.length) messages.value = response.messages
    persistDraft()
  } catch {
    // The current draft is already available locally; keep it usable if the process restarted.
  }
})

const startEdit = () => { snapshot.value = plan.value ? JSON.parse(JSON.stringify(plan.value)) : null; editMode.value = true }
const cancelEdit = () => { if (snapshot.value) plan.value = snapshot.value; editMode.value = false }
const updateDay = (segmentIndex: number, dayIndex: number, day: TripPlan['segments'][number]['days'][number]) => { if (plan.value) { const segment = plan.value.segments[segmentIndex]; segment.days = segment.days.map((item, i) => i === dayIndex ? day : item) } }
const updateBudget = (key: keyof NonNullable<TripPlan['budget']>, value: string) => { if (plan.value?.budget) { plan.value.budget = { ...plan.value.budget, [key]: Number(value) }; plan.value.budget.total = plan.value.budget.total_attractions + plan.value.budget.total_hotels + plan.value.budget.total_meals + plan.value.budget.total_transportation } }

const sendMessage = async () => {
  const content = chatInput.value.trim()
  if (!content || !sessionId.value || chatLoading.value) return
  chatInput.value = ''
  messages.value.push({ role: 'user', content })
  chatLoading.value = true
  sessionStatus.value = 'replanning'
  try {
    const response = await sendPlanningMessage(sessionId.value, { message: content, draft_version: draftVersion.value })
    messages.value.push({ role: 'assistant', content: response.message })
    sessionStatus.value = response.status || sessionStatus.value
    if (response.data && response.plan_changed) {
      plan.value = response.data
      draftVersion.value = response.draft_version || draftVersion.value
      review.value = response.review || null
      changes.value = response.changes || []
      persistDraft()
    }
    if (response.type === 'error') message.warning(response.message)
  } catch (error: any) {
    sessionStatus.value = 'failed'
    messages.value.push({ role: 'assistant', content: error.message || '本次调整失败，已保留上一版计划。' })
    message.error(error.message || '提交修改需求失败')
  } finally { chatLoading.value = false }
}

const confirmPlan = () => {
  Modal.confirm({
    title: '确认这份旅行计划？',
    content: '确认后，当前版本会保存到历史行程中。',
    okText: '确认保存', cancelText: '继续修改',
    onOk: async () => {
      if (!plan.value) return
      saving.value = true
      try {
        if (sessionId.value) {
          const response = await confirmPlanningSession(sessionId.value, { draft_version: draftVersion.value })
          sessionStatus.value = response.status
          recordId.value = response.record_id || 0
          sessionStorage.setItem('tripSessionStatus', sessionStatus.value)
          if (recordId.value) sessionStorage.setItem('tripPlanId', String(recordId.value))
          message.success(response.message || '计划已保存')
        } else if (recordId.value) {
          await updateHistory(recordId.value, plan.value)
          message.success('行程已保存')
        }
      } catch (error: any) { message.error(error.message || '确认计划失败') } finally { saving.value = false }
    },
  })
}

const saveLegacyEdit = async () => {
  if (!plan.value || !recordId.value) { message.warning('请先确认临时计划'); return }
  saving.value = true
  try { await updateHistory(recordId.value, plan.value); editMode.value = false; message.success('行程已保存') } catch (error: any) { message.error(error.message || '保存行程失败') } finally { saving.value = false }
}
</script>

<template>
  <main v-if="plan" class="result-page page-container">
    <div class="result-toolbar">
      <button class="back-link" type="button" @click="router.push('/')">← 返回规划</button>
      <div class="result-actions">
        <span class="draft-status">{{ statusLabel }} · v{{ draftVersion }}</span>
        <button v-if="!editMode && !isDraft" class="outline-button" type="button" @click="startEdit">编辑行程</button>
        <button v-if="editMode" class="outline-button" type="button" @click="cancelEdit">取消</button>
        <button v-if="editMode" class="primary-small" type="button" :disabled="saving" @click="saveLegacyEdit">{{ saving ? '保存中…' : '保存修改' }}</button>
        <button v-if="isDraft" class="primary-small" type="button" :disabled="saving || chatLoading" @click="confirmPlan">{{ saving ? '保存中…' : '确认计划' }}</button>
      </div>
    </div>
    <TripSummary :key="`summary-${draftVersion}`" :plan="plan" />
    <div class="result-layout">
      <div>
        <div class="section-title-row"><div><div class="eyebrow">THE ITINERARY</div><h2>每天，都值得期待</h2></div><span class="edit-tip" v-if="editMode">编辑模式已开启</span></div>
        <template v-for="(segment, segmentIndex) in plan.segments" :key="segment.city">
          <div class="segment-heading"><div class="eyebrow">CITY SEGMENT {{ segmentIndex + 1 }}</div><h2>{{ segment.city }}</h2><p>{{ segment.start_date }} 至 {{ segment.end_date }}</p><div v-if="segment.transport_from_previous" class="segment-transport">{{ segment.transport_from_previous.from_city }} → {{ segment.transport_from_previous.to_city }} · {{ segment.transport_from_previous.method }}</div></div>
          <DayItinerary v-for="(day, dayIndex) in segment.days" :key="`${segment.city}-${day.day_index}`" :day="day" :edit-mode="editMode" @update="updateDay(segmentIndex, dayIndex, $event)" />
        </template>
      </div>
      <aside class="result-aside">
        <div v-if="isDraft" class="aside-card chat-card">
          <div class="eyebrow">AI PLANNING PARTNER</div><h3>继续调整这份计划</h3><p class="chat-hint">例如：少安排一个景点、换成地铁附近的酒店、预算控制在 2000 元以内。</p>
          <div class="chat-messages"><div v-for="(item, index) in messages" :key="`${item.role}-${index}`" class="chat-message" :class="`chat-${item.role}`"><span>{{ item.role === 'user' ? '你' : 'Agent' }}</span><p>{{ item.content }}</p></div><div v-if="chatLoading" class="chat-message chat-assistant"><span>Agent</span><p>正在重新规划…</p></div></div>
          <div v-if="changes.length" class="change-summary"><strong>本轮修改</strong><span v-for="item in changes" :key="item">{{ item }}</span></div>
          <form class="chat-form" @submit.prevent="sendMessage"><textarea v-model="chatInput" :disabled="chatLoading" rows="3" placeholder="告诉 Agent 你还想怎么调整…"></textarea><button class="primary-small" type="submit" :disabled="chatLoading || !chatInput.trim()">{{ chatLoading ? '规划中…' : '发送修改' }}</button></form>
        </div>
        <div class="aside-card paper-card"><div class="eyebrow">ROUTE MAP</div><h3>一路向前</h3><MapPanel :days="plan.segments.flatMap(segment => segment.days)" /></div>
        <div v-if="plan.segments.some(segment => segment.weather_info?.length)" class="aside-card weather-card"><div class="eyebrow">WEATHER NOTES</div><h3>天气小贴士</h3><template v-for="segment in plan.segments" :key="segment.city"><div class="segment-weather-label">{{ segment.city }}</div><div v-for="weather in segment.weather_info" :key="`${segment.city}-${weather.date}`" class="weather-row"><span>{{ weather.date.slice(5) }}</span><strong>{{ weather.forecast_available === false ? '暂无预报' : weather.day_weather }}</strong><span>{{ weather.forecast_available === false ? '—' : `${weather.day_temp}° / ${weather.night_temp}°` }}</span></div></template></div>
        <div class="aside-card budget-card"><div class="eyebrow">ESTIMATED BUDGET</div><h3>预算预览</h3><div v-if="budget"><div class="budget-row"><span>门票</span><input v-if="editMode" class="edit-input budget-input" type="number" :value="budget.total_attractions" @input="updateBudget('total_attractions', ($event.target as HTMLInputElement).value)" /><strong v-else>¥{{ budget.total_attractions }}</strong></div><div class="budget-row"><span>住宿</span><input v-if="editMode" class="edit-input budget-input" type="number" :value="budget.total_hotels" @input="updateBudget('total_hotels', ($event.target as HTMLInputElement).value)" /><strong v-else>¥{{ budget.total_hotels }}</strong></div><div class="budget-row"><span>餐饮</span><input v-if="editMode" class="edit-input budget-input" type="number" :value="budget.total_meals" @input="updateBudget('total_meals', ($event.target as HTMLInputElement).value)" /><strong v-else>¥{{ budget.total_meals }}</strong></div><div class="budget-total"><span>合计</span><strong>¥{{ budget.total }}</strong></div></div><span v-else class="muted">暂无预算信息</span></div>
      </aside>
    </div>
  </main>
  <main v-else class="empty-page page-container"><div class="paper-card empty-card"><div class="empty-icon">✈</div><h2>还没有打开的行程</h2><p>先去规划一段属于你的旅程吧。</p><button class="primary-small" type="button" @click="router.push('/')">开始规划</button></div></main>
</template>

<style scoped>
.result-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;justify-content:flex-end}.draft-status{font-size:11px;color:var(--muted)}
.chat-card{background:#f5f1e9;border:1px solid var(--line)}.chat-card h3{margin:6px 0}.chat-hint{font-size:12px;line-height:1.6;color:var(--muted)}.chat-messages{display:flex;flex-direction:column;gap:9px;max-height:340px;overflow:auto;margin:15px 0}.chat-message{border-radius:12px;padding:9px 11px;font-size:12px;line-height:1.6}.chat-message span{display:block;font-size:10px;color:var(--muted);margin-bottom:3px}.chat-message p{margin:0}.chat-assistant{background:#fff}.chat-user{background:#dce5d5;align-self:flex-end;max-width:90%}.chat-form{display:flex;flex-direction:column;gap:8px}.chat-form textarea{width:100%;box-sizing:border-box;border:1px solid var(--line);border-radius:10px;padding:9px;background:#fff;resize:vertical;font:inherit;font-size:12px}.chat-form button{align-self:flex-end}
.change-summary{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0;font-size:11px}.change-summary strong{width:100%;color:var(--muted)}.change-summary span{background:#fff;border-radius:999px;padding:5px 8px}
@media (max-width:760px){.result-actions{width:100%;justify-content:flex-start}.draft-status{width:100%}.chat-messages{max-height:none}}
</style>
