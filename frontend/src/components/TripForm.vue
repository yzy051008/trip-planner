<script setup lang="ts">
import { computed, reactive } from 'vue'
import { message } from 'ant-design-vue'
import dayjs, { type Dayjs } from 'dayjs'
import type { TripRequest } from '@/types'
import { normalizeTripRequest } from '@/utils/tripRequest'

const emit = defineEmits<{ submit: [TripRequest] }>()
const form = reactive({ city: '', start_date: null as Dayjs | null, end_date: null as Dayjs | null, transportation: '公共交通', accommodation: '舒适型酒店', preferences: [] as string[], free_text_input: '', traveler_count: 1 as number | string, budget_limit: '' as number | string })
const cities = ['北京', '上海', '广州', '深圳', '成都', '杭州']
const days = computed(() => form.start_date && form.end_date ? form.end_date.diff(form.start_date, 'day') + 1 : 0)
const disabledDate = (current: Dayjs) => current.isBefore(dayjs().startOf('day'))
const submit = () => {
  if (!form.city.trim()) { message.warning('请先填写目的地城市'); return }
  if (!form.start_date || !form.end_date) { message.warning('请先选择出发日期和结束日期'); return }
  if (days.value < 1) { message.warning('结束日期不能早于出发日期'); return }
  if (Number(form.traveler_count) < 1) { message.warning('出行人数至少为 1 人'); return }
  if (form.budget_limit !== '' && Number(form.budget_limit) < 0) { message.warning('预算不能为负数'); return }
  emit('submit', normalizeTripRequest({ city: form.city.trim(), start_date: form.start_date.format('YYYY-MM-DD'), end_date: form.end_date.format('YYYY-MM-DD'), travel_days: days.value, transportation: form.transportation, accommodation: form.accommodation, preferences: form.preferences, free_text_input: form.free_text_input.trim(), traveler_count: form.traveler_count, budget_limit: form.budget_limit }))
}
const chooseCity = (city: string) => { form.city = city }
</script>

<template>
  <a-form layout="vertical" @finish="submit">
    <div class="field-row">
      <a-form-item label="目的地城市" required class="field-wide">
        <a-input v-model:value="form.city" size="large" placeholder="输入一个城市，例如：北京" />
      </a-form-item>
      <a-form-item label="旅行天数" class="days-badge">
        <div class="days-number">{{ days || '—' }}<small>天</small></div>
      </a-form-item>
    </div>
    <div class="quick-cities"><span>想去：</span><button v-for="city in cities" :key="city" type="button" @click="chooseCity(city)">{{ city }}</button></div>
    <div class="field-row">
      <a-form-item label="出发日期" required class="field-half"><a-date-picker v-model:value="form.start_date" size="large" :disabled-date="disabledDate" style="width:100%" /></a-form-item>
      <a-form-item label="结束日期" required class="field-half"><a-date-picker v-model:value="form.end_date" size="large" :disabled-date="(d: Dayjs) => disabledDate(d) || !!form.start_date && d.isBefore(form.start_date, 'day')" style="width:100%" /></a-form-item>
    </div>
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
