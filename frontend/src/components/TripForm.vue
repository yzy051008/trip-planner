<script setup lang="ts">
import { computed, reactive } from 'vue'
import { message } from 'ant-design-vue'
import dayjs, { type Dayjs } from 'dayjs'
import type { TripRequest } from '@/types'
import { normalizeTripRequest } from '@/utils/tripRequest'

const emit = defineEmits<{ submit: [TripRequest] }>()
const form = reactive({ destinations: [{ city: '', start_date: null as Dayjs | null, end_date: null as Dayjs | null }], transportation: '公共交通', accommodation: '舒适型酒店', preferences: [] as string[], free_text_input: '', traveler_count: 1 as number | string, budget_limit: '' as number | string })
const cities = ['北京', '上海', '广州', '深圳', '成都', '杭州']
const days = computed(() => form.destinations.reduce((total, item) => total + (item.start_date && item.end_date ? item.end_date.diff(item.start_date, 'day') + 1 : 0), 0))
const disabledDate = (current: Dayjs) => current.isBefore(dayjs().startOf('day'))
const addDestination = () => form.destinations.push({ city: '', start_date: null, end_date: null })
const removeDestination = (index: number) => { if (form.destinations.length > 1) form.destinations.splice(index, 1) }
const submit = () => {
  if (form.destinations.some(item => !item.city.trim())) { message.warning('请填写所有目的地城市'); return }
  if (form.destinations.some(item => !item.start_date || !item.end_date)) { message.warning('请完整选择每个城市的日期'); return }
  if (form.destinations.some(item => item.start_date && item.end_date && item.end_date.isBefore(item.start_date, 'day'))) { message.warning('结束日期不能早于开始日期'); return }
  if (form.destinations.some((item, index) => {
    const previousEnd = index > 0 ? form.destinations[index - 1].end_date : null
    return Boolean(item.start_date && previousEnd && !item.start_date.isSame(previousEnd, 'day') && !item.start_date.isSame(previousEnd.add(1, 'day'), 'day'))
  })) { message.warning('相邻城市的日期需要连续，或共享一天作为交通日'); return }
  if (Number(form.traveler_count) < 1) { message.warning('出行人数至少为 1 人'); return }
  if (form.budget_limit !== '' && Number(form.budget_limit) < 0) { message.warning('预算不能为负数'); return }
  emit('submit', normalizeTripRequest({ destinations: form.destinations.map(item => ({ city: item.city.trim(), start_date: item.start_date!.format('YYYY-MM-DD'), end_date: item.end_date!.format('YYYY-MM-DD') })), transportation: form.transportation, accommodation: form.accommodation, preferences: form.preferences, free_text_input: form.free_text_input.trim(), traveler_count: form.traveler_count, budget_limit: form.budget_limit }))
}
const chooseCity = (city: string) => { form.destinations[0].city = city }
</script>

<template>
  <a-form layout="vertical" @finish="submit">
    <div v-for="(destination, index) in form.destinations" :key="index" class="destination-block">
      <div class="field-row"><a-form-item :label="`目的地 ${index + 1}`" required class="field-wide"><a-input v-model:value="destination.city" size="large" placeholder="输入城市，例如：北京" /></a-form-item><button v-if="form.destinations.length > 1" type="button" class="remove-destination" @click="removeDestination(index)">移除</button></div>
      <div v-if="index === 0" class="quick-cities"><span>想去：</span><button v-for="city in cities" :key="city" type="button" @click="chooseCity(city)">{{ city }}</button></div>
      <div class="field-row"><a-form-item label="开始日期" required class="field-half"><a-date-picker v-model:value="destination.start_date" size="large" :disabled-date="disabledDate" style="width:100%" /></a-form-item><a-form-item label="结束日期" required class="field-half"><a-date-picker v-model:value="destination.end_date" size="large" :disabled-date="(d: Dayjs) => disabledDate(d) || !!destination.start_date && d.isBefore(destination.start_date, 'day')" style="width:100%" /></a-form-item></div>
    </div>
    <div class="destination-actions"><button type="button" @click="addDestination">＋ 添加城市</button><span>共 {{ days || '—' }} 天</span></div>
    <div class="field-row">
      <a-form-item label="出行方式" class="field-half"><a-select v-model:value="form.transportation" size="large" style="width:100%"><a-select-option value="公共交通">公共交通</a-select-option><a-select-option value="自驾">自驾</a-select-option><a-select-option value="步行">步行</a-select-option><a-select-option value="混合">混合</a-select-option></a-select></a-form-item>
      <a-form-item label="住宿偏好" class="field-half"><a-select v-model:value="form.accommodation" size="large" style="width:100%"><a-select-option value="经济型酒店">经济型酒店</a-select-option><a-select-option value="舒适型酒店">舒适型酒店</a-select-option><a-select-option value="豪华酒店">豪华酒店</a-select-option><a-select-option value="民宿">民宿</a-select-option></a-select></a-form-item>
    </div>
    <div class="field-row">
      <a-form-item label="出行人数" class="field-half"><a-input-number v-model:value="form.traveler_count" :min="1" :precision="0" size="large" style="width:100%" addon-after="人" /></a-form-item>
      <a-form-item label="人均预算上限" class="field-half"><a-input-number v-model:value="form.budget_limit" :min="0" :precision="0" size="large" style="width:100%" placeholder="可选" addon-after="元" /></a-form-item>
    </div>
    <a-form-item label="旅行偏好"><a-checkbox-group v-model:value="form.preferences"><a-checkbox v-for="item in ['历史文化','自然风光','美食','购物','艺术','休闲']" :key="item" :value="item">{{ item }}</a-checkbox></a-checkbox-group></a-form-item>
    <a-form-item label="特别期待"><a-textarea v-model:value="form.free_text_input" :rows="3" placeholder="例如：想看升旗、需要无障碍设施、对海鲜过敏……" /></a-form-item>
    <a-button html-type="button" type="primary" size="large" block class="primary-action" @click="submit">生成我的漫游计划 <span>→</span></a-button>
  </a-form>
</template>
