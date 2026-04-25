import logging
import os
from dataclasses import dataclass, field
from typing import List

import numpy as np
import pandas as pd

from core.strategies import BaseStrategy, SignalType, TradeSignal, StrategyResult

logger = logging.getLogger(__name__)

_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "models")
os.makedirs(_MODEL_DIR, exist_ok=True)


@dataclass
class FeatureConfig:
    name: str
    function: str = ""
    params: dict = field(default_factory=dict)
    window: int = 0

    def to_dict(self) -> dict:
        return {"name": self.name, "function": self.function, "params": self.params, "window": self.window}


class FeatureEngineeringPipeline:
    def __init__(self):
        self._features: List[FeatureConfig] = []

    def add_feature(self, config: FeatureConfig):
        self._features.append(config)

    def add_default_features(self):
        defaults = [
            FeatureConfig("return_1d", "pct_change", {"period": 1}),
            FeatureConfig("return_5d", "pct_change", {"period": 5}),
            FeatureConfig("return_20d", "pct_change", {"period": 20}),
            FeatureConfig("volatility_10d", "rolling_std", {"window": 10}),
            FeatureConfig("volatility_20d", "rolling_std", {"window": 20}),
            FeatureConfig("ma5_ratio", "ma_ratio", {"period": 5}),
            FeatureConfig("ma20_ratio", "ma_ratio", {"period": 20}),
            FeatureConfig("rsi_14", "rsi", {"period": 14}),
            FeatureConfig("volume_ratio", "volume_ratio", {"window": 5}),
            FeatureConfig("atr_ratio", "atr_ratio", {"period": 14}),
            FeatureConfig("bb_position", "bb_position", {"period": 20}),
            FeatureConfig("momentum_10d", "momentum", {"period": 10}),
        ]
        self._features = defaults

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df

        df = df.copy()
        c = df["close"].values.astype(float) if "close" in df.columns else np.array([])
        h = df["high"].values.astype(float) if "high" in df.columns else np.array([])
        low_arr = df["low"].values.astype(float) if "low" in df.columns else np.array([])
        v = df["volume"].values.astype(float) if "volume" in df.columns else np.array([])

        for feat in self._features:
            try:
                if feat.function == "pct_change":
                    p = feat.params.get("period", 1)
                    df[feat.name] = pd.Series(c).pct_change(p).values
                elif feat.function == "rolling_std":
                    w = feat.params.get("window", 20)
                    rets = pd.Series(c).pct_change().values
                    df[feat.name] = pd.Series(rets).rolling(w).std().values
                elif feat.function == "ma_ratio":
                    p = feat.params.get("period", 20)
                    ma = pd.Series(c).rolling(p).mean().values
                    df[feat.name] = np.where(ma > 0, c / ma - 1, 0)
                elif feat.function == "rsi":
                    p = feat.params.get("period", 14)
                    delta = np.diff(c, prepend=c[0])
                    gain = np.where(delta > 0, delta, 0)
                    loss = np.where(delta < 0, -delta, 0)
                    avg_gain = pd.Series(gain).ewm(alpha=1/p, min_periods=p).mean().values
                    avg_loss = pd.Series(loss).ewm(alpha=1/p, min_periods=p).mean().values
                    rs = np.where(avg_loss != 0, avg_gain / avg_loss, 100)
                    df[feat.name] = 100 - 100 / (1 + rs)
                elif feat.function == "volume_ratio":
                    w = feat.params.get("window", 5)
                    avg_v = pd.Series(v).rolling(w).mean().values
                    df[feat.name] = np.where(avg_v > 0, v / avg_v, 1)
                elif feat.function == "atr_ratio":
                    p = feat.params.get("period", 14)
                    if len(h) > 0 and len(low_arr) > 0 and len(c) > 0:
                        tr = np.maximum(h - low_arr, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(low_arr - np.roll(c, 1))))
                        tr[0] = h[0] - low_arr[0] if len(h) > 0 else 0
                        atr = pd.Series(tr).rolling(p).mean().values
                        df[feat.name] = np.where(c > 0, atr / c, 0)
                elif feat.function == "bb_position":
                    p = feat.params.get("period", 20)
                    s = pd.Series(c)
                    mid = s.rolling(p).mean().values
                    std = s.rolling(p).std().values
                    upper = mid + 2 * std
                    lower = mid - 2 * std
                    diff = upper - lower
                    df[feat.name] = np.where(diff > 0, (c - lower) / diff, 0.5)
                elif feat.function == "momentum":
                    p = feat.params.get("period", 10)
                    df[feat.name] = np.where(c[:-p] > 0 if len(c) > p else False,
                                              c[p:] / c[:-p] - 1, 0) if len(c) > p else np.zeros(len(c))
            except Exception as e:
                logger.debug(f"Feature {feat.name} failed: {e}")

        return df

    def get_features(self) -> List[dict]:
        return [f.to_dict() for f in self._features]


