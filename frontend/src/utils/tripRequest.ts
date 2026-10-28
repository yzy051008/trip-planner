import type { TripRequest } from '@/types'

type FormRequest = Omit<TripRequest, 'traveler_count' | 'budget_limit'> & {
  traveler_count?: number | string
  budget_limit?: number | string
  city?: string
  start_date?: string
  end_date?: string
  travel_days?: number
}

export function normalizeTripRequest(form: FormRequest): TripRequest {
  const { traveler_count: rawTravelerCount, budget_limit: rawBudget, ...base } = form
  const travelerCount = Number(rawTravelerCount || 1)
  const budget = rawBudget === '' || rawBudget == null
    ? undefined
    : Number(form.budget_limit)
  const destinations = base.destinations?.length
    ? base.destinations
    : base.city && base.start_date && base.end_date
      ? [{ city: base.city, start_date: base.start_date, end_date: base.end_date }]
      : []
  return {
    destinations,
    transportation: base.transportation,
    accommodation: base.accommodation,
    preferences: base.preferences,
    free_text_input: base.free_text_input,
    traveler_count: travelerCount > 0 ? travelerCount : 1,
    ...(budget == null || Number.isNaN(budget) ? {} : { budget_limit: budget }),
  }
}
