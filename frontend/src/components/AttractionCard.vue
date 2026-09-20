<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { Attraction } from '@/types'
import { fetchAttractionPhoto } from '@/services/api'
const props = defineProps<{ attraction: Attraction; editMode?: boolean }>()
const emit = defineEmits<{ update: [Attraction]; remove: [] }>()
const photo = ref(props.attraction.image_url || props.attraction.photos?.[0] || '')
const loading = ref(false)
const imageFailed = ref(false)
onMounted(async () => { if (!photo.value && props.attraction.name) { loading.value = true; try { photo.value = (await fetchAttractionPhoto(props.attraction.name)).data.photo_url || '' } catch { /* 图片失败不影响行程 */ } finally { loading.value = false } } })
const update = (key: keyof Attraction, value: string | number) => emit('update', { ...props.attraction, [key]: key === 'visit_duration' || key === 'ticket_price' ? Number(value) : value })
</script>
<template>
  <article class="attraction-card">
    <div class="attraction-photo" style="height: 108px; min-height: 108px; max-height: 108px; overflow: hidden"><img v-if="photo && !imageFailed" :src="photo" :alt="attraction.name" style="width: 100%; height: 108px; object-fit: cover; display: block" @error="imageFailed = true" /><span v-if="!photo || imageFailed">{{ loading ? '加载中' : '景点图片暂不可用' }}</span><button v-if="editMode" type="button" class="remove-button" @click="emit('remove')">×</button></div>
    <div class="attraction-body">
      <div class="card-kicker">{{ attraction.category || '景点' }} <span v-if="attraction.rating">★ {{ attraction.rating }}</span></div>
      <input v-if="editMode" class="edit-input title-input" :value="attraction.name" @input="update('name', ($event.target as HTMLInputElement).value)" /><h3 v-else class="attraction-name">{{ attraction.name }}</h3>
      <input v-if="editMode" class="edit-input" :value="attraction.address" @input="update('address', ($event.target as HTMLInputElement).value)" /><p v-else class="attraction-address muted">{{ attraction.address }}</p>
      <textarea v-if="editMode" class="edit-input" :value="attraction.description" @input="update('description', ($event.target as HTMLTextAreaElement).value)" /><div v-else class="description-scroll"><p>{{ attraction.description }}</p></div>
      <div class="card-meta"><span>⏱ {{ attraction.visit_duration }} 分钟</span><span>¥ {{ attraction.ticket_price || 0 }}</span></div>
    </div>
  </article>
</template>
<style scoped>
.attraction-photo img { width: 100%; height: 100%; object-fit: cover; display: block; }
.attraction-photo { height: 108px !important; min-height: 108px !important; }
.attraction-name { margin: 7px 0 4px !important; line-height: 1.3; }
.attraction-address { margin: 0 0 8px !important; min-height: 32px; line-height: 1.45 !important; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.description-scroll { max-height: 130px; overflow-y: scroll; overscroll-behavior: contain; padding: 3px 7px 3px 0; scrollbar-width: thin; scrollbar-color: #c8bda9 transparent; border-top: 1px solid #eee7db; }
.description-scroll::-webkit-scrollbar { width: 5px; }
.description-scroll::-webkit-scrollbar-thumb { background: #c8bda9; border-radius: 10px; }
.description-scroll p { margin: 8px 0; min-height: 0; }
</style>
