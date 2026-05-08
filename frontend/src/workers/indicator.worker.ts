const ctx: Worker = self as unknown as Worker

function calcMA(data: number[], period: number): (number | null)[] {
  const result: (number | null)[] = []
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push(null)
    } else {
      let sum = 0
      for (let j = i - period + 1; j <= i; j++) sum += data[j]
      result.push(sum / period)
    }
  }
  return result
}

function calcEMA(data: number[], period: number): (number | null)[] {
  const result: (number | null)[] = []
  const k = 2 / (period + 1)
  let ema: number | null = null
  for (let i = 0; i < data.length; i++) {
    if (ema === null) {
      ema = data[i]
    } else {
      ema = data[i] * k + ema * (1 - k)
    }
    result.push(ema)
  }
  return result
}

function calcRSI(data: number[], period: number = 14): (number | null)[] {
  const result: (number | null)[] = []
  if (data.length < 2) return [null]
  let avgGain = 0
  let avgLoss = 0
  for (let i = 1; i <= Math.min(period, data.length - 1); i++) {
    const diff = data[i] - data[i - 1]
    if (diff > 0) avgGain += diff
    else avgLoss += Math.abs(diff)
  }
  avgGain /= period
  avgLoss /= period
  for (let i = 0; i < period; i++) result.push(null)
  if (avgLoss === 0) result.push(100)
  else result.push(100 - 100 / (1 + avgGain / avgLoss))
  for (let i = period + 1; i < data.length; i++) {
    const diff = data[i] - data[i - 1]
    const gain = diff > 0 ? diff : 0
    const loss = diff < 0 ? Math.abs(diff) : 0
    avgGain = (avgGain * (period - 1) + gain) / period
    avgLoss = (avgLoss * (period - 1) + loss) / period
    if (avgLoss === 0) result.push(100)
    else result.push(100 - 100 / (1 + avgGain / avgLoss))
  }
  return result
}

function calcMACD(data: number[], fast = 12, slow = 26, signal = 9) {
  const emaFast = calcEMA(data, fast)
  const emaSlow = calcEMA(data, slow)
  const dif: (number | null)[] = []
  for (let i = 0; i < data.length; i++) {
    const f = emaFast[i]
    const s = emaSlow[i]
    if (f !== null && s !== null) dif.push(f - s)
    else dif.push(null)
  }
  const validDif = dif.filter((v): v is number => v !== null)
  const deaArr = calcEMA(validDif, signal)
  const dea: (number | null)[] = []
  let di = 0
  for (let i = 0; i < dif.length; i++) {
    if (dif[i] !== null) {
      dea.push(deaArr[di] ?? null)
      di++
    } else {
      dea.push(null)
    }
  }
  const hist: (number | null)[] = []
  for (let i = 0; i < dif.length; i++) {
    const d = dif[i]
    const e = dea[i]
    if (d !== null && e !== null) hist.push((d - e) * 2)
    else hist.push(null)
  }
  return { dif, dea, hist }
}

ctx.addEventListener('message', (e: MessageEvent) => {
  const { type, data, params } = e.data
  try {
    let result: (number | null)[] | { dif: (number | null)[]; dea: (number | null)[]; hist: (number | null)[] } | null = null
    switch (type) {
      case 'ma':
        result = calcMA(data, params.period)
        break
      case 'ema':
        result = calcEMA(data, params.period)
        break
      case 'rsi':
        result = calcRSI(data, params.period)
        break
      case 'macd':
        result = calcMACD(data, params.fast, params.slow, params.signal)
        break
      default:
        result = null
    }
    ctx.postMessage({ type, result })
  } catch (err: unknown) {
    ctx.postMessage({ type, error: err instanceof Error ? err.message : String(err) })
  }
})
