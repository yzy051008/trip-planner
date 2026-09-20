<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { deleteHistory, fetchHistory, fetchHistoryDetail } from '@/services/api'
import type { HistorySummary } from '@/types'
const router = useRouter(); const records = ref<HistorySummary[]>([]); const total = ref(0); const page = ref(1); const city = ref(''); const loading = ref(false); let timer: ReturnType<typeof setTimeout> | undefined
const load = async () => { loading.value = true; try { const response = await fetchHistory(page.value, 9, city.value.trim()); records.value = response.data; total.value = response.total } catch (error: any) { message.error(error.message) } finally { loading.value = false } }
const search = () => { if (timer) clearTimeout(timer); timer = setTimeout(() => { page.value = 1; load() }, 400) }
const view = async (id: number) => { try { const response = await fetchHistoryDetail(id); sessionStorage.setItem('tripPlan', JSON.stringify(response.data.plan)); sessionStorage.setItem('tripPlanId', String(id)); router.push('/result') } catch (error: any) { message.error(error.message) } }
const remove = (record: HistorySummary) => Modal.confirm({ title: '删除这段旅程？', content: '删除后无法恢复，请确认。', okText: '删除', cancelText: '取消', okType: 'danger', onOk: async () => { await deleteHistory(record.id); message.success('已删除'); if (records.value.length === 1 && page.value > 1) page.value--; await load() } })
onMounted(load)
</script>
<template>
  <main class="history-page page-container"><div class="history-heading"><div><div class="eyebrow">YOUR JOURNEY ARCHIVE</div><h1>我的行程</h1><p>每一次出发，都是一页值得收藏的故事。</p></div><button class="primary-small" type="button" @click="router.push('/')">＋ 新建行程</button></div><div class="history-tools"><a-input v-model:value="city" placeholder="搜索城市" allow-clear @input="search"><template #prefix>⌕</template></a-input><span class="muted">共 {{ total }} 段旅程</span></div><a-spin :spinning="loading"><div v-if="records.length" class="history-grid"><article v-for="record in records" :key="record.id" class="history-card paper-card"><div class="archive-number">NO. {{ String(record.id).padStart(3, '0') }}</div><div class="eyebrow">{{ record.start_date }} — {{ record.end_date }}</div><h2>{{ record.city }}</h2><p>{{ record.travel_days }} 天 · {{ record.transportation }} · {{ record.accommodation }}</p><div class="tag-line"><span v-for="tag in record.preferences" :key="tag">{{ tag }}</span></div><div class="history-actions"><button class="text-button" type="button" @click="remove(record)">删除</button><button class="primary-small" type="button" @click="view(record.id)">查看行程 →</button></div></article></div><div v-else class="paper-card empty-card"><div class="empty-icon">◎</div><h2>还没有旅行记录</h2><p>下一段故事，从今天开始。</p><button class="primary-small" type="button" @click="router.push('/')">开始规划</button></div></a-spin><a-pagination v-if="total > 9" v-model:current="page" :total="total" :page-size="9" class="pagination" @change="load" /></main>
</template>
