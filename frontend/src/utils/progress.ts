export interface ProgressStage { label: string; atSecond: number; percent: number }

export const PROGRESS_STAGES: ProgressStage[] = [
  { label: '正在分析你的旅行偏好', atSecond: 0, percent: 8 },
  { label: '正在搜索目的地景点', atSecond: 4, percent: 28 },
  { label: '正在整理天气与住宿', atSecond: 10, percent: 52 },
  { label: '正在编排每日路线', atSecond: 18, percent: 72 },
  { label: '正在生成最终计划', atSecond: 30, percent: 82 },
  { label: '正在检查行程是否符合需求', atSecond: 42, percent: 90 }
]

export function getProgressForElapsed(elapsedMs: number): { stage: ProgressStage; percent: number } {
  const elapsedSeconds = Math.max(0, elapsedMs) / 1000
  let current = PROGRESS_STAGES[0]
  for (const stage of PROGRESS_STAGES) {
    if (elapsedSeconds >= stage.atSecond) current = stage
  }
  const percent = Math.min(92, current.percent + Math.ceil(Math.max(0, elapsedSeconds - current.atSecond) / 8))
  return { stage: current, percent }
}
