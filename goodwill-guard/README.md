# goodwill-guard

A Claude Code mod that enforces the Goodwill HTML worksheet rules.

## Install

At the prompt of a Claude Code terminal session:

```
/plugin install goodwill-guard --marketplace rainytech/github-practice
```

Answer `y` to add the marketplace, then pick a scope (user scope recommended).

## What it does

- **Blocker:** a full-file `Write` to an `.html` file that already exists is refused; Claude is told to use str_replace (Edit).
- **Checks:** after every `Write` or `Edit` of an `.html` file, the file is checked against 10 rules.
  Each violation is listed with its file name and line number.
  1. `break-after`, `page-break-after`, `break-before`, `page-break-before` anywhere
  2. `<thead` or `<tfoot` anywhere
  3. `.q span`, `.notes span`, `.adj span`, `.wn-text span` (must be `.q > span` etc.)
  4. The ÷ sign anywhere
  5. `@page` margin not 0
  6. `body` padding not 0.5cm
  7. `break-inside` on any selector other than `table.wn tr` and `.formula-box`
  8. `body` or `.page-block` background not `#C8C8C8`
  9. `table.wn` without `table-layout: fixed`
  10. Header date not today's date (India time) in the `6 October 2026` format
- **Output:** violations open the **Goodwill Guard** panel (reopen it with `/goodwill-guard`) and are passed to Claude so it can fix them in the same turn.
  With no violations the status line shows `Goodwill Guard: all clear`.

Only changes made through Claude's Write and Edit tools are checked.
Files changed by shell commands (`sed`, `cat >`) are not.

## Develop

```
claude plugin validate goodwill-guard
claude plugin test goodwill-guard
node --experimental-strip-types goodwill-guard/samples/run.mts goodwill-guard/samples/sample-bad.html
```
