import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createLogger, setLogLevel } from './useLogger'

describe('createLogger', () => {
  beforeEach(() => {
    setLogLevel('debug')
  })

  it('creates a logger with all methods', () => {
    const logger = createLogger('test')
    expect(logger.debug).toBeTypeOf('function')
    expect(logger.info).toBeTypeOf('function')
    expect(logger.warn).toBeTypeOf('function')
    expect(logger.error).toBeTypeOf('function')
  })

  it('respects log level filtering', () => {
    setLogLevel('error')
    const logger = createLogger('test')
    expect(() => logger.debug('test')).not.toThrow()
    expect(() => logger.info('test')).not.toThrow()
    expect(() => logger.warn('test')).not.toThrow()
    expect(() => logger.error('test')).not.toThrow()
  })

  it('calls console.error on error level', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    setLogLevel('error')
    const logger = createLogger('ctx')
    logger.error('boom', { code: 500 })
    expect(spy).toHaveBeenCalled()
    spy.mockRestore()
  })

  it('suppresses debug when level is warn', () => {
    const spy = vi.spyOn(console, 'debug').mockImplementation(() => {})
    setLogLevel('warn')
    const logger = createLogger('ctx')
    logger.debug('should not appear')
    expect(spy).not.toHaveBeenCalled()
    spy.mockRestore()
  })
})
