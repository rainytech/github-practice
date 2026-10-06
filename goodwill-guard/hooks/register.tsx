import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, ToolCallResult } from 'claude-code'

import { checkHtml, formatReport } from './checks'

const PANE = 'goodwill-guard'
const TITLE = 'Goodwill Guard'
const reports = atom({ plugin: 'goodwill-guard', key: 'reports' } as const, [])

const isHtml = (path: string) => /\.html?$/i.test(path)

async function audit($: EngineInterface, path: string, ran: ToolCallResult): Promise<ToolCallResult> {
  if (ran.deny !== undefined || ran.isError === true || !isHtml(path)) return ran

  const src = await $.fs.read(path)
  const violations = checkHtml(path, String(src), await $.clock.now())
  await update($, reports, list => [{ file: path, violations }, ...list.filter(r => r.file !== path)].slice(0, 20))

  if (violations.length === 0) {
    $.ui.status('Goodwill Guard: all clear')
    return ran
  }

  $.ui.status(`Goodwill Guard: ${violations.length} violation(s) — /goodwill-guard`)
  $.ui.open({ id: PANE, title: TITLE }).catch(() => undefined)

  return { ...ran, context: [...(ran.context ?? []), formatReport(path, violations)] }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'goodwill-guard',
      description: 'Show the Goodwill Guard violations panel',
    })
    return next(e)
  })

  on('command.run', { command: 'goodwill-guard' }, async $ => {
    await $.ui.open({ id: PANE, title: TITLE })
    return { text: 'Goodwill Guard panel opened.' }
  })

  // BLOCKER: no full-file rewrite of an existing .html file.
  on('tool.call', { tool: 'Write' }, async ($, e, next) => {
    if (isHtml(e.file_path) && (await $.fs.exists(e.file_path)))
      return {
        deny:
          `Goodwill Guard: ${e.file_path} already exists. Full-file rewrites are banned (RULE 1). ` +
          'Use str_replace (the Edit tool) to change only the part that needs changing.',
      }
    return audit($, e.file_path, await next(e))
  }).catch(($, e, next) => (next.called ? next(e) : { deny: 'Goodwill Guard: its write check failed.' }))

  on('tool.call', { tool: 'Edit' }, async ($, e, next) => audit($, e.file_path, await next(e)))

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const list = await read($, reports)

    if (list.length === 0) return <Text dimColor>No .html file checked yet.</Text>

    return (
      <Box flexDirection="column">
        {list.map(report => (
          <Box flexDirection="column" marginBottom={1}>
            <Text bold>{report.file}</Text>
            {report.violations.length === 0 ? (
              <Text color="green">Goodwill Guard: all clear</Text>
            ) : (
              report.violations.map(v => (
                <Text>
                  <Text color="red" bold>{`L${v.line}`}</Text>
                  <Text color="magenta">{`  #${v.rule} ${v.title}`}</Text>
                  <Text dimColor>{`  ${v.found}`}</Text>
                </Text>
              ))
            )}
          </Box>
        ))}
      </Box>
    )
  })
}
