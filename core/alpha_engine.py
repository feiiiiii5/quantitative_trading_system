import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from core.factor_pipeline import winsorize, zscore_normalize, rank_normalize

logger = logging.getLogger(__name__)


@dataclass
class AlphaExpression:
    name: str
    expression: str
    category: str
    compute_fn: Callable[[pd.DataFrame], pd.Series]
    description: str = ""


@dataclass
class AlphaResult:
    name: str
    values: pd.Series
    ic: float = 0.0
    ic_ir: float = 0.0
    turnover: float = 0.0
    decay: float = 0.0
    passed: bool = False
    category: str = ""
    description: str = ""


def _safe_series(values, index) -> pd.Series:
    s = pd.Series(values, index=index, dtype=float)
    return s.replace([np.inf, -np.inf], np.nan)


class AlphaPrimitive:
    @staticmethod
    def returns(close: pd.Series, period: int = 1) -> pd.Series:
        return close.pct_change(period)

    @staticmethod
    def momentum(close: pd.Series, period: int = 20) -> pd.Series:
        return close / close.shift(period) - 1

    @staticmethod
    def volatility(close: pd.Series, period: int = 20) -> pd.Series:
        ret = close.pct_change()
        return ret.rolling(period).std()

    @staticmethod
    def volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
        ma = volume.rolling(period).mean()
        return volume / ma.replace(0, np.nan)

    @staticmethod
    def rank(series: pd.Series) -> pd.Series:
        return series.rank(pct=True)

    @staticmethod
    def zscore(series: pd.Series, period: int = 20) -> pd.Series:
        ma = series.rolling(period).mean()
        std = series.rolling(period).std()
        return (series - ma) / std.replace(0, np.nan)

    @staticmethod
    def delay(series: pd.Series, period: int = 1) -> pd.Series:
        return series.shift(period)

    @staticmethod
    def delta(series: pd.Series, period: int = 1) -> pd.Series:
        return series - series.shift(period)

    @staticmethod
    def ts_mean(series: pd.Series, period: int = 20) -> pd.Series:
        return series.rolling(period).mean()

    @staticmethod
    def ts_std(series: pd.Series, period: int = 20) -> pd.Series:
        return series.rolling(period).std()

    @staticmethod
    def ts_max(series: pd.Series, period: int = 20) -> pd.Series:
        return series.rolling(period).max()

    @staticmethod
    def ts_min(series: pd.Series, period: int = 20) -> pd.Series:
        return series.rolling(period).min()

    @staticmethod
    def ts_sum(series: pd.Series, period: int = 20) -> pd.Series:
        return series.rolling(period).sum()

    @staticmethod
    def ts_corr(x: pd.Series, y: pd.Series, period: int = 20) -> pd.Series:
        return x.rolling(period).corr(y)

    @staticmethod
    def ts_cov(x: pd.Series, y: pd.Series, period: int = 20) -> pd.Series:
        return x.rolling(period).cov(y)

    @staticmethod
    def ts_regression_residual(y: pd.Series, x: pd.Series, period: int = 20) -> pd.Series:
        result = pd.Series(np.nan, index=y.index, dtype=float)
        if len(y) < period or len(x) < period:
            return result
        for i in range(period - 1, len(y)):
            y_w = y.iloc[i - period + 1:i + 1].values
            x_w = x.iloc[i - period + 1:i + 1].values
            mask = np.isfinite(y_w) & np.isfinite(x_w)
            if mask.sum() < 3:
                continue
            y_c = y_w[mask]
            x_c = x_w[mask]
            x_mean = x_c.mean()
            y_mean = y_c.mean()
            denom = np.sum((x_c - x_mean) ** 2)
            if denom < 1e-12:
                continue
            beta = np.sum((x_c - x_mean) * (y_c - y_mean)) / denom
            alpha = y_mean - beta * x_mean
            result.iloc[i] = y_w[-1] - (alpha + beta * x_w[-1])
        return result

    @staticmethod
    def breakout(close: pd.Series, high: pd.Series, low: pd.Series, period: int = 20) -> pd.Series:
        hh = high.rolling(period).max()
        ll = low.rolling(period).min()
        range_val = hh - ll
        return (close - ll) / range_val.replace(0, np.nan)

    @staticmethod
    def mean_reversion(close: pd.Series, period: int = 20) -> pd.Series:
        ma = close.rolling(period).mean()
        std = close.rolling(period).std()
        return -(close - ma) / std.replace(0, np.nan)

    @staticmethod
    def rsi(close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = (-delta.clip(upper=0))
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return (100 - 100 / (1 + rs)).fillna(50)

    @staticmethod
    def macd_hist(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
        ema_f = close.ewm(span=fast, adjust=False).mean()
        ema_s = close.ewm(span=slow, adjust=False).mean()
        dif = ema_f - ema_s
        dea = dif.ewm(span=signal, adjust=False).mean()
        return (dif - dea) * 2


class AlphaGenerator:
    def __init__(self, config: dict = None):
        self._config = config or {}
        self._primitives = AlphaPrimitive()
        self._registry: Dict[str, AlphaExpression] = {}
        self._build_default_alphas()

    def _build_default_alphas(self):
        self.register(AlphaExpression(
            name="alpha_momentum_rank",
            expression="rank(momentum(close, 20))",
            category="momentum",
            compute_fn=lambda df: AlphaPrimitive.rank(AlphaPrimitive.momentum(df["close"], 20)),
            description="20日动量排名因子",
        ))
        self.register(AlphaExpression(
            name="alpha_momentum_rank_60",
            expression="rank(momentum(close, 60))",
            category="momentum",
            compute_fn=lambda df: AlphaPrimitive.rank(AlphaPrimitive.momentum(df["close"], 60)),
            description="60日动量排名因子",
        ))
        self.register(AlphaExpression(
            name="alpha_mean_reversion_zscore",
            expression="zscore(mean_reversion(close, 20))",
            category="mean_reversion",
            compute_fn=lambda df: AlphaPrimitive.zscore(AlphaPrimitive.mean_reversion(df["close"], 20)),
            description="20日均值回归Z-Score因子",
        ))
        self.register(AlphaExpression(
            name="alpha_mean_reversion_rank",
            expression="rank(mean_reversion(close, 10))",
            category="mean_reversion",
            compute_fn=lambda df: AlphaPrimitive.rank(AlphaPrimitive.mean_reversion(df["close"], 10)),
            description="10日均值回归排名因子",
        ))
        self.register(AlphaExpression(
            name="alpha_volatility_breakout",
            expression="breakout(close, high, low, 20)",
            category="breakout",
            compute_fn=lambda df: AlphaPrimitive.breakout(df["close"], df["high"], df["low"], 20),
            description="20日价格突破位置因子",
        ))
        self.register(AlphaExpression(
            name="alpha_residual_momentum",
            expression="residual(momentum(close, 20), volatility(close, 20))",
            category="residual",
            compute_fn=lambda df: AlphaPrimitive.ts_regression_residual(
                AlphaPrimitive.momentum(df["close"], 20),
                AlphaPrimitive.volatility(df["close"], 20),
                60,
            ),
            description="动量对波动率回归残差因子",
        ))
        self.register(AlphaExpression(
            name="alpha_volume_momentum",
            expression="rank(momentum(close, 10)) * volume_ratio(volume, 20)",
            category="volume_price",
            compute_fn=lambda df: AlphaPrimitive.rank(AlphaPrimitive.momentum(df["close"], 10)) * AlphaPrimitive.volume_ratio(df["volume"], 20),
            description="量价动量组合因子",
        ))
        self.register(AlphaExpression(
            name="alpha_rsi_contrarian",
            expression="-rank(rsi(close, 14))",
            category="mean_reversion",
            compute_fn=lambda df: -AlphaPrimitive.rank(AlphaPrimitive.rsi(df["close"], 14)),
            description="RSI逆向因子（RSI越高越看空）",
        ))
        self.register(AlphaExpression(
            name="alpha_macd_momentum",
            expression="rank(macd_hist(close))",
            category="momentum",
            compute_fn=lambda df: AlphaPrimitive.rank(AlphaPrimitive.macd_hist(df["close"])),
            description="MACD柱排名因子",
        ))
        self.register(AlphaExpression(
            name="alpha_vol_adjusted_momentum",
            expression="momentum(close, 20) / volatility(close, 20)",
            category="momentum",
            compute_fn=lambda df: AlphaPrimitive.momentum(df["close"], 20) / AlphaPrimitive.volatility(df["close"], 20).replace(0, np.nan),
            description="波动率调整动量因子（类似Sharpe）",
        ))
        self.register(AlphaExpression(
            name="alpha_ts_corr_price_vol",
            expression="ts_corr(close, volume, 20)",
            category="volume_price",
            compute_fn=lambda df: AlphaPrimitive.ts_corr(df["close"], df["volume"], 20),
            description="20日量价相关性因子",
        ))
        self.register(AlphaExpression(
            name="alpha_acceleration",
            expression="delta(momentum(close, 10), 5)",
            category="momentum",
            compute_fn=lambda df: AlphaPrimitive.delta(AlphaPrimitive.momentum(df["close"], 10), 5),
            description="动量加速度因子（动量的变化）",
        ))
        self.register(AlphaExpression(
            name="alpha_high_low_range",
            expression="rank((high - low) / ts_mean(high - low, 20))",
            category="volatility",
            compute_fn=lambda df: AlphaPrimitive.rank(
                (df["high"] - df["low"]) / AlphaPrimitive.ts_mean(df["high"] - df["low"], 20).replace(0, np.nan)
            ),
            description="日内振幅相对排名因子",
        ))
        self.register(AlphaExpression(
            name="alpha_volume_skew",
            expression="rank(volume * ts_std(close, 5) / ts_std(close, 20))",
            category="volume_price",
            compute_fn=lambda df: AlphaPrimitive.rank(
                df["volume"] * AlphaPrimitive.ts_std(df["close"], 5) / AlphaPrimitive.ts_std(df["close"], 20).replace(0, np.nan)
            ),
            description="量波比因子（短期波动/长期波动加权成交量）",
        ))
        self.register(AlphaExpression(
            name="alpha_mean_reversion_60",
            expression="zscore(mean_reversion(close, 60))",
            category="mean_reversion",
            compute_fn=lambda df: AlphaPrimitive.zscore(AlphaPrimitive.mean_reversion(df["close"], 60)),
            description="60日均值回归Z-Score因子",
        ))
        self.register(AlphaExpression(
            name="alpha_residual_return_vol",
            expression="residual(returns(close, 5), volatility(close, 20))",
            category="residual",
            compute_fn=lambda df: AlphaPrimitive.ts_regression_residual(
                AlphaPrimitive.returns(df["close"], 5),
                AlphaPrimitive.volatility(df["close"], 20),
                60,
            ),
            description="5日收益对波动率回归残差因子",
        ))

    def register(self, alpha: AlphaExpression) -> None:
        self._registry[alpha.name] = alpha

    def list_alphas(self) -> List[AlphaExpression]:
        return list(self._registry.values())

    def list_alpha_names(self) -> List[str]:
        return list(self._registry.keys())

    def compute_alpha(self, name: str, df: pd.DataFrame) -> Optional[pd.Series]:
        alpha = self._registry.get(name)
        if alpha is None:
            logger.warning(f"Alpha {name} not found in registry")
            return None
        try:
            values = alpha.compute_fn(df)
            values = winsorize(values)
            values = zscore_normalize(values)
            return values
        except Exception as e:
            logger.debug(f"Alpha {name} computation failed: {e}")
            return None

    def compute_all_alphas(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        results = {}
        for name in self._registry:
            values = self.compute_alpha(name, df)
            if values is not None and values.notna().sum() > 10:
                results[name] = values
        return results

    def generate_custom_alpha(
        self,
        name: str,
        expression: str,
        category: str,
        compute_fn: Callable[[pd.DataFrame], pd.Series],
        description: str = "",
    ) -> AlphaExpression:
        alpha = AlphaExpression(
            name=name,
            expression=expression,
            category=category,
            compute_fn=compute_fn,
            description=description,
        )
        self.register(alpha)
        return alpha

    def generate_parametric_alphas(
        self,
        df: pd.DataFrame,
        base_alphas: List[str] = None,
        periods: List[int] = None,
    ) -> Dict[str, pd.Series]:
        base_alphas = base_alphas or ["momentum", "mean_reversion", "volatility"]
        periods = periods or [5, 10, 20, 40, 60]
        results = {}

        for base in base_alphas:
            for p in periods:
                name = f"alpha_{base}_{p}"
                if name in self._registry:
                    values = self.compute_alpha(name, df)
                    if values is not None and values.notna().sum() > 10:
                        results[name] = values
                    continue

                if base == "momentum":
                    fn = lambda df_, pp=p: AlphaPrimitive.rank(AlphaPrimitive.momentum(df_["close"], pp))
                    desc = f"{p}日动量排名因子"
                elif base == "mean_reversion":
                    fn = lambda df_, pp=p: AlphaPrimitive.zscore(AlphaPrimitive.mean_reversion(df_["close"], pp))
                    desc = f"{p}日均值回归Z-Score因子"
                elif base == "volatility":
                    fn = lambda df_, pp=p: -AlphaPrimitive.rank(AlphaPrimitive.volatility(df_["close"], pp))
                    desc = f"{p}日低波动因子（波动率越低排名越高）"
                elif base == "breakout":
                    fn = lambda df_, pp=p: AlphaPrimitive.breakout(df_["close"], df_["high"], df_["low"], pp)
                    desc = f"{p}日突破位置因子"
                else:
                    continue

                self.register(AlphaExpression(
                    name=name,
                    expression=f"{base}(close, {p})",
                    category=base,
                    compute_fn=fn,
                    description=desc,
                ))
                values = self.compute_alpha(name, df)
                if values is not None and values.notna().sum() > 10:
                    results[name] = values

        return results
