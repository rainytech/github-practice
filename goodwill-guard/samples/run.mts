// Runs the checks on the sample files: node --experimental-strip-types samples/run.mts <file>...
import { readFileSync } from 'node:fs'
import { basename } from 'node:path'
import { checkHtml, formatReport } from '../hooks/checks.ts'

for (const path of process.argv.slice(2)) {
  const name = basename(path)
  console.log(formatReport(name, checkHtml(name, readFileSync(path, 'utf8'), Date.now())) + '\n')
}