class LightGBMStrategy(BaseStrategy):
    def __init__(self, target_period: int = 5, threshold: float = 0.02):
        super().__init__("LightGBM因子策略", "基于LightGBM多因子模型的预测策略")
        self.target_period = target_period
        self.threshold = threshold
        self._model = None
        self._pipeline = FeatureEngineeringPipeline()
        self._pipeline.add_default_features()

    def get_default_params(self) -> dict:
        return {"target_period": self.target_period, "threshold": self.threshold}

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        if not self._validate_df(df, 60):
            return StrategyResult(name=self.name, description=self.description)

        if self._model is None:
            self._load_model()

        featured = self._pipeline.transform(df)
        c = featured["close"].values.astype(float)

        if self._model is None:
            return self._rule_based_signals(featured, c)

        try:
            feature_cols = [col for col in featured.columns
                           if col not in ["date", "open", "high", "low", "close", "volume"]]
            X = featured[feature_cols].values
            X = np.nan_to_num(X, nan=0)
            if len(X) > 0:
                preds = self._model.predict(X[-1:])
                pred_return = preds[0]
                if pred_return > self.threshold:
                    return StrategyResult(
                        name=self.name, description=self.description,
                        score=min(80, pred_return * 1000),
                        current_signal=TradeSignal(
                            signal_type=SignalType.BUY, strength=min(pred_return * 10, 1.0),
                            reason=f"LightGBM预测收益: {pred_return:.4f}",
                            price=c[-1],
                        ),
                    )
                elif pred_return < -self.threshold:
                    return StrategyResult(
                        name=self.name, description=self.description,
                        score=max(-80, pred_return * 1000),
                        current_signal=TradeSignal(
                            signal_type=SignalType.SELL, strength=min(abs(pred_return) * 10, 1.0),
                            reason=f"LightGBM预测亏损: {pred_return:.4f}",
                            price=c[-1],
                        ),
                    )
        except Exception as e:
            logger.debug(f"LightGBM prediction failed: {e}")

        return StrategyResult(name=self.name, description=self.description)

    def _rule_based_signals(self, df: pd.DataFrame, c: np.ndarray) -> StrategyResult:
        score = 0.0
        reasons = []

        if "rsi_14" in df.columns:
            rsi = df["rsi_14"].values
            if not np.isnan(rsi[-1]):
                if rsi[-1] < 30:
                    score += 30
                    reasons.append(f"RSI超卖({rsi[-1]:.1f})")
                elif rsi[-1] > 70:
                    score -= 30
                    reasons.append(f"RSI超买({rsi[-1]:.1f})")

        if "bb_position" in df.columns:
            bb = df["bb_position"].values
            if not np.isnan(bb[-1]):
                if bb[-1] < 0.2:
                    score += 20
                    reasons.append("布林带下轨附近")
                elif bb[-1] > 0.8:
                    score -= 20
                    reasons.append("布林带上轨附近")

        if "ma5_ratio" in df.columns:
            mr = df["ma5_ratio"].values
            if not np.isnan(mr[-1]):
                if mr[-1] > 0.03:
                    score += 15
                    reasons.append("突破5日均线")
                elif mr[-1] < -0.03:
                    score -= 15

        current_signal = None
        if score > 20:
            current_signal = TradeSignal(
                signal_type=SignalType.BUY, strength=min(score / 100, 1.0),
                reason="; ".join(reasons), price=c[-1],
            )
        elif score < -20:
            current_signal = TradeSignal(
                signal_type=SignalType.SELL, strength=min(abs(score) / 100, 1.0),
                reason="; ".join(reasons), price=c[-1],
            )

        return StrategyResult(
            name=self.name, description=self.description,
            score=score, current_signal=current_signal,
            params=self.get_default_params(),
        )

    def train(self, df: pd.DataFrame) -> dict:
        featured = self._pipeline.transform(df)
        c = featured["close"].values.astype(float)

        if len(c) < self.target_period + 10:
            return {"success": False, "error": "数据不足"}

        future_returns = np.zeros(len(c))
        future_returns[:len(c) - self.target_period] = (
            c[self.target_period:] / c[:len(c) - self.target_period] - 1
        )
        featured["target"] = future_returns

        feature_cols = [col for col in featured.columns
                       if col not in ["date", "open", "high", "low", "close", "volume", "target"]]

        train_mask = featured["target"] != 0
        if train_mask.sum() < 50:
            return {"success": False, "error": "有效训练样本不足"}

        X = featured.loc[train_mask, feature_cols].values
        y = featured.loc[train_mask, "target"].values
        X = np.nan_to_num(X, nan=0)

        try:
            import lightgbm as lgb
            train_data = lgb.Dataset(X, y)
            params = {
                "objective": "regression",
                "metric": "mse",
                "verbosity": -1,
                "num_leaves": 31,
                "learning_rate": 0.05,
                "n_estimators": 100,
            }
            self._model = lgb.train(params, train_data, num_boost_round=100)
            self._save_model()
            return {"success": True, "samples": len(y), "features": len(feature_cols)}
        except ImportError:
            try:
                from sklearn.ensemble import GradientBoostingRegressor
                self._model = GradientBoostingRegressor(n_estimators=100, max_depth=5)
                self._model.fit(X, y)
                self._save_model()
                return {"success": True, "samples": len(y), "features": len(feature_cols), "model": "sklearn"}
            except ImportError:
                return {"success": False, "error": "需要安装lightgbm或scikit-learn"}

    def _save_model(self):
        if self._model is None:
            return
        try:
            import joblib
            path = os.path.join(_MODEL_DIR, "lightgbm_model.pkl")
            joblib.dump(self._model, path)
        except Exception as e:
            logger.debug(f"LightGBM model save failed: {e}")

    def _load_model(self):
        try:
            import joblib
            path = os.path.join(_MODEL_DIR, "lightgbm_model.pkl")
            if os.path.exists(path):
                self._model = joblib.load(path)
        except Exception as e:
            logger.debug(f"LightGBM model load failed: {e}")


