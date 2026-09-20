<script setup lang="ts">
import type { Meal } from '@/types'
const props = defineProps<{ meals: Meal[]; editMode?: boolean }>()
const emit = defineEmits<{ update: [Meal[]] }>()
const add = () => emit('update', [...props.meals, { type: 'snack', name: '新的餐饮推荐', description: '', estimated_cost: 0 }])
const remove = (index: number, meals: Meal[]) => emit('update', meals.filter((_, i) => i !== index))
const patch = (index: number, key: keyof Meal, value: string | number, meals: Meal[]) => emit('update', meals.map((meal, i) => i === index ? { ...meal, [key]: key === 'estimated_cost' ? Number(value) : value } : meal))
</script>
<template>
  <div class="meal-list"><div class="section-line"><span>餐饮安排</span><button v-if="editMode" type="button" @click="add">＋ 添加</button></div>
    <div v-for="(meal, index) in meals" :key="index" class="meal-row"><span class="meal-type">{{ meal.type === 'breakfast' ? '早' : meal.type === 'lunch' ? '午' : meal.type === 'dinner' ? '晚' : '食' }}</span><input v-if="editMode" class="edit-input" :value="meal.name" @input="patch(index, 'name', ($event.target as HTMLInputElement).value, meals)" /><strong v-else>{{ meal.name }}</strong><input v-if="editMode" class="edit-input meal-cost" type="number" :value="meal.estimated_cost" @input="patch(index, 'estimated_cost', ($event.target as HTMLInputElement).value, meals)" /><span v-if="!editMode" class="muted">¥{{ meal.estimated_cost }}</span><button v-if="editMode" type="button" class="text-button" @click="remove(index, meals)">删除</button></div>
  </div>
</template>
