import numpy as np
import pandas as pd


class TechnicalIndicators:

    @staticmethod
    def compute_all(df: pd.DataFrame) -> dict:
        if df is None or len(df) < 30:
            return {}
        c = df["close"].values.astype(float)
        h = df["high"].values.astype(float)
        l = df["low"].values.astype(float)
        v = df["volume"].values.astype(float) if "volume" in df.columns else np.zeros(len(df))

        ma = TechnicalIndicators._ma(c)
        ema = TechnicalIndicators._ema(c)
        boll = TechnicalIndicators._boll(c)
        macd = TechnicalIndicators._macd(c)
        supertrend = TechnicalIndicators._supertrend(h, l, c)
        ichimoku = TechnicalIndicators._ichimoku(h, l, c)

        rsi = TechnicalIndicators._rsi(c)
        kdj = TechnicalIndicators._kdj(h, l, c)
        cci = TechnicalIndicators._cci(h, l, c)
        williams_r = TechnicalIndicators._williams_r(h, l, c)
        roc = TechnicalIndicators._roc(c)

        vwap = TechnicalIndicators._vwap(h, l, c, v)
        obv = TechnicalIndicators._obv(c, v)
        volume_ratio = TechnicalIndicators._volume_ratio(v)
        cmf = TechnicalIndicators._cmf(h, l, c, v)

        atr = TechnicalIndicators._atr(h, l, c)
        hist_vol = TechnicalIndicators._hist_vol(c)
        bb_position = TechnicalIndicators._bb_position(c, boll)

        trend_score = TechnicalIndicators._trend_score(
            ma, ema, macd, rsi, kdj, cci, supertrend, boll, bb_position
        )
        signal = TechnicalIndicators._signal(trend_score)

        return {
            "ma": ma, "ema": ema, "boll": boll, "macd": macd,
            "supertrend": supertrend, "ichimoku": ichimoku,
            "rsi": rsi, "kdj": kdj, "cci": _last(cci),
            "williams_r": _last(williams_r), "roc": roc,
            "vwap": _last(vwap), "obv": _last(obv),
            "volume_ratio": _last(volume_ratio), "cmf": _last(cmf),
            "atr": _last(atr), "hist_vol": hist_vol,
            "bb_position": _last(bb_position),
            "trend_score": trend_score, "signal": signal,
        }

    @staticmethod
    def _ma(c: np.ndarray) -> dict:
        result = {}
        for p in [5, 10, 20, 60, 120]:
            if len(c) >= p:
                vals = pd.Series(c).rolling(p).mean().values
                result[p] = _to_list(vals)
        return result

    @staticmethod
    def _ema(c: np.ndarray) -> dict:
        result = {}
        for p in [12, 26]:
            s = pd.Series(c)
            vals = s.ewm(span=p, adjust=False).mean().values
            result[p] = _to_list(vals)
        return result

    @staticmethod
    def _boll(c: np.ndarray, period: int = 20, nbdev: float = 2.0) -> dict:
        s = pd.Series(c)
        mid = s.rolling(period).mean()
        std = s.rolling(period).std()
        upper = mid + nbdev * std
        lower = mid - nbdev * std
        width = ((upper - lower) / mid * 100).values
        return {
            "upper": _to_list(upper.values),
            "mid": _to_list(mid.values),
            "lower": _to_list(lower.values),
            "width": _to_list(width),
        }

    @staticmethod
    def _macd(c: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
        s = pd.Series(c)
        ema_fast = s.ewm(span=fast, adjust=False).mean()
        ema_slow = s.ewm(span=slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        hist = (dif - dea) * 2
        return {
            "dif": _to_list(dif.values),
            "dea": _to_list(dea.values),
            "hist": _to_list(hist.values),
        }

    @staticmethod
    def _supertrend(h: np.ndarray, l: np.ndarray, c: np.ndarray,
                    period: int = 10, multiplier: float = 3.0) -> dict:
        tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)),
                                           np.abs(l - np.roll(c, 1))))
        tr[0] = h[0] - l[0]
        atr = pd.Series(tr).rolling(period).mean().values
        n = len(c)
        upper_band = np.zeros(n)
        lower_band = np.zeros(n)
        supertrend = np.zeros(n)
        direction = np.ones(n)

        hl2 = (h + l) / 2
        upper_band = hl2 + multiplier * atr
        lower_band = hl2 - multiplier * atr

        for i in range(1, n):
            if np.isnan(atr[i]):
                supertrend[i] = np.nan
                continue
            if lower_band[i] > lower_band[i - 1] or c[i - 1] < lower_band[i - 1]:
                pass
            else:
                lower_band[i] = lower_band[i - 1]
            if upper_band[i] < upper_band[i - 1] or c[i - 1] > upper_band[i - 1]:
                pass
            else:
                upper_band[i] = upper_band[i - 1]
            if direction[i - 1] == 1:
                if c[i] < lower_band[i]:
                    direction[i] = -1
                    supertrend[i] = upper_band[i]
                else:
                    direction[i] = 1
                    supertrend[i] = lower_band[i]
            else:
                if c[i] > upper_band[i]:
                    direction[i] = 1
                    supertrend[i] = lower_band[i]
                else:
                    direction[i] = -1
                    supertrend[i] = upper_band[i]

        return {
            "value": _to_list(supertrend),
            "direction": _to_list(direction),
        }

    @staticmethod
    def _ichimoku(h: np.ndarray, l: np.ndarray, c: np.ndarray) -> dict:
        def _mid(high, low, period):
            roll_h = pd.Series(high).rolling(period).max()
            roll_l = pd.Series(low).rolling(period).min()
            return ((roll_h + roll_l) / 2).values

        tenkan = _mid(h, l, 9)
        kijun = _mid(h, l, 26)
        senkou_a = (tenkan + kijun) / 2
        senkou_b = _mid(h, l, 52)
        return {
            "tenkan": _to_list(tenkan),
            "kijun": _to_list(kijun),
            "senkou_a": _to_list(senkou_a),
            "senkou_b": _to_list(senkou_b),
        }

    @staticmethod
    def _rsi(c: np.ndarray) -> dict:
        result = {}
        for p in [6, 12, 24]:
            delta = np.diff(c, prepend=c[0])
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)
            avg_gain = pd.Series(gain).ewm(alpha=1 / p, min_periods=p).mean().values
            avg_loss = pd.Series(loss).ewm(alpha=1 / p, min_periods=p).mean().values
            rs = np.where(avg_loss != 0, avg_gain / avg_loss, 100)
            rsi_vals = 100 - 100 / (1 + rs)
            result[p] = _to_list(rsi_vals)
        return result

    @staticmethod
    def _kdj(h: np.ndarray, l: np.ndarray, c: np.ndarray,
             n: int = 9, m1: int = 3, m2: int = 3) -> dict:
        hh = pd.Series(h).rolling(n).max().values
        ll = pd.Series(l).rolling(n).min().values
        rsv = np.where(
            np.isfinite(hh) & np.isfinite(ll) & (hh != ll),
            (c - ll) / (hh - ll) * 100,
            50.0,
        )
        k = np.full(len(c), 50.0)
        d = np.full(len(c), 50.0)
        for i in range(1, len(c)):
            k[i] = (2 / m1) * k[i - 1] + (1 / m1) * rsv[i]
            d[i] = (2 / m2) * d[i - 1] + (1 / m2) * k[i]
        j = 3 * k - 2 * d
        return {"k": _to_list(k), "d": _to_list(d), "j": _to_list(j)}

    @staticmethod
    def _cci(h: np.ndarray, l: np.ndarray, c: np.ndarray, period: int = 14) -> np.ndarray:
        tp = (h + l + c) / 3
        ma = pd.Series(tp).rolling(period).mean().values
        md = pd.Series(tp).rolling(period).apply(
            lambda x: np.abs(x - x.mean()).mean(), raw=True
        ).values
        cci = np.where(np.isfinite(md) & (md != 0), (tp - ma) / (0.015 * md), 0)
        return cci

    @staticmethod
    def _williams_r(h: np.ndarray, l: np.ndarray, c: np.ndarray, period: int = 14) -> np.ndarray:
        hh = pd.Series(h).rolling(period).max().values
        ll = pd.Series(l).rolling(period).min().values
        wr = np.where(np.isfinite(hh) & np.isfinite(ll) & (hh != ll), (hh - c) / (hh - ll) * -100, -50)
        return wr

    @staticmethod
    def _roc(c: np.ndarray) -> dict:
        result = {}
        for p in [5, 10, 20]:
            vals = np.zeros(len(c))
            vals[p:] = (c[p:] - c[:-p]) / c[:-p] * 100
            result[p] = _to_list(vals)
        return result

    @staticmethod
    def _vwap(h: np.ndarray, l: np.ndarray, c: np.ndarray, v: np.ndarray) -> np.ndarray:
        tp = (h + l + c) / 3
        cum_tp_v = np.cumsum(tp * v)
        cum_v = np.cumsum(v)
        return np.where(cum_v != 0, cum_tp_v / cum_v, c)

    @staticmethod
    def _obv(c: np.ndarray, v: np.ndarray) -> np.ndarray:
        direction = np.sign(np.diff(c, prepend=c[0]))
        obv = np.cumsum(direction * v)
        return obv

    @staticmethod
    def _volume_ratio(v: np.ndarray, period: int = 5) -> np.ndarray:
        avg = pd.Series(v).rolling(period).mean().values
        return np.where(avg != 0, v / avg, 1)

    @staticmethod
    def _cmf(h: np.ndarray, l: np.ndarray, c: np.ndarray, v: np.ndarray,
             period: int = 20) -> np.ndarray:
        clv = np.where((h - l) != 0, ((c - l) - (h - c)) / (h - l), 0)
        mfv = clv * v
        cmf = pd.Series(mfv).rolling(period).sum() / pd.Series(v).rolling(period).sum()
        return cmf.values

    @staticmethod
    def _atr(h: np.ndarray, l: np.ndarray, c: np.ndarray, period: int = 14) -> np.ndarray:
        tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)),
                                           np.abs(l - np.roll(c, 1))))
        tr[0] = h[0] - l[0]
        return pd.Series(tr).ewm(alpha=1 / period, min_periods=period).mean().values

    @staticmethod
    def _hist_vol(c: np.ndarray) -> dict:
        log_ret = np.log(c[1:] / c[:-1])
        log_ret = np.insert(log_ret, 0, 0)
        result = {}
        for p in [10, 20, 60]:
            vol = pd.Series(log_ret).rolling(p).std().values * np.sqrt(252) * 100
            result[p] = _to_list(vol)
        return result

    @staticmethod
    def _bb_position(c: np.ndarray, boll: dict) -> np.ndarray:
        upper = np.array(boll["upper"])
        lower = np.array(boll["lower"])
        diff = upper - lower
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(diff != 0, (c - lower) / diff, 0.5)

    @staticmethod
    def _trend_score(ma, ema, macd, rsi, kdj, cci, supertrend, boll, bb_position) -> float:
        score = 0
        try:
            last_close_idx = -1
            if 5 in ma and 20 in ma:
                ma5_last = ma[5][last_close_idx]
                ma20_last = ma[20][last_close_idx]
                if not np.isnan(ma5_last) and not np.isnan(ma20_last):
                    score += 15 if ma5_last > ma20_last else -15
            if 10 in ma and 60 in ma:
                ma10_last = ma[10][last_close_idx]
                ma60_last = ma[60][last_close_idx]
                if not np.isnan(ma10_last) and not np.isnan(ma60_last):
                    score += 15 if ma10_last > ma60_last else -15
            if 12 in ema and 26 in ema:
                dif_last = macd["dif"][last_close_idx]
                dea_last = macd["dea"][last_close_idx]
                if not np.isnan(dif_last) and not np.isnan(dea_last):
                    score += 10 if dif_last > dea_last else -10
                    hist_last = macd["hist"][last_close_idx]
                    hist_prev = macd["hist"][-2] if len(macd["hist"]) > 1 else 0
                    if hist_last > hist_prev:
                        score += 5
                    else:
                        score -= 5
            for p in [6, 12, 24]:
                if p in rsi:
                    val = rsi[p][last_close_idx]
                    if not np.isnan(val):
                        if val > 70:
                            score -= 8
                        elif val > 50:
                            score += 5
                        elif val < 30:
                            score += 8
                        elif val < 50:
                            score -= 5
            k_last = kdj["k"][last_close_idx]
            d_last = kdj["d"][last_close_idx]
            if not np.isnan(k_last) and not np.isnan(d_last):
                if k_last > d_last:
                    score += 5
                else:
                    score -= 5
                if k_last > 80:
                    score -= 5
                elif k_last < 20:
                    score += 5
            cci_val = cci if isinstance(cci, (int, float)) else 0
            if cci_val > 100:
                score += 5
            elif cci_val < -100:
                score -= 5
            st_dir = supertrend.get("direction", [])
            if st_dir:
                score += 10 if st_dir[last_close_idx] == 1 else -10
            bb_pos = bb_position if isinstance(bb_position, (int, float)) else 0.5
            if bb_pos > 0.8:
                score -= 5
            elif bb_pos < 0.2:
                score += 5
        except (IndexError, KeyError, TypeError):
            pass
        return max(-100, min(100, score))

    @staticmethod
    def _signal(trend_score: float) -> str:
        if trend_score >= 50:
            return "strong_buy"
        elif trend_score >= 15:
            return "buy"
        elif trend_score <= -50:
            return "strong_sell"
        elif trend_score <= -15:
            return "sell"
        return "neutral"


def _to_list(arr) -> list:
    if isinstance(arr, np.ndarray):
        return np.nan_to_num(arr, nan=0).round(4).tolist()
    if isinstance(arr, pd.Series):
        return np.nan_to_num(arr.values, nan=0).round(4).tolist()
    return []


def _last(arr) -> float:
    try:
        if isinstance(arr, np.ndarray):
            val = arr[-1]
        elif isinstance(arr, list):
            val = arr[-1]
        else:
            return 0.0
        return round(float(val), 4) if not np.isnan(val) else 0.0
    except (IndexError, TypeError):
        return 0.0
