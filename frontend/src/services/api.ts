import axios from 'axios'
import type { HistoryDetailResponse, HistoryListResponse, MutationResponse, PhotoResponse, PlanningConfirmRequest, PlanningMessageRequest, PlanningSessionResponse, PlanningTurnResponse, TripPlan, TripPlanResponse, TripRequest } from '@/types'

const client = axios.create({
  // 开发环境始终走 Vite 代理，避免 localhost/127.0.0.1 跨域和旧 .env 注入值造成 Network Error
  baseURL: import.meta.env.DEV ? '' : (import.meta.env.VITE_API_BASE_URL || ''),
  timeout: 300000,
  headers: { 'Content-Type': 'application/json' }
})

function readableError(error: any, fallback: string): Error {
  return new Error(error?.response?.data?.detail || error?.response?.data?.message || error?.message || fallback)
}

export async function generateTripPlan(request: TripRequest): Promise<TripPlanResponse> {
  try { return (await client.post<TripPlanResponse>('/api/trip/plan', request)).data } catch (error) { throw readableError(error, '生成旅行计划失败') }
}
export async function createPlanningSession(request: TripRequest): Promise<PlanningSessionResponse> {
  try { return (await client.post<PlanningSessionResponse>('/api/planning/sessions', request)).data } catch (error) { throw readableError(error, '生成临时计划失败') }
}
export async function fetchPlanningSession(id: string): Promise<PlanningSessionResponse> {
  try { return (await client.get<PlanningSessionResponse>(`/api/planning/sessions/${id}`)).data } catch (error) { throw readableError(error, '加载临时计划失败') }
}
export async function sendPlanningMessage(id: string, payload: PlanningMessageRequest): Promise<PlanningTurnResponse> {
  try { return (await client.post<PlanningTurnResponse>(`/api/planning/sessions/${id}/messages`, payload)).data } catch (error) { throw readableError(error, '提交修改需求失败') }
}
export async function confirmPlanningSession(id: string, payload: PlanningConfirmRequest): Promise<PlanningSessionResponse> {
  try { return (await client.post<PlanningSessionResponse>(`/api/planning/sessions/${id}/confirm`, payload)).data } catch (error) { throw readableError(error, '确认计划失败') }
}
export async function cancelPlanningSession(id: string): Promise<PlanningSessionResponse> {
  try { return (await client.delete<PlanningSessionResponse>(`/api/planning/sessions/${id}`)).data } catch (error) { throw readableError(error, '放弃临时计划失败') }
}
export async function fetchHistory(page = 1, pageSize = 10, city = ''): Promise<HistoryListResponse> {
  try { return (await client.get<HistoryListResponse>('/api/history', { params: { page, page_size: pageSize, city: city || undefined } })).data } catch (error) { throw readableError(error, '加载历史记录失败') }
}
export async function fetchHistoryDetail(id: number): Promise<HistoryDetailResponse> {
  try { return (await client.get<HistoryDetailResponse>(`/api/history/${id}`)).data } catch (error) { throw readableError(error, '加载行程详情失败') }
}
export async function updateHistory(id: number, plan: TripPlan): Promise<MutationResponse> {
  try { return (await client.put<MutationResponse>(`/api/history/${id}`, plan)).data } catch (error) { throw readableError(error, '保存行程失败') }
}
export async function deleteHistory(id: number): Promise<MutationResponse> {
  try { return (await client.delete<MutationResponse>(`/api/history/${id}`)).data } catch (error) { throw readableError(error, '删除行程失败') }
}
export async function fetchAttractionPhoto(name: string): Promise<PhotoResponse> {
  try { return (await client.get<PhotoResponse>('/api/poi/photo', { params: { name } })).data } catch (error) { throw readableError(error, '获取景点图片失败') }
}
