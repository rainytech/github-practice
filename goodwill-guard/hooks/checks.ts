import type { GoodwillViolation } from '../types'

export const RULE_TITLES: Record<number, string> = {
  1: 'Forced page break',
  2: '<thead> / <tfoot> used',
  3: 'Descendant span selector (use ">")',
  4: '÷ sign used (use a stacked .frac)',
  5: '@page margin must be 0',
  6: 'body padding must be 0.5cm',
  7: 'break-inside on a selector other than "table.wn tr" / ".formula-box"',
  8: 'Background must be #C8C8C8',
  9: 'table.wn missing "table-layout: fixed"',
  10: "Header date is not today's date",
}

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

// The institute is in Kerala: "today" is the date in India Standard Time.
const IST_OFFSET_MS = 330 * 60 * 1000

export function todayStamp(nowMs: number): string {
  const d = new Date(nowMs + IST_OFFSET_MS)
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`
}

type Rule = { selectors: string[]; selectorLine: number; decls: Decl[] }
type Decl = { prop: string; value: string; line: number }

const ALLOWED_BREAK_INSIDE = new Set(['table.wn tr', '.formula-box'])
const ZERO = /^0(?:px|cm|mm|in|pt|em|rem|%)?$/

function lineAt(starts: number[], offset: number): number {
  let lo = 0
  let hi = starts.length - 1
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1
    if ((starts[mid] ?? 0) <= offset) lo = mid
    else hi = mid - 1
  }
  return lo + 1
}

function blank(text: string): string {
  return text.replace(/[^\n]/g, ' ')
}

function parseCss(src: string, starts: number[]): Rule[] {
  const rules: Rule[] = []
  const styleRe = /<style\b[^>]*>([\s\S]*?)<\/style>/gi
  for (const style of src.matchAll(styleRe)) {
    const bodyOffset = (style.index ?? 0) + style[0].indexOf('>') + 1
    const css = (style[1] ?? '').replace(/\/\*[\s\S]*?\*\//g, blank)
    for (const rule of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
      const rawSel = rule[1] ?? ''
      const selStart = bodyOffset + (rule.index ?? 0) + (rawSel.length - rawSel.trimStart().length)
      const declStart = bodyOffset + (rule.index ?? 0) + rawSel.length + 1
      const decls: Decl[] = []
      const body = rule[2] ?? ''
      for (const decl of body.matchAll(/([-\w]+)\s*:\s*([^;]*)/g)) {
        const lead = (decl[0].length - decl[0].trimStart().length)
        decls.push({
          prop: (decl[1] ?? '').toLowerCase(),
          value: (decl[2] ?? '').trim(),
          line: lineAt(starts, declStart + (decl.index ?? 0) + lead),
        })
      }
      rules.push({
        selectors: rawSel.split(',').map(s => s.trim().replace(/\s+/g, ' ')).filter(Boolean),
        selectorLine: lineAt(starts, selStart),
        decls,
      })
    }
  }
  return rules
}

function stripImportant(value: string): string {
  return value.replace(/!\s*important/i, '').trim()
}

function headerDateCheck(src: string, starts: number[], expected: string): { line: number; found: string } | undefined {
  const open = /<(\w+)\b[^>]*\bclass\s*=\s*["'][^"']*\bheader\b[^"']*["'][^>]*>/i.exec(src)
  if (!open) return { line: 1, found: 'no .header element found' }
  const tag = (open[1] ?? 'div').toLowerCase()
  const tagRe = new RegExp(`<(/?)${tag}\\b[^>]*>`, 'gi')
  tagRe.lastIndex = open.index + open[0].length
  let depth = 1
  let end = src.length
  for (let m = tagRe.exec(src); m; m = tagRe.exec(src)) {
    depth += m[1] ? -1 : 1
    if (depth === 0) {
      end = m.index
      break
    }
  }
  const inner = src.slice(open.index, end)
  const month = MONTHS.join('|')
  const dateRe = new RegExp(
    `\\b\\d{1,2}(?:st|nd|rd|th)?\\s+(?:${month}|[A-Z][a-z]{2})\\.?,?\\s+\\d{2,4}\\b` +
      `|\\b(?:${month}|[A-Z][a-z]{2})\\.?\\s+\\d{1,2}(?:st|nd|rd|th)?,?\\s+\\d{4}\\b` +
      `|\\b\\d{1,4}[/.-]\\d{1,2}[/.-]\\d{1,4}\\b`,
    'g',
  )
  const dates = [...inner.matchAll(dateRe)]
  if (dates.length === 0) return { line: lineAt(starts, open.index), found: 'no date in header' }
  const exact = dates.find(d => d[0] === expected)
  if (exact) return undefined
  const first = dates[0]!
  return { line: lineAt(starts, open.index + (first.index ?? 0)), found: first[0] }
}

export function checkHtml(file: string, src: string, nowMs: number): GoodwillViolation[] {
  const out: GoodwillViolation[] = []
  const add = (rule: number, line: number, found: string) =>
    out.push({ file, line, rule, title: RULE_TITLES[rule] ?? '', found: found.trim().slice(0, 120) })

  const starts = [0]
  for (let i = 0; i < src.length; i++) if (src[i] === '\n') starts.push(i + 1)
  const lines = src.split('\n')

  // Line scans: 1, 2, 4, and inline-style break-inside for 7.
  lines.forEach((text, i) => {
    const line = i + 1
    for (const m of text.matchAll(/(?:page-)?break-(?:after|before)/gi)) add(1, line, m[0])
    for (const m of text.matchAll(/<\s*(?:thead|tfoot)\b/gi)) add(2, line, m[0])
    if (text.includes('÷')) add(4, line, text)
    if (/style\s*=\s*["'][^"']*\b(?:page-)?break-inside/i.test(text)) add(7, line, 'inline style with break-inside')
  })

  const rules = parseCss(src, starts)

  // 3: descendant span selectors.
  for (const rule of rules)
    for (const sel of rule.selectors)
      for (const m of sel.matchAll(/(\.(?:q|notes|adj|wn-text))\s+span\b/g))
        add(3, rule.selectorLine, `${sel}  →  use "${m[1]} > span"`)

  // 5: @page margin.
  const pages = rules.filter(r => r.selectors.some(s => s.startsWith('@page')))
  for (const page of pages)
    for (const d of page.decls)
      if (/^margin(?:-|$)/.test(d.prop) && !stripImportant(d.value).split(/\s+/).every(v => ZERO.test(v)))
        add(5, d.line, `${d.prop}: ${d.value}`)
  if (pages.length > 0 && !pages.some(p => p.decls.some(d => d.prop === 'margin')))
    add(5, pages[0]!.selectorLine, '@page has no "margin: 0"')
  if (pages.length === 0 && rules.length > 0) add(5, rules[0]!.selectorLine, 'no @page rule')

  // 6: body padding.
  const bodies = rules.filter(r => r.selectors.includes('body'))
  for (const body of bodies)
    for (const d of body.decls)
      if (d.prop === 'padding' && stripImportant(d.value) !== '0.5cm') add(6, d.line, `padding: ${d.value}`)
      else if (/^padding-/.test(d.prop)) add(6, d.line, `${d.prop}: ${d.value}`)
  if (rules.length > 0 && !bodies.some(b => b.decls.some(d => d.prop === 'padding')))
    add(6, bodies[0]?.selectorLine ?? rules[0]!.selectorLine, 'body has no "padding: 0.5cm"')

  // 7: break-inside scoping.
  for (const rule of rules)
    for (const d of rule.decls)
      if (/^(?:page-)?break-inside$/.test(d.prop)) {
        const stray = rule.selectors.filter(s => !ALLOWED_BREAK_INSIDE.has(s))
        if (stray.length > 0) add(7, d.line, `${stray.join(', ')} { ${d.prop}: ${d.value} }`)
      }

  // 8: body / .page-block background.
  for (const target of ['body', '.page-block']) {
    const owners = rules.filter(r => r.selectors.includes(target))
    for (const r of owners)
      for (const d of r.decls)
        if ((d.prop === 'background' || d.prop === 'background-color') &&
            stripImportant(d.value).toUpperCase() !== '#C8C8C8')
          add(8, d.line, `${target} { ${d.prop}: ${d.value} }`)
    if (owners.length > 0 && !owners.some(r => r.decls.some(d => d.prop === 'background' || d.prop === 'background-color')))
      add(8, owners[0]!.selectorLine, `${target} has no background (needs #C8C8C8)`)
  }

  // 9: table.wn layout.
  const wnRules = rules.filter(r => r.selectors.includes('table.wn'))
  const isFixed = wnRules.some(r => r.decls.some(d => d.prop === 'table-layout' && stripImportant(d.value) === 'fixed'))
  if (!isFixed) {
    const wnTable = lines.findIndex(t => /<table\b[^>]*class\s*=\s*["'][^"']*\bwn\b/i.test(t))
    if (wnRules.length > 0) add(9, wnRules[0]!.selectorLine, 'table.wn { … } has no table-layout: fixed')
    else if (wnTable >= 0) add(9, wnTable + 1, 'no table.wn rule with table-layout: fixed')
  }

  // 10: header date.
  const expected = todayStamp(nowMs)
  const date = headerDateCheck(src, starts, expected)
  if (date) add(10, date.line, `${date.found}  →  expected "${expected}"`)

  return out.sort((a, b) => a.line - b.line || a.rule - b.rule)
}

export function formatReport(file: string, violations: GoodwillViolation[]): string {
  if (violations.length === 0) return 'Goodwill Guard: all clear'
  const rows = violations.map(v => `  ${file}:${v.line}  #${v.rule} ${v.title} — ${v.found}`)
  return [`Goodwill Guard: ${violations.length} violation(s) in ${file}. Fix each with str_replace:`, ...rows].join('\n')
}
