import { describe, it, expect, vi, beforeEach } from 'vitest'
import { exportToCsv } from './useExport'

describe('useExport', () => {
  let blobCalls: string[]

  beforeEach(() => {
    blobCalls = []
    vi.spyOn(globalThis, 'Blob').mockImplementation((parts?: BlobPart[]) => {
      blobCalls = (parts ?? []) as string[]
      return {} as Blob
    })
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
    vi.spyOn(document, 'createElement').mockReturnValue({
      click: vi.fn(),
    } as unknown as HTMLAnchorElement)
  })

  describe('CSV injection sanitization', () => {
    it('escapes cells starting with equals sign', () => {
      const columns = [{ key: 'name', label: 'Name' }]
      const rows = [{ name: '=SUM(A1:A10)' }]

      exportToCsv('test.csv', columns, rows)

      const csvContent = blobCalls[0].replace('\uFEFF', '')
      expect(csvContent).toContain("'=SUM(A1:A10)")
    })

    it('escapes cells starting with plus sign', () => {
      const columns = [{ key: 'val', label: 'Value' }]
      const rows = [{ val: '+cmd|/C calc' }]

      exportToCsv('test.csv', columns, rows)

      const csvContent = blobCalls[0].replace('\uFEFF', '')
      expect(csvContent).toContain("'+cmd|/C calc")
    })

    it('escapes cells starting with minus sign', () => {
      const columns = [{ key: 'val', label: 'Value' }]
      const rows = [{ val: '-1+1|cmd' }]

      exportToCsv('test.csv', columns, rows)

      const csvContent = blobCalls[0].replace('\uFEFF', '')
      expect(csvContent).toContain("'-1+1|cmd")
    })

    it('escapes cells starting with at sign', () => {
      const columns = [{ key: 'val', label: 'Value' }]
      const rows = [{ val: '@SUM(A1)' }]

      exportToCsv('test.csv', columns, rows)

      const csvContent = blobCalls[0].replace('\uFEFF', '')
      expect(csvContent).toContain("'@SUM(A1)")
    })

    it('does not escape normal cell values', () => {
      const columns = [{ key: 'name', label: 'Name' }]
      const rows = [{ name: 'Normal Value' }]

      exportToCsv('test.csv', columns, rows)

      const csvContent = blobCalls[0].replace('\uFEFF', '')
      expect(csvContent).toContain('Normal Value')
      expect(csvContent).not.toContain("'Normal Value")
    })
  })

  describe('CSV structure', () => {
    it('includes BOM for Excel compatibility', () => {
      const columns = [{ key: 'a', label: 'A' }]
      const rows = [{ a: '1' }]

      exportToCsv('test.csv', columns, rows)

      expect(blobCalls[0].startsWith('\uFEFF')).toBe(true)
    })

    it('formats column headers with labels', () => {
      const columns = [
        { key: 'sym', label: 'Symbol' },
        { key: 'price', label: 'Price' },
      ]
      const rows = [{ sym: 'AAPL', price: '150' }]

      exportToCsv('test.csv', columns, rows)

      const csvContent = blobCalls[0].replace('\uFEFF', '')
      expect(csvContent).toContain('"Symbol","Price"')
    })

    it('uses format function when provided', () => {
      const columns = [
        { key: 'val', label: 'Value', format: (v: unknown) => `$${v}` },
      ]
      const rows = [{ val: 100 }]

      exportToCsv('test.csv', columns, rows)

      const csvContent = blobCalls[0].replace('\uFEFF', '')
      expect(csvContent).toContain('$100')
    })

    it('handles null and undefined values', () => {
      const columns = [{ key: 'a', label: 'A' }, { key: 'b', label: 'B' }]
      const rows = [{ a: null, b: undefined }]

      exportToCsv('test.csv', columns, rows)

      const csvContent = blobCalls[0].replace('\uFEFF', '')
      const lines = csvContent.split('\n')
      expect(lines[1]).toContain('""')
    })
  })
})
