import { describe, expect, it } from 'vitest'
import { PROGRESS_STAGES, getProgressForElapsed } from './progress'

describe('generation progress stages', () => {
  it('exposes the user-facing planning stages in order', () => {
    expect(PROGRESS_STAGES.map(stage => stage.label)).toEqual([
      '正在分析你的旅行偏好',
      '正在搜索目的地景点',
      '正在整理天气与住宿',
      '正在编排每日路线',
      '正在生成最终计划',
      '正在检查行程是否符合需求'
    ])
  })

  it('caps simulated progress before the API response arrives', () => {
    expect(getProgressForElapsed(0).percent).toBe(8)
    expect(getProgressForElapsed(20_000).percent).toBeLessThanOrEqual(92)
    expect(getProgressForElapsed(60_000).percent).toBe(92)
  })
})