class XGBoostStrategy(BaseStrategy):
    def __init__(self, target_period: int = 5, threshold: float = 0.02):
        super().__init__("XGBoost因子策略", "基于XGBoost多因子模型的预测策略")
        self.target_period = target_period
        self.threshold = threshold
        self._model = None
        self._pipeline = FeatureEngineeringPipeline()
        self._pipeline.add_default_features()

    def get_default_params(self) -> dict:
        return {"target_period": self.target_period, "threshold": self.threshold}

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        if not self._validate_df(df, 60):
            return StrategyResult(name=self.name, description=self.description)

        if self._model is None:
            self._load_model()

        featured = self._pipeline.transform(df)
        c = featured["close"].values.astype(float)

        if self._model is None:
            return StrategyResult(name=self.name, description=self.description, score=0)

        try:
            feature_cols = [col for col in featured.columns
                           if col not in ["date", "open", "high", "low", "close", "volume"]]
            X = featured[feature_cols].values
            X = np.nan_to_num(X, nan=0)
            if len(X) > 0:
                preds = self._model.predict(X[-1:])
                pred_return = preds[0]
                if pred_return > self.threshold:
                    return StrategyResult(
                        name=self.name, description=self.description,
                        score=min(80, pred_return * 1000),
                        current_signal=TradeSignal(
                            signal_type=SignalType.BUY, strength=min(pred_return * 10, 1.0),
                            reason=f"XGBoost预测收益: {pred_return:.4f}", price=c[-1],
                        ),
                    )
                elif pred_return < -self.threshold:
                    return StrategyResult(
                        name=self.name, description=self.description,
                        score=max(-80, pred_return * 1000),
                        current_signal=TradeSignal(
                            signal_type=SignalType.SELL, strength=min(abs(pred_return) * 10, 1.0),
                            reason=f"XGBoost预测亏损: {pred_return:.4f}", price=c[-1],
                        ),
                    )
        except Exception as e:
            logger.debug(f"XGBoost prediction failed: {e}")

        return StrategyResult(name=self.name, description=self.description)

    def train(self, df: pd.DataFrame) -> dict:
        featured = self._pipeline.transform(df)
        c = featured["close"].values.astype(float)

        if len(c) < self.target_period + 10:
            return {"success": False, "error": "数据不足"}

        future_returns = np.zeros(len(c))
        future_returns[:len(c) - self.target_period] = (
            c[self.target_period:] / c[:len(c) - self.target_period] - 1
        )
        featured["target"] = future_returns

        feature_cols = [col for col in featured.columns
                       if col not in ["date", "open", "high", "low", "close", "volume", "target"]]

        train_mask = featured["target"] != 0
        if train_mask.sum() < 50:
            return {"success": False, "error": "有效训练样本不足"}

        X = featured.loc[train_mask, feature_cols].values
        y = featured.loc[train_mask, "target"].values
        X = np.nan_to_num(X, nan=0)

        try:
            import xgboost as xgb
            self._model = xgb.XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.05)
            self._model.fit(X, y)
            self._save_model()
            return {"success": True, "samples": len(y), "features": len(feature_cols)}
        except ImportError:
            return {"success": False, "error": "需要安装xgboost"}

    def _save_model(self):
        if self._model is None:
            return
        try:
            import joblib
            path = os.path.join(_MODEL_DIR, "xgboost_model.pkl")
            joblib.dump(self._model, path)
        except Exception as e:
            logger.debug(f"XGBoost model save failed: {e}")

    def _load_model(self):
        try:
            import joblib
            path = os.path.join(_MODEL_DIR, "xgboost_model.pkl")
            if os.path.exists(path):
                self._model = joblib.load(path)
        except Exception as e:
            logger.debug(f"XGBoost model load failed: {e}")


class MLStrategyModule:
    def __init__(self):
        self.lgb_strategy = LightGBMStrategy()
        self.xgb_strategy = XGBoostStrategy()
        self._pipeline = FeatureEngineeringPipeline()
        self._pipeline.add_default_features()

    def get_feature_pipeline(self) -> FeatureEngineeringPipeline:
        return self._pipeline

    def train_model(self, df: pd.DataFrame, model_type: str = "lightgbm") -> dict:
        if model_type == "lightgbm":
            return self.lgb_strategy.train(df)
        elif model_type == "xgboost":
            return self.xgb_strategy.train(df)
        return {"success": False, "error": f"不支持的模型: {model_type}"}

    def get_available_models(self) -> List[dict]:
        models = [
            {"name": "lightgbm", "display_name": "LightGBM", "available": False},
            {"name": "xgboost", "display_name": "XGBoost", "available": False},
        ]
        import importlib
        models[0]["available"] = importlib.util.find_spec("lightgbm") is not None
        models[1]["available"] = importlib.util.find_spec("xgboost") is not None
        return models

    def get_features_info(self) -> List[dict]:
        return self._pipeline.get_features()
