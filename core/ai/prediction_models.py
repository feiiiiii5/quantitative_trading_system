import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ModelPrediction:
    model_name: str
    symbol: str
    prediction: float = 0.0
    confidence: float = 0.0
    horizon: str = "1d"
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name, "symbol": self.symbol,
            "prediction": round(self.prediction, 4),
            "confidence": round(self.confidence, 4),
            "horizon": self.horizon, "timestamp": self.timestamp,
        }


@dataclass
class ABTestResult:
    model_a: str
    model_b: str
    metric: str
    score_a: float = 0.0
    score_b: float = 0.0
    winner: str = ""
    sample_size: int = 0

    def to_dict(self) -> dict:
        return {
            "model_a": self.model_a, "model_b": self.model_b,
            "metric": self.metric,
            "score_a": round(self.score_a, 4), "score_b": round(self.score_b, 4),
            "winner": self.winner, "sample_size": self.sample_size,
        }


class LSTMPredictor:
    def __init__(self, lookback: int = 20):
        self.lookback = lookback
        self._model = None

    def train(self, prices: np.ndarray) -> dict:
        if len(prices) < self.lookback + 10:
            return {"success": False, "error": "数据不足"}

        try:
            from sklearn.preprocessing import MinMaxScaler

            scaler = MinMaxScaler()
            scaled = scaler.fit_transform(prices.reshape(-1, 1))

            X, y = [], []
            for i in range(self.lookback, len(scaled)):
                X.append(scaled[i - self.lookback:i, 0])
                y.append(scaled[i, 0])
            X, y = np.array(X), np.array(y)

            import importlib.util
            if importlib.util.find_spec("tensorflow.keras.models") is None:
                return {"success": False, "error": "需要安装tensorflow"}
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import LSTM, Dense, Dropout

            X = X.reshape(X.shape[0], X.shape[1], 1)
            model = Sequential([
                LSTM(50, return_sequences=True, input_shape=(self.lookback, 1)),
                Dropout(0.2),
                LSTM(50),
                Dropout(0.2),
                Dense(1),
            ])
            model.compile(optimizer="adam", loss="mse")
            model.fit(X, y, epochs=10, batch_size=32, verbose=0)
            self._model = model
            self._scaler = scaler
            return {"success": True, "model": "lstm", "samples": len(y)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def predict(self, recent_prices: np.ndarray) -> Optional[float]:
        if self._model is None:
            return None
        try:
            scaled = self._scaler.transform(recent_prices[-self.lookback:].reshape(-1, 1))
            X = scaled.reshape(1, self.lookback, 1)
            pred = self._model.predict(X, verbose=0)
            return float(self._scaler.inverse_transform(pred)[0, 0])
        except Exception:
            return None


class GARCHPredictor:
    def __init__(self, p: int = 1, q: int = 1):
        self.p = p
        self.q = q
        self._model = None
        self._last_vol = 0.0

    def train(self, returns: np.ndarray) -> dict:
        if len(returns) < 100:
            return {"success": False, "error": "数据不足"}

        try:
            import arch
            model = arch.arch_model(returns * 100, vol="Garch", p=self.p, q=self.q)
            res = model.fit(disp="off")
            self._model = res
            self._last_vol = res.conditional_volatility[-1] / 100
            return {"success": True, "model": "garch", "last_vol": round(self._last_vol, 6)}
        except ImportError:
            self._last_vol = np.std(returns)
            return {"success": True, "model": "simple_vol", "last_vol": round(self._last_vol, 6)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def predict_volatility(self, horizon: int = 5) -> Optional[float]:
        if self._model is None:
            return self._last_vol if self._last_vol > 0 else None
        try:
            forecast = self._model.forecast(horizon=horizon)
            return float(np.mean(forecast.variance.iloc[-1]) ** 0.5 / 100)
        except Exception:
            return self._last_vol


class PredictionModelPlatform:
    def __init__(self):
        self._lstm = LSTMPredictor()
        self._garch = GARCHPredictor()
        self._predictions: Dict[str, List[ModelPrediction]] = {}
        self._ab_tests: List[ABTestResult] = []

    def get_available_models(self) -> List[dict]:
        models = [
            {"name": "lstm", "display": "LSTM", "available": False, "type": "price"},
            {"name": "garch", "display": "GARCH", "available": False, "type": "volatility"},
            {"name": "transformer", "display": "Transformer", "available": False, "type": "price"},
        ]
        import importlib.util
        models[0]["available"] = importlib.util.find_spec("tensorflow") is not None
        models[1]["available"] = importlib.util.find_spec("arch") is not None
        return models

    def train_model(self, model_name: str, data: np.ndarray, **kwargs) -> dict:
        if model_name == "lstm":
            lookback = kwargs.get("lookback", 20)
            self._lstm = LSTMPredictor(lookback=lookback)
            return self._lstm.train(data)
        elif model_name == "garch":
            p = kwargs.get("p", 1)
            q = kwargs.get("q", 1)
            self._garch = GARCHPredictor(p=p, q=q)
            return self._garch.train(data)
        return {"success": False, "error": f"不支持的模型: {model_name}"}

    def predict(self, model_name: str, data: np.ndarray, horizon: int = 5) -> dict:
        if model_name == "lstm":
            result = self._lstm.predict(data)
            if result is not None:
                pred = ModelPrediction(
                    model_name="lstm", symbol="",
                    prediction=result, confidence=0.5,
                    horizon=f"{horizon}d", timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                )
                return {"success": True, "prediction": pred.to_dict()}
            return {"success": False, "error": "LSTM模型未训练或预测失败"}
        elif model_name == "garch":
            vol = self._garch.predict_volatility(horizon)
            if vol is not None:
                pred = ModelPrediction(
                    model_name="garch", symbol="",
                    prediction=vol, confidence=0.6,
                    horizon=f"{horizon}d", timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                )
                return {"success": True, "prediction": pred.to_dict()}
            return {"success": False, "error": "GARCH模型未训练或预测失败"}
        return {"success": False, "error": f"不支持的模型: {model_name}"}

    def run_ab_test(
        self, model_a: str, model_b: str, data: np.ndarray, metric: str = "mse",
    ) -> dict:
        if len(data) < 20:
            return {"success": False, "error": "数据不足，至少需要20个数据点"}

        split = int(len(data) * 0.7)
        train_data = data[:split]
        test_data = data[split:]

        self.train_model(model_a, train_data)
        self.train_model(model_b, train_data)

        pred_a_result = self.predict(model_a, train_data, horizon=len(test_data))
        pred_b_result = self.predict(model_b, train_data, horizon=len(test_data))

        pred_a_val = pred_a_result.get("prediction", {}).get("prediction", 0)
        pred_b_val = pred_b_result.get("prediction", {}).get("prediction", 0)

        actual_mean = float(np.mean(test_data))

        if metric == "mse":
            score_a = float((pred_a_val - actual_mean) ** 2)
            score_b = float((pred_b_val - actual_mean) ** 2)
        elif metric == "mae":
            score_a = float(abs(pred_a_val - actual_mean))
            score_b = float(abs(pred_b_val - actual_mean))
        else:
            score_a = 0
            score_b = 0

        winner = model_a if score_a < score_b else model_b

        result = ABTestResult(
            model_a=model_a, model_b=model_b, metric=metric,
            score_a=score_a, score_b=score_b,
            winner=winner, sample_size=len(test_data),
        )
        self._ab_tests.append(result)

        return {"success": True, **result.to_dict()}

    def get_ab_results(self) -> List[dict]:
        return [t.to_dict() for t in self._ab_tests]

    def get_predictions(self, symbol: str) -> List[dict]:
        preds = self._predictions.get(symbol, [])
        return [p.to_dict() for p in preds[-20:]]
