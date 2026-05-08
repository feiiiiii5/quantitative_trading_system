import { describe, it, expect } from 'vitest'
import { formatPrice, formatNumber, formatPct, formatVolume, formatAmount, safeToFixed } from './format'

describe('formatPrice', () => {
  it('formats positive numbers with 2 decimal places', () => {
    expect(formatPrice(123.456)).toBe('123.46')
  })

  it('formats zero', () => {
    expect(formatPrice(0)).toBe('0.00')
  })

  it('formats negative numbers', () => {
    expect(formatPrice(-99.9)).toBe('-99.90')
  })

  it('returns fallback for NaN', () => {
    expect(formatPrice(NaN)).toBe('-')
  })

  it('formats very large numbers', () => {
    expect(formatPrice(1e9)).toBe('1000000000.00')
  })

  it('formats very small numbers', () => {
    expect(formatPrice(0.001)).toBe('0.00')
  })
})

describe('formatNumber', () => {
  it('formats numbers below 1e4 with default 2 digits', () => {
    expect(formatNumber(999)).toBe('999.00')
  })

  it('converts numbers >= 1e4 to 万', () => {
    expect(formatNumber(15000)).toBe('1.50万')
  })

  it('converts numbers >= 1e8 to 亿', () => {
    expect(formatNumber(2e8)).toBe('2.00亿')
  })

  it('returns fallback for NaN', () => {
    expect(formatNumber(NaN)).toBe('-')
  })
})

describe('formatPct', () => {
  it('adds plus sign for positive percentages', () => {
    expect(formatPct(3.5)).toBe('+3.50%')
  })

  it('no plus sign for negative percentages', () => {
    expect(formatPct(-1.2)).toBe('-1.20%')
  })

  it('returns fallback for NaN', () => {
    expect(formatPct(NaN)).toBe('-')
  })

  it('formats zero percentage with plus sign', () => {
    expect(formatPct(0)).toBe('+0.00%')
  })
})

describe('formatVolume', () => {
  it('formats small volumes as integers', () => {
    expect(formatVolume(500)).toBe('500')
  })

  it('converts volumes >= 1e4 to 万', () => {
    expect(formatVolume(20000)).toBe('2万')
  })

  it('converts volumes >= 1e8 to 亿', () => {
    expect(formatVolume(3e8)).toBe('3.00亿')
  })

  it('formats zero volume', () => {
    expect(formatVolume(0)).toBe('0')
  })

  it('returns fallback for NaN', () => {
    expect(formatVolume(NaN)).toBe('-')
  })
})

describe('formatAmount', () => {
  it('converts amounts >= 1e12 to 万亿', () => {
    expect(formatAmount(1.5e12)).toBe('1.50万亿')
  })

  it('converts amounts >= 1e8 to 亿', () => {
    expect(formatAmount(5e8)).toBe('5.00亿')
  })

  it('converts amounts >= 1e4 to 万', () => {
    expect(formatAmount(25000)).toBe('3万')
  })

  it('formats small amounts as integers', () => {
    expect(formatAmount(999)).toBe('999')
  })

  it('handles negative values', () => {
    expect(formatAmount(-5e8)).toBe('-500000000')
  })

  it('returns fallback for NaN', () => {
    expect(formatAmount(NaN)).toBe('-')
  })
})

describe('safeToFixed', () => {
  it('formats valid numbers', () => {
    expect(safeToFixed(3.14159, 3)).toBe('3.142')
  })

  it('returns fallback for null', () => {
    expect(safeToFixed(null)).toBe('-')
  })

  it('returns custom fallback', () => {
    expect(safeToFixed(undefined, 2, 'N/A')).toBe('N/A')
  })
})
