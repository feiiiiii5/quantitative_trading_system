function calcMA(data: number[], period: number): number[] {
  const result: number[] = []
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) { result.push(NaN); continue }
    let sum = 0
    for (let j = i - period + 1; j <= i; j++) sum += data[j]
    result.push(sum / period)
  }
  return result
}

function calcEMA(data: number[], period: number): number[] {
  const result: number[] = [data[0]]
  const k = 2 / (period + 1)
  for (let i = 1; i < data.length; i++) {
    result.push(data[i] * k + result[i - 1] * (1 - k))
  }
  return result
}

function calcMACD(close: number[], fast = 12, slow = 26, signal = 9) {
  const emaFast = calcEMA(close, fast)
  const emaSlow = calcEMA(close, slow)
  const dif = emaFast.map((v, i) => v - emaSlow[i])
  const dea = calcEMA(dif, signal)
  const hist = dif.map((v, i) => 2 * (v - dea[i]))
  return { dif, dea, hist }
}

function calcRSI(close: number[], periods = [6, 12, 24]): Record<number, number[]> {
  const result: Record<number, number[]> = {}
  for (const p of periods) {
    const arr: number[] = [50]
    let avgGain = 0, avgLoss = 0
    for (let i = 1; i < close.length; i++) {
      const change = close[i] - close[i - 1]
      const gain = change > 0 ? change : 0
      const loss = change < 0 ? -change : 0
      if (i <= p) {
        avgGain += gain; avgLoss += loss
        if (i === p) {
          avgGain /= p; avgLoss /= p
          arr.push(avgLoss > 0 ? 100 - 100 / (1 + avgGain / avgLoss) : 100)
        } else { arr.push(50) }
      } else {
        avgGain = (avgGain * (p - 1) + gain) / p
        avgLoss = (avgLoss * (p - 1) + loss) / p
        arr.push(avgLoss > 0 ? 100 - 100 / (1 + avgGain / avgLoss) : 100)
      }
    }
    result[p] = arr
  }
  return result
}

function calcKDJ(high: number[], low: number[], close: number[], n = 9, m1 = 3, m2 = 3) {
  const kArr: number[] = [50], dArr: number[] = [50], jArr: number[] = [50]
  for (let i = 1; i < close.length; i++) {
    const start = Math.max(0, i - n + 1)
    let hn = high[i], ln = low[i]
    for (let j = start; j < i; j++) { if (high[j] > hn) hn = high[j]; if (low[j] < ln) ln = low[j] }
    const rsv = hn - ln > 0 ? (close[i] - ln) / (hn - ln) * 100 : 50
    const k = (m1 - 1) / m1 * kArr[i - 1] + rsv / m1
    const d = (m2 - 1) / m2 * dArr[i - 1] + k / m2
    kArr.push(k); dArr.push(d); jArr.push(3 * k - 2 * d)
  }
  return { k: kArr, d: dArr, j: jArr }
}

function calcBOLL(close: number[], period = 20, mult = 2) {
  const mid = calcMA(close, period)
  const upper: number[] = [], lower: number[] = []
  for (let i = 0; i < close.length; i++) {
    if (isNaN(mid[i])) { upper.push(NaN); lower.push(NaN); continue }
    const start = Math.max(0, i - period + 1)
    let sum = 0
    for (let j = start; j <= i; j++) sum += (close[j] - mid[i]) ** 2
    const std = Math.sqrt(sum / (i - start + 1))
    upper.push(mid[i] + mult * std)
    lower.push(mid[i] - mult * std)
  }
  return { mid, upper, lower }
}

function calcVWAP(close: number[], volume: number[], period = 20) {
  const result: number[] = []
  for (let i = 0; i < close.length; i++) {
    const start = Math.max(0, i - period + 1)
    let cv = 0, tv = 0
    for (let j = start; j <= i; j++) { cv += close[j] * volume[j]; tv += volume[j] }
    result.push(tv > 0 ? cv / tv : close[i])
  }
  return result
}

self.onmessage = function (e: MessageEvent) {
  const { type, data } = e.data
  const close = data.close as number[]
  const high = data.high as number[]
  const low = data.low as number[]
  const volume = data.volume as number[]

  let result: any = null
  switch (type) {
    case 'macd': result = calcMACD(close); break
    case 'rsi': result = calcRSI(close); break
    case 'kdj': result = calcKDJ(high, low, close); break
    case 'boll': result = calcBOLL(close); break
    case 'vwap': result = calcVWAP(close, volume); break
    case 'ma': result = { ma5: calcMA(close, 5), ma10: calcMA(close, 10), ma20: calcMA(close, 20), ma60: calcMA(close, 60) }; break
    case 'all':
      result = {
        macd: calcMACD(close),
        rsi: calcRSI(close),
        kdj: calcKDJ(high, low, close),
        boll: calcBOLL(close),
        vwap: calcVWAP(close, volume),
        ma: { ma5: calcMA(close, 5), ma10: calcMA(close, 10), ma20: calcMA(close, 20), ma60: calcMA(close, 60) },
      }
      break
  }
  self.postMessage({ type, result })
}
