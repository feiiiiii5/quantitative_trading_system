import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class CorrelationAnalyzer:
    """多股票相关性分析器，支持滚动相关、条件相关和组合分散度评估"""

    def __init__(self, lookback: int = 60):
        self._lookback = lookback

    def compute_correlation_matrix(
        self,
        price_data: dict[str, pd.Series],
        method: str = "pearson",
    ) -> dict:
        """计算多股票收益率相关系数矩阵

        Args:
            price_data: {symbol: price_series} 字典
            method: pearson / spearman / kendall

        Returns:
            包含矩阵、热力图数据和统计摘要的字典
        """
        if len(price_data) < 2:
            return {"error": "至少需要2只股票"}

        # 构建收益率DataFrame
        returns_dict = {}
        for symbol, prices in price_data.items():
            if len(prices) < 2:
                continue
            ret = prices.pct_change().dropna()
            if len(ret) > 0:
                returns_dict[symbol] = ret

        if len(returns_dict) < 2:
            return {"error": "有效收益率数据不足"}

        df = pd.DataFrame(returns_dict)
        # 对齐时间索引
        df = df.dropna()

        if len(df) < 10:
            return {"error": f"重叠数据点不足: {len(df)} < 10"}

        corr_matrix = df.corr(method=method)

        symbols = list(corr_matrix.columns)
        n = len(symbols)

        # 生成热力图数据（前端友好格式）
        heatmap = []
        for i in range(n):
            for j in range(n):
                heatmap.append({
                    "x": symbols[j],
                    "y": symbols[i],
                    "value": round(float(corr_matrix.iloc[i, j]), 4),
                })

        # 计算相关性统计摘要
        upper_tri = []
        for i in range(n):
            for j in range(i + 1, n):
                upper_tri.append(corr_matrix.iloc[i, j])

        avg_corr = float(np.mean(upper_tri))
        max_corr_pair = None
        min_corr_pair = None
        max_val = -2.0
        min_val = 2.0
        for i in range(n):
            for j in range(i + 1, n):
                v = float(corr_matrix.iloc[i, j])
                if v > max_val:
                    max_val = v
                    max_corr_pair = (symbols[i], symbols[j])
                if v < min_val:
                    min_val = v
                    min_corr_pair = (symbols[i], symbols[j])

        # 组合分散度评分（0-100，越高越分散）
        diversification_score = max(0, min(100, (1 - avg_corr) * 100))

        # 高相关对（>0.7）
        high_corr_pairs = []
        for i in range(n):
            for j in range(i + 1, n):
                v = float(corr_matrix.iloc[i, j])
                if abs(v) > 0.7:
                    high_corr_pairs.append({
                        "pair": f"{symbols[i]}-{symbols[j]}",
                        "correlation": round(v, 4),
                    })

        return {
            "symbols": symbols,
            "method": method,
            "matrix": {
                sym: {s: round(float(corr_matrix.loc[sym, s]), 4) for s in symbols}
                for sym in symbols
            },
            "heatmap": heatmap,
            "summary": {
                "avg_correlation": round(avg_corr, 4),
                "max_correlation": {
                    "pair": f"{max_corr_pair[0]}-{max_corr_pair[1]}" if max_corr_pair else None,
                    "value": round(max_val, 4),
                },
                "min_correlation": {
                    "pair": f"{min_corr_pair[0]}-{min_corr_pair[1]}" if min_corr_pair else None,
                    "value": round(min_val, 4),
                },
                "diversification_score": round(diversification_score, 1),
                "high_correlation_pairs": high_corr_pairs,
                "n_pairs": len(upper_tri),
            },
        }

    def compute_rolling_correlation(
        self,
        price_a: pd.Series,
        price_b: pd.Series,
        window: int = 60,
    ) -> dict:
        """计算两只股票的滚动相关系数

        Args:
            price_a: 股票A价格序列
            price_b: 股票B价格序列
            window: 滚动窗口大小

        Returns:
            滚动相关系数时间序列
        """
        ret_a = price_a.pct_change().dropna()
        ret_b = price_b.pct_change().dropna()

        # 对齐
        common_idx = ret_a.index.intersection(ret_b.index)
        if len(common_idx) < window + 5:
            return {"error": f"重叠数据不足: 需要{window + 5}，实际{len(common_idx)}"}

        ret_a = ret_a.loc[common_idx]
        ret_b = ret_b.loc[common_idx]

        rolling_corr = ret_a.rolling(window).corr(ret_b)
        rolling_corr = rolling_corr.dropna()

        # 降采样到最多200个点
        max_points = 200
        if len(rolling_corr) > max_points:
            step = len(rolling_corr) / max_points
            indices = [int(i * step) for i in range(max_points)]
            if indices[-1] != len(rolling_corr) - 1:
                indices.append(len(rolling_corr) - 1)
            rolling_corr = rolling_corr.iloc[indices]

        dates = [str(d)[:10] for d in rolling_corr.index]
        values = [round(float(v), 4) if np.isfinite(v) else None for v in rolling_corr.values]

        # 统计
        valid_values = [v for v in values if v is not None]
        return {
            "dates": dates,
            "values": values,
            "current": values[-1] if values else None,
            "mean": round(float(np.mean(valid_values)), 4) if valid_values else None,
            "std": round(float(np.std(valid_values)), 4) if valid_values else None,
            "regime": "high_corr" if (valid_values and valid_values[-1] > 0.7) else
                      ("low_corr" if (valid_values and valid_values[-1] < 0.3) else "moderate"),
        }

    def compute_diversification_score(
        self,
        price_data: dict[str, pd.Series],
    ) -> dict:
        """组合分散度深度评估：有效独立资产数(ENB)、条件分散收益(CDB)、尾部相关性

        Args:
            price_data: {symbol: price_series} 字典

        Returns:
            多维度分散度评估结果
        """
        if len(price_data) < 2:
            return {"error": "至少需要2只股票"}

        returns_dict = {}
        for symbol, prices in price_data.items():
            if len(prices) < 2:
                continue
            ret = prices.pct_change().dropna()
            if len(ret) > 0:
                returns_dict[symbol] = ret

        if len(returns_dict) < 2:
            return {"error": "有效收益率数据不足"}

        df = pd.DataFrame(returns_dict).dropna()
        if len(df) < 20:
            return {"error": f"重叠数据点不足: {len(df)} < 20"}

        corr_matrix = df.corr()
        symbols = list(corr_matrix.columns)
        n = len(symbols)

        upper_tri = [corr_matrix.iloc[i, j] for i in range(n) for j in range(i + 1, n)]
        avg_corr = float(np.mean(upper_tri)) if upper_tri else 0

        cov_matrix = df.cov().values
        eigenvalues = np.linalg.eigvalsh(cov_matrix)
        eigenvalues = eigenvalues[::-1]
        total_var = np.sum(eigenvalues)
        if total_var < 1e-12:
            return {"error": "协方差矩阵退化"}

        explained_ratio = eigenvalues / total_var
        enb = 1.0 / np.sum(explained_ratio ** 2) if np.sum(explained_ratio ** 2) > 1e-12 else 1.0

        downside_mask = df.mean(axis=1) < 0
        upside_mask = ~downside_mask
        downside_corr = avg_corr
        upside_corr = avg_corr
        if downside_mask.sum() > 10:
            ds_df = df.loc[downside_mask]
            if len(ds_df) > 5:
                ds_corr = ds_df.corr()
                ds_upper = [ds_corr.iloc[i, j] for i in range(n) for j in range(i + 1, n)]
                downside_corr = float(np.mean(ds_upper)) if ds_upper else avg_corr
        if upside_mask.sum() > 10:
            us_df = df.loc[upside_mask]
            if len(us_df) > 5:
                us_corr = us_df.corr()
                us_upper = [us_corr.iloc[i, j] for i in range(n) for j in range(i + 1, n)]
                upside_corr = float(np.mean(us_upper)) if us_upper else avg_corr

        try:
            cdb = upside_corr - downside_corr
        except Exception as e:
            logger.debug("CDB计算失败: %s", e)
            cdb = 0.0

        composite_score = (
            min(enb / n, 1.0) * 40 +
            (1 - avg_corr) * 30 +
            max(0, cdb) * 30
        )
        composite_score = max(0, min(100, composite_score))

        return {
            "symbols": symbols,
            "n_assets": n,
            "effective_number_of_bets": round(float(enb), 2),
            "enb_ratio": round(float(enb / n), 4),
            "avg_correlation": round(avg_corr, 4),
            "downside_correlation": round(float(downside_corr), 4),
            "upside_correlation": round(float(upside_corr), 4),
            "conditional_diversification_benefit": round(float(cdb), 4),
            "pca_explained_variance": [round(float(r), 4) for r in explained_ratio[:min(5, n)]],
            "composite_diversification_score": round(float(composite_score), 1),
            "rating": (
                "excellent" if composite_score > 75 else
                "good" if composite_score > 55 else
                "moderate" if composite_score > 35 else
                "poor"
            ),
        }

    def compute_beta_matrix(
        self,
        price_data: dict[str, pd.Series],
        benchmark: pd.Series,
    ) -> dict:
        """计算多股票相对基准的Beta矩阵

        Args:
            price_data: {symbol: price_series} 字典
            benchmark: 基准价格序列

        Returns:
            Beta值和系统性风险分析
        """
        bench_ret = benchmark.pct_change().dropna()
        results = {}

        for symbol, prices in price_data.items():
            ret = prices.pct_change().dropna()
            common_idx = ret.index.intersection(bench_ret.index)
            if len(common_idx) < 20:
                continue

            r = ret.loc[common_idx].values
            b = bench_ret.loc[common_idx].values

            bench_var = np.var(b)
            if bench_var < 1e-12:
                continue

            beta = float(np.cov(r, b)[0, 1] / bench_var)
            # R²
            corr = np.corrcoef(r, b)[0, 1]
            r_squared = corr ** 2
            # 特质波动率
            total_var = np.var(r)
            systematic_var = beta ** 2 * bench_var
            idio_var = max(0, total_var - systematic_var)
            idio_vol = float(np.sqrt(idio_var) * np.sqrt(252) * 100)

            results[symbol] = {
                "beta": round(beta, 4),
                "r_squared": round(float(r_squared), 4),
                "correlation": round(float(corr), 4),
                "idiosyncratic_volatility_pct": round(idio_vol, 2),
                "classification": (
                    "high_beta" if beta > 1.3 else
                    ("low_beta" if beta < 0.7 else "market_beta")
                ),
            }

        return {
            "benchmark": "provided",
            "betas": results,
            "summary": {
                "avg_beta": round(float(np.mean([v["beta"] for v in results.values()])), 4) if results else None,
                "high_beta_count": sum(1 for v in results.values() if v["beta"] > 1.3),
                "low_beta_count": sum(1 for v in results.values() if v["beta"] < 0.7),
            },
        }


# 全局单例
_analyzer: CorrelationAnalyzer | None = None


def get_correlation_analyzer() -> CorrelationAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = CorrelationAnalyzer()
    return _analyzer
