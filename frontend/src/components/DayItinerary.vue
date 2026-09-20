<script setup lang="ts">
import type { DayPlan, Attraction, Meal } from '@/types'
import AttractionCard from './AttractionCard.vue'
import MealList from './MealList.vue'
const props = defineProps<{ day: DayPlan; editMode?: boolean }>()
const emit = defineEmits<{ update: [DayPlan] }>()
const patch = (key: keyof DayPlan, value: string | Attraction[] | Meal[]) => emit('update', { ...props.day, [key]: value })
const updateAttraction = (index: number, item: Attraction) => patch('attractions', props.day.attractions.map((a, i) => i === index ? item : a))
const removeAttraction = (index: number) => patch('attractions', props.day.attractions.filter((_, i) => i !== index))
const addAttraction = () => patch('attractions', [...props.day.attractions, { name: '新的景点', address: '', location: { longitude: 0, latitude: 0 }, visit_duration: 90, description: '', category: '景点', photos: [], ticket_price: 0 }])
</script>
<template>
  <section class="day-block">
    <div class="day-heading"><span class="day-number">{{ String(day.day_index + 1).padStart(2, '0') }}</span><div><div class="eyebrow">DAY {{ day.day_index + 1 }}</div><h2>{{ day.date }}</h2></div></div>
    <div class="day-fields"><div><span class="label">今日主题</span><input v-if="editMode" class="edit-input" :value="day.description" @input="patch('description', ($event.target as HTMLInputElement).value)" /><span v-else>{{ day.description }}</span></div><div><span class="label">交通 · 住宿</span><div v-if="editMode" class="field-row"><input class="edit-input" :value="day.transportation" @input="patch('transportation', ($event.target as HTMLInputElement).value)" /><input class="edit-input" :value="day.accommodation" @input="patch('accommodation', ($event.target as HTMLInputElement).value)" /></div><span v-else>{{ day.transportation }} · {{ day.accommodation }}</span></div></div>
    <div class="section-line"><span>景点路线</span><button v-if="editMode" type="button" @click="addAttraction">＋ 添加景点</button></div>
    <div class="attraction-grid"><AttractionCard v-for="(attraction, index) in day.attractions" :key="index" :attraction="attraction" :edit-mode="editMode" @update="updateAttraction(index, $event)" @remove="removeAttraction(index)" /></div>
    <MealList :meals="day.meals" :edit-mode="editMode" @update="patch('meals', $event)" />
    <div v-if="day.hotel" class="hotel-note"><span>⌂</span><div v-if="editMode" class="hotel-edit"><input class="edit-input" :value="day.hotel.name" @input="patch('hotel', { ...day.hotel, name: ($event.target as HTMLInputElement).value } as any)" /><input class="edit-input" :value="day.hotel.address" @input="patch('hotel', { ...day.hotel, address: ($event.target as HTMLInputElement).value } as any)" /></div><div v-else><strong>{{ day.hotel.name }}</strong><p>{{ day.hotel.address }} · {{ day.hotel.price_range }}</p></div></div>
  </section>
</template>
