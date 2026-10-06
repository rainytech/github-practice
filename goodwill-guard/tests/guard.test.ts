import { describe, expect, mock, test } from 'claude-code/testing'

import { checkHtml, todayStamp } from '../hooks/checks'

// 6 October 2026, 11:30 IST.
const NOW = Date.UTC(2026, 9, 6, 6, 0)

const CLEAN = `<html><head><style>
@page { size: A4; margin: 0; }
body { background: #C8C8C8; padding: 0.5cm; }
.page-block { background: #C8C8C8 !important; }
table.wn tr,
.formula-box { break-inside: avoid; page-break-inside: avoid; }
.q > span, .notes > span, .adj > span, .wn-text > span { display: block; }
table.wn { width: 100%; table-layout: fixed; }
</style></head><body>
<div class="header"><div>GOODWILL</div><div>6 October 2026</div></div>
<div class="page-block"><table class="wn"><tbody><tr><th>Particulars</th></tr></tbody></table></div>
</body></html>`

const rulesOf = (src: string) => checkHtml('t.html', src, NOW).map(v => v.rule)
const swap = (from: string, to: string) => CLEAN.replace(from, to)

describe('checks', () => {
  test('clean file is all clear', async () => {
    expect(checkHtml('t.html', CLEAN, NOW)).toEqual([])
  })

  test("today's stamp uses India time", async () => {
    expect(todayStamp(NOW)).toBe('6 October 2026')
    expect(todayStamp(Date.UTC(2026, 9, 5, 19, 0))).toBe('6 October 2026')
  })

  test('#1 forced page breaks, with line numbers', async () => {
    const v = checkHtml('t.html', swap('</body>', '<p style="page-break-after: always"></p>\n</body>'), NOW)
    expect(v.map(x => [x.rule, x.line])).toEqual([[1, 12]])
    expect(rulesOf(swap('.page-block {', '.page-block { break-after: page;'))).toEqual([1])
  })

  test('#2 thead and tfoot', async () => {
    expect(rulesOf(swap('<tbody>', '<thead></thead><tfoot></tfoot><tbody>'))).toEqual([2, 2])
  })

  test('#3 descendant span selectors', async () => {
    expect(rulesOf(swap('.q > span, .notes > span, .adj > span, .wn-text > span', '.q span, .notes span, .adj span, .wn-text span'))).toEqual([3, 3, 3, 3])
  })

  test('#4 division sign', async () => {
    expect(rulesOf(swap('GOODWILL', '3 ÷ 4'))).toEqual([4])
  })

  test('#5 @page margin', async () => {
    expect(rulesOf(swap('margin: 0;', 'margin: 0.25cm;'))).toEqual([5])
    expect(rulesOf(swap('margin: 0;', ''))).toEqual([5])
  })

  test('#6 body padding', async () => {
    expect(rulesOf(swap('padding: 0.5cm', 'padding: 0.5in'))).toEqual([6])
  })

  test('#7 break-inside scope', async () => {
    expect(rulesOf(swap('.formula-box {', '.formula-box, tr {'))).toEqual([7, 7])
    expect(rulesOf(swap('</style>', '.notes-block { break-inside: avoid; }\n</style>'))).toEqual([7])
  })

  test('#8 backgrounds', async () => {
    expect(rulesOf(swap('background: #C8C8C8;', 'background: #fff;'))).toEqual([8])
    expect(rulesOf(swap('#C8C8C8 !important', 'white !important'))).toEqual([8])
  })

  test('#9 table-layout fixed', async () => {
    expect(rulesOf(swap('table-layout: fixed;', ''))).toEqual([9])
  })

  test('#10 header date', async () => {
    expect(rulesOf(swap('6 October 2026', '24 August 2026'))).toEqual([10])
    expect(rulesOf(swap('6 October 2026', '6th October, 2026'))).toEqual([10])
    expect(rulesOf(swap('6 October 2026', '06/10/2026'))).toEqual([10])
    expect(rulesOf(swap('<div>6 October 2026</div>', ''))).toEqual([10])
  })
})

describe('hooks', () => {
  test('blocks a full rewrite of an existing .html file', async ($, on) => {
    let isWritten = false
    on('fs.exists', async () => ({ value: true }))
    on('tool.call', { tool: 'Write' }, async () => {
      isWritten = true
      return { result: { type: 'update', filePath: '/w/a.html', content: '' } } as never
    })
    const ran = await $.tool.call({ tool: 'Write', file_path: '/w/a.html', content: CLEAN })
    expect(isWritten).toBe(false)
    expect(String(ran.deny ?? ran.text)).toContain('str_replace')
  })

  test('lets a new .html file be written, and reports its violations', async ($, on) => {
    mock.clock(on, { now: NOW })
    let isWritten = false
    on('fs.exists', async () => ({ value: false }))
    on('fs.read', async () => ({ value: swap('table-layout: fixed;', '') }))
    on('tool.call', { tool: 'Write' }, async () => {
      isWritten = true
      return { result: { type: 'create', filePath: '/w/b.html', content: '' } } as never
    })
    const ran = await $.tool.call({ tool: 'Write', file_path: '/w/b.html', content: CLEAN })
    expect(isWritten).toBe(true)
    expect(ran.deny).toBeUndefined()
    expect(String(ran.context ?? '')).toContain('#9 table.wn missing')
  })

  test('leaves non-html writes alone', async ($, on) => {
    let isWritten = false
    on('fs.exists', async () => ({ value: true }))
    on('tool.call', { tool: 'Write' }, async () => {
      isWritten = true
      return { result: { type: 'update', filePath: '/w/notes.md', content: '' } } as never
    })
    await $.tool.call({ tool: 'Write', file_path: '/w/notes.md', content: 'x' })
    expect(isWritten).toBe(true)
  })
})
