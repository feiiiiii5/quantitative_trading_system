type LogLevel = 'debug' | 'info' | 'warn' | 'error'

interface LogEntry {
  level: LogLevel
  context: string
  message: string
  data?: unknown
  timestamp: number
}

const LOG_LEVEL_PRIORITY: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
}

let minLevel: LogLevel = 'warn'

export function setLogLevel(level: LogLevel): void {
  minLevel = level
}

interface Logger {
  debug: (msg: string, data?: unknown) => void
  info: (msg: string, data?: unknown) => void
  warn: (msg: string, data?: unknown) => void
  error: (msg: string, data?: unknown) => void
}

export function createLogger(context: string): Logger {
  function emit(level: LogLevel, message: string, data?: unknown): void {
    if (LOG_LEVEL_PRIORITY[level] < LOG_LEVEL_PRIORITY[minLevel]) return

    const entry: LogEntry = {
      level,
      context,
      message,
      data,
      timestamp: Date.now(),
    }

    const prefix = `[${entry.context}]`

    switch (level) {
      case 'debug':
        console.debug(prefix, message, data ?? '')
        break
      case 'info':
        console.info(prefix, message, data ?? '')
        break
      case 'warn':
        console.warn(prefix, message, data ?? '')
        break
      case 'error':
        console.error(prefix, message, data ?? '')
        break
    }
  }

  return {
    debug: (msg: string, data?: unknown) => emit('debug', msg, data),
    info: (msg: string, data?: unknown) => emit('info', msg, data),
    warn: (msg: string, data?: unknown) => emit('warn', msg, data),
    error: (msg: string, data?: unknown) => emit('error', msg, data),
  }
}
