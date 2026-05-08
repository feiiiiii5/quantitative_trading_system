function sanitizeCsvCell(value: string): string {
  const first = value.charAt(0)
  if (first === '=' || first === '+' || first === '-' || first === '@' || first === '\t' || first === '\r') {
    return `'${value}`
  }
  return value
}

export function exportToCsv(filename: string, columns: { key: string; label: string; format?: (v: unknown) => string }[], rows: Record<string, unknown>[]): void {
  const header = columns.map(c => `"${c.label}"`).join(',')
  const dataLines = rows.map(row =>
    columns.map(c => {
      const raw = row[c.key]
      const formatted = c.format ? c.format(raw) : String(raw ?? '')
      const escaped = formatted.replace(/"/g, '""')
      return `"${sanitizeCsvCell(escaped)}"`
    }).join(',')
  )
  const csv = [header, ...dataLines].join('\n')
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
