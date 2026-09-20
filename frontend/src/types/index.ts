export interface TripRequest {
  city: string
  start_date: string
  end_date: string
  travel_days: number
  transportation: string
  accommodation: string
  preferences: string[]
  free_text_input?: string
  traveler_count: number
  budget_limit?: number | null
}

export interface Location { longitude: number; latitude: number }
export interface Attraction {
  name: string; address: string; location: Location; visit_duration: number
  description: string; category?: string; rating?: number | null; photos: string[]
  poi_id?: string; image_url?: string | null; ticket_price: number
}
export interface Meal {
  type: string; name: string; address?: string | null; location?: Location | null
  description?: string | null; estimated_cost: number
}
export interface Hotel {
  name: string; address: string; location?: Location | null; price_range: string
  rating: string; distance: string; type: string; estimated_cost: number
}
export interface DayPlan {
  date: string; day_index: number; description: string; transportation: string
  accommodation: string; hotel?: Hotel | null; attractions: Attraction[]; meals: Meal[]
}
export interface WeatherInfo {
  date: string; forecast_available?: boolean; day_weather: string; night_weather: string; day_temp: number | string
  night_temp: number | string; wind_direction: string; wind_power: string
}
export interface Budget {
  total_attractions: number; total_hotels: number; total_meals: number
  total_transportation: number; total: number
}
export interface TripPlan {
  city: string; start_date: string; end_date: string; days: DayPlan[]
  weather_info: WeatherInfo[]; overall_suggestions: string; budget?: Budget | null
}
export interface ReviewResult {
  level: 'A' | 'B' | 'C'
  passed: boolean
  hard_rule_passed: boolean
  semantic_rule_passed: boolean
  issues: string[]
  suggestions: string[]
  summary: string
  retry_count: number
}
export interface TripPlanResponse { success: boolean; message: string; id?: number | null; data?: TripPlan | null; review?: ReviewResult | null }
export interface HistorySummary {
  id: number; city: string; start_date: string; end_date: string; travel_days: number
  transportation: string; accommodation: string; preferences: string[]; created_at: string
}
export interface HistoryListResponse {
  success: boolean; data: HistorySummary[]; total: number; page: number; page_size: number
}
export interface HistoryDetail { id: number; city: string; start_date: string; end_date: string; travel_days: number; transportation: string; accommodation: string; preferences: string[]; free_text_input?: string; traveler_count?: number; budget_limit?: number | null; plan: TripPlan; created_at: string }
export interface HistoryDetailResponse { success: boolean; data: HistoryDetail }
export interface MutationResponse { success: boolean; message: string; id?: number }
export interface PhotoResponse { success: boolean; data: { name: string; photo_url?: string | null } }
