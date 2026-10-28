import { describe, expect, it } from 'vitest'
import { normalizeTripRequest } from './tripRequest'

describe('normalizeTripRequest', () => {
  it('uses one traveler and omits an empty budget', () => {
    const request = normalizeTripRequest({
      destinations: [{ city: '上海', start_date: '2026-09-01', end_date: '2026-09-03' }],
      transportation: '公共交通',
      accommodation: '舒适型酒店',
      preferences: [],
      free_text_input: '',
      traveler_count: '',
      budget_limit: '',
    })

    expect(request.traveler_count).toBe(1)
    expect(request).not.toHaveProperty('budget_limit')
  })

  it('converts traveler count and budget to numbers', () => {
    const request = normalizeTripRequest({
      destinations: [{ city: '上海', start_date: '2026-09-01', end_date: '2026-09-03' }],
      transportation: '公共交通',
      accommodation: '舒适型酒店',
      preferences: [],
      free_text_input: '',
      traveler_count: '2',
      budget_limit: '5000',
    })

    expect(request.traveler_count).toBe(2)
    expect(request.budget_limit).toBe(5000)
  })
})
