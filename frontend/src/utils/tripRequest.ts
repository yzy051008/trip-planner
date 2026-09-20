import type { TripRequest } from '@/types'

type FormRequest = Omit<TripRequest, 'traveler_count' | 'budget_limit'> & {
  traveler_count?: number | string
  budget_limit?: number | string
}

export function normalizeTripRequest(form: FormRequest): TripRequest {
  const { traveler_count: rawTravelerCount, budget_limit: rawBudget, ...base } = form
  const travelerCount = Number(rawTravelerCount || 1)
  const budget = rawBudget === '' || rawBudget == null
    ? undefined
    : Number(form.budget_limit)
  return {
    ...base,
    traveler_count: travelerCount > 0 ? travelerCount : 1,
    ...(budget == null || Number.isNaN(budget) ? {} : { budget_limit: budget }),
  }
}
