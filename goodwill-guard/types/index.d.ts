export type GoodwillViolation = {
  file: string
  line: number
  rule: number
  title: string
  found: string
}

export type GoodwillReport = {
  file: string
  violations: GoodwillViolation[]
}

declare module 'claude-code' {
  interface PluginState {
    'goodwill-guard': { reports: GoodwillReport[] }
  }
}
