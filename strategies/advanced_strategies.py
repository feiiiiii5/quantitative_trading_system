#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级量化交易策略模块
包含业界领先的量化策略：
1. 多因子模型（Fama-French、CAPM扩展）
2. 机器学习预测模型（XGBoost、LightGBM、LSTM）
3. 高频交易算法（做市商、统计套利）
4. 自适应策略（市场状态识别、参数动态调整）
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
import warnings

from core.engine import BaseStrategy, Order
from utils.logger import get_logger

logger = get_logger(__name__)


class MarketRegime(Enum):
    """市场状态枚举"""
    BULL = "bull"           # 牛市
    BEAR = "bear"           # 熊市
    HIGH_VOL = "high_vol"   # 高波动
    LOW_VOL = "low_vol"     # 低波动
    TRENDING = "trending"    # 趋势市
    MEAN_REVERT = "mean_revert"  # 震荡市


@dataclass
class FactorConfig:
    """因子配置"""
    name: str
    enabled: bool = True
    weight: float = 1.0
    params: Dict = None


class MultiFactorStrategy(BaseStrategy):
    """
    多因子量化策略
    
    实现Fama-French五因子模型及扩展：
    - 市场因子 (MKT)
    - 规模因子 (SMB)  
    - 价值因子 (HML)
    - 盈利因子 (RMW)
    - 投资因子 (CMA)
    
    可扩展更多Alpha因子
    """
    
    def __init__(self, **kwargs):
        default_params = {
            # 因子权重
            'mkt_weight': 1.0,
            'smb_weight': 0.5,
            'hml_weight': 0.5,
            'rmw_weight': 0.3,
            'cma_weight': 0.3,
            
            # Alpha因子
            'momentum_weight': 0.5,
            'quality_weight': 0.3,
            'growth_weight': 0.2,
            
            # 交易参数
            'rebalance_period': 20,       # 再平衡周期
            'top_n': 20,                 # 持有top N只股票
            'min_stocks': 10,            # 最小持仓数量
            
            # 风控参数
            'max_weight_per_stock': 0.15, # 单只最大权重
            'max_turnover': 0.5,          # 最大换手率
        }
        
        if kwargs:
            default_params.update(kwargs)
        
        super().__init__(name="MultiFactor", parameters=default_params)
        
        # 因子数据
        self.factors = {}
        self.factor_returns = {}
        self.portfolio_weights = {}
        
        # 状态
        self.last_rebalance_idx = 0
    
    def init(self):
        """计算所有因子 - 从 self._data 获取数据"""
        if self._data is None:
            raise ValueError("策略数据未设置")
        
        logger.info("开始计算多因子模型...")
        data = self._data.data  # 获取底层DataFrame
        
        # 计算市场因子
        self._calculate_market_factor(data)
        
        # 计算风格因子
        self._calculate_style_factors(data)
        
        # 计算Alpha因子
        self._calculate_alpha_factors(data)
        
        # 计算因子收益率
        self._calculate_factor_returns(data)
        
        logger.info("多因子模型计算完成")
    
    def _calculate_market_factor(self, data: pd.DataFrame):
        """计算市场因子 (MKT) = 市场收益率 - 无风险利率"""
        # 日收益率
        returns = data['close'].pct_change()
        
        # 市场因子 = 收益率本身（简化版，假设无风险利率为0）
        self.factors['mkt'] = returns
        
        # 也可以使用市场指数收益率作为市场因子
        # self.factors['mkt'] = market_returns
    
    def _calculate_style_factors(self, data: pd.DataFrame):
        """
        计算风格因子
        
        SMB (Small Minus Big): 小市值因子
        HML (High Minus Low): 价值因子（高PE vs 低PE）
        RMW (Robust Minus Weak): 盈利因子
        CMA (Conservative Minus Aggressive): 投资因子
        """
        close = data['close']
        volume = data['volume']
        
        # 规模因子：使用成交量作为规模的代理指标
        # 实际应用中需要使用市值数据
        avg_volume = volume.rolling(window=20).mean()
        self.factors['smb'] = -np.sign(avg_volume - avg_volume.mean())  # 小市值预期正收益
        
        # 价值因子：使用价格动量作为价值的代理
        # 实际应用中使用PB、PE等
        price_change = close.pct_change(20)
        self.factors['hml'] = price_change
        
        # 盈利因子：使用波动率作为盈利质量的代理
        volatility = close.rolling(window=20).std()
        self.factors['rmw'] = 1 / (volatility + 0.001)  # 低波动=高质量
        
        # 投资因子：使用成交量变化作为投资活跃度代理
        volume_change = volume.pct_change(10)
        self.factors['cma'] = -volume_change  # 低投资=保守
    
    def _calculate_alpha_factors(self, data: pd.DataFrame):
        """计算Alpha因子（超额收益来源）"""
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # 动量因子 (Momentum)
        momentum_20 = close.pct_change(20)
        momentum_60 = close.pct_change(60)
        self.factors['momentum'] = 0.6 * momentum_20 + 0.4 * momentum_60
        
        # 质量因子 (Quality)
        # 使用ROE、毛利率等代理指标
        returns = close.pct_change()
        self.factors['quality'] = returns.rolling(window=20).mean() / (returns.rolling(window=20).std() + 0.001)
        
        # 成长因子 (Growth)
        # 使用收入增长、利润增长等
        ma5 = close.rolling(window=5).mean()
        ma20 = close.rolling(window=20).mean()
        self.factors['growth'] = (ma5 - ma20) / ma20
    
    def _calculate_factor_returns(self, data: pd.DataFrame):
        """计算因子收益率（回归方法）"""
        # 简化：使用因子自身收益率
        # 实际应用中需要用因子暴露度进行加权回归
        for name, factor in self.factors.items():
            self.factor_returns[name] = factor
    
    def next(self, index: int) -> Optional[Order]:
        """每周期执行逻辑 - 通过 self._data.close.iloc[index] 访问当前价格"""
        params = self.parameters
        
        # 检查是否需要再平衡
        should_rebalance = (index - self.last_rebalance_idx) >= params['rebalance_period']
        
        if should_rebalance:
            self.last_rebalance_idx = index
            return self._generate_rebalance_signal(index)
        
        return None
    
    def _generate_rebalance_signal(self, index: int) -> Optional[Order]:
        """生成再平衡信号"""
        params = self.parameters
        
        # 计算综合因子得分
        score = self._calculate_composite_score(index)
        
        # 选择得分最高的股票
        if score is None or len(score) == 0:
            return None
        
        top_indices = score.nlargest(min(params['top_n'], len(score))).index
        
        # 计算目标权重
        target_weights = {}
        for idx in top_indices:
            weight = 1.0 / len(top_indices)
            weight = min(weight, params['max_weight_per_stock'])
            target_weights[idx] = weight
        
        # 归一化权重
        total_weight = sum(target_weights.values())
        if total_weight > 0:
            target_weights = {k: v/total_weight for k, v in target_weights.items()}
        
        # 生成交易信号
        current_position = self._position
        
        if current_position <= 0:  # 空仓或低仓
            return self.buy(
                symbol=self._data.name if self._data else "",
                quantity=sum(target_weights.values()) * 1000,
                reason="因子选股再平衡"
            )
        elif current_position > 0:  # 有持仓
            # 可能有减仓信号
            if len(target_weights) < params['min_stocks']:
                return self.sell(
                    symbol=self._data.name if self._data else "",
                    quantity=self._position * 0.3,
                    reason="降低持仓数量"
                )
        
        return None
    
    def _calculate_composite_score(self, index: int) -> pd.Series:
        """计算综合因子得分"""
        params = self.parameters
        
        if index < 60:
            return pd.Series()
        
        score = pd.Series(0.0, index=[index])
        
        # 累加各因子得分
        if 'mkt' in self.factors:
            score += params['mkt_weight'] * self.factors['mkt'].iloc[index]
        
        if 'momentum' in self.factors:
            score += params['momentum_weight'] * self.factors['momentum'].iloc[index]
        
        if 'quality' in self.factors:
            score += params['quality_weight'] * self.factors['quality'].iloc[index]
        
        if 'growth' in self.factors:
            score += params['growth_weight'] * self.factors['growth'].iloc[index]
        
        return score


class AdaptiveMarketRegimeStrategy(BaseStrategy):
    """
    自适应市场状态策略
    
    自动识别市场状态并切换对应最优策略：
    - 趋势跟踪（趋势市）
    - 均值回归（震荡市）
    - 高波动保护（高波动市）
    - 低波动增持（低波动市）
    """
    
    def __init__(self, **kwargs):
        default_params = {
            # 市场状态识别参数
            'vol_window': 20,              # 波动率计算窗口
            'trend_window': 50,            # 趋势判断窗口
            'regime_threshold_vol': 0.02,  # 波动率状态阈值
            'regime_threshold_trend': 0.0, # 趋势状态阈值
            
            # 策略权重
            'trend_weight': 0.6,           # 趋势策略权重
            'mean_revert_weight': 0.4,     # 均值回归权重
            
            # 子策略参数
            'atr_period': 14,              # ATR周期
            'rsi_period': 14,              # RSI周期
            'bb_period': 20,               # 布林带周期
        }
        
        if kwargs:
            default_params.update(kwargs)
        
        super().__init__(name="AdaptiveRegime", parameters=default_params)
        
        # 子策略指标
        self.current_regime = None
        self.regime_history = []
        
        # 子策略指标
        self.atr = None
        self.rsi = None
        self.bb_upper = None
        self.bb_lower = None
        self.trend_ma = None
    
    def init(self):
        """计算所有指标 - 从 self._data 获取数据"""
        if self._data is None:
            raise ValueError("策略数据未设置")
        
        params = self.parameters
        data = self._data.data
        
        high = data['high']
        low = data['low']
        close = data['close']
        
        # 计算ATR
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        self.atr = tr.rolling(window=params['atr_period']).mean()
        
        # 计算RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=params['rsi_period']).mean()
        avg_loss = loss.rolling(window=params['rsi_period']).mean()
        rs = avg_gain / (avg_loss + 0.001)
        self.rsi = 100 - (100 / (1 + rs))
        
        # 计算布林带
        bb_ma = close.rolling(window=params['bb_period']).mean()
        bb_std = close.rolling(window=params['bb_period']).std()
        self.bb_upper = bb_ma + 2 * bb_std
        self.bb_lower = bb_ma - 2 * bb_std
        
        # 计算趋势线
        self.trend_ma = close.rolling(window=params['trend_window']).mean()
        
        logger.info("自适应策略指标计算完成")
    
    def next(self, index: int) -> Optional[Order]:
        """执行逻辑 - 通过 self._data.close.iloc[index] 访问当前价格"""
        if index < max(self.parameters['vol_window'], self.parameters['trend_window']):
            return None
        
        # 识别市场状态
        regime = self._identify_market_regime(index)
        
        # 根据状态选择策略
        if regime == MarketRegime.TRENDING:
            return self._trend_following_signal(index)
        elif regime == MarketRegime.MEAN_REVERT:
            return self._mean_revert_signal(index)
        elif regime == MarketRegime.HIGH_VOL:
            return self._high_volatility_signal(index)
        elif regime == MarketRegime.LOW_VOL:
            return self._low_volatility_signal(index)
        else:
            return None
    
    def _identify_market_regime(self, index: int) -> MarketRegime:
        """识别市场状态"""
        params = self.parameters
        close = self._data.close.iloc[index]
        
        # 计算波动率状态
        recent_vol = self.atr.iloc[index] / self.trend_ma.iloc[index] if index > 0 else 0
        
        # 计算趋势强度
        trend_strength = (close - self.trend_ma.iloc[index]) / self.trend_ma.iloc[index] if index > 0 else 0
        
        # 判断状态
        if recent_vol > params['regime_threshold_vol']:
            regime = MarketRegime.HIGH_VOL
        elif recent_vol < params['regime_threshold_vol'] * 0.5:
            regime = MarketRegime.LOW_VOL
        elif abs(trend_strength) > params['regime_threshold_trend']:
            regime = MarketRegime.TRENDING
        else:
            regime = MarketRegime.MEAN_REVERT
        
        self.current_regime = regime
        self.regime_history.append(regime)
        
        return regime
    
    def _trend_following_signal(self, index: int) -> Optional[Order]:
        """趋势跟踪信号"""
        close = self._data.close.iloc[index]
        
        # 使用均线金叉死叉
        if index > self.parameters['trend_window']:
            prev_trend = (self._data.close.iloc[index-1] - self.trend_ma.iloc[index-1]) / self.trend_ma.iloc[index-1]
            curr_trend = (close - self.trend_ma.iloc[index]) / self.trend_ma.iloc[index]
            
            if prev_trend < 0 and curr_trend > 0:
                return self.buy(
                    symbol=self._data.name if self._data else "",
                    quantity=800,
                    reason="趋势市-向上突破"
                )
            elif prev_trend > 0 and curr_trend < 0:
                return self.sell(
                    symbol=self._data.name if self._data else "",
                    quantity=self._position,
                    reason="趋势市-向下突破"
                )
        
        return None
    
    def _mean_revert_signal(self, index: int) -> Optional[Order]:
        """均值回归信号"""
        close = self._data.close.iloc[index]
        
        # 使用布林带
        upper = self.bb_upper.iloc[index]
        lower = self.bb_lower.iloc[index]
        
        if close <= lower:
            return self.buy(
                symbol=self._data.name if self._data else "",
                quantity=600,
                reason="震荡市-触及下轨"
            )
        elif close >= upper:
            return self.sell(
                symbol=self._data.name if self._data else "",
                quantity=self._position * 0.6,
                reason="震荡市-触及上轨"
            )
        
        return None
    
    def _high_volatility_signal(self, index: int) -> Optional[Order]:
        """高波动市信号 - 降低仓位"""
        # RSI超买超卖
        rsi = self.rsi.iloc[index]
        
        if rsi < 30:
            return self.buy(
                symbol=self._data.name if self._data else "",
                quantity=300,
                reason="高波动-超卖反弹"
            )  # 轻仓
        elif rsi > 70:
            return self.sell(
                symbol=self._data.name if self._data else "",
                quantity=self._position * 0.5,
                reason="高波动-超买减仓"
            )
        
        return None
    
    def _low_volatility_signal(self, index: int) -> Optional[Order]:
        """低波动市信号 - 可适度加仓"""
        rsi = self.rsi.iloc[index]
        
        if rsi < 40:
            return self.buy(
                symbol=self._data.name if self._data else "",
                quantity=700,
                reason="低波动-逢低加仓"
            )
        elif rsi > 60:
            return self.sell(
                symbol=self._data.name if self._data else "",
                quantity=self._position * 0.3,
                reason="低波动-适度减仓"
            )
        
        return None


class MachineLearningStrategy(BaseStrategy):
    """
    机器学习预测策略
    
    使用XGBoost/LightGBM进行价格方向预测：
    - 特征工程：技术指标、市场情绪、宏观因子
    - 模型训练：滚动窗口训练
    - 预测信号：分类输出（涨/跌/震荡）
    """
    
    def __init__(self, **kwargs):
        default_params = {
            # 模型参数
            'model_type': 'xgboost',     # xgboost 或 lightgbm
            'lookback': 60,              # 回看窗口
            'forward_periods': 5,         # 预测周期
            
            # 训练参数
            'train_window': 252,         # 训练窗口（一年）
            'retrain_interval': 20,      # 再训练间隔
            'min_samples': 100,           # 最小样本数
            
            # 交易参数
            'confidence_threshold': 0.6, # 置信度阈值
            'position_size': 0.8,        # 仓位大小
        }
        
        if kwargs:
            default_params.update(kwargs)
        
        super().__init__(name="MLPrediction", parameters=default_params)
        
        self.model = None
        self.feature_columns = []
        self.last_train_idx = 0
        self.feature_data = None
        self.labels = None
    
    def init(self):
        """构建特征 - 从 self._data 获取数据"""
        if self._data is None:
            raise ValueError("策略数据未设置")
        
        logger.info("构建机器学习特征...")
        
        params = self.parameters
        data = self._data.data
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        features = pd.DataFrame(index=data.index)
        
        # 价格特征
        features['returns_1d'] = close.pct_change(1)
        features['returns_5d'] = close.pct_change(5)
        features['returns_10d'] = close.pct_change(10)
        features['returns_20d'] = close.pct_change(20)
        
        # 波动率特征
        features['volatility_5d'] = close.pct_change().rolling(5).std()
        features['volatility_20d'] = close.pct_change().rolling(20).std()
        
        # 趋势特征
        ma5 = close.rolling(5).mean()
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()
        
        features['ma5_ratio'] = close / ma5 - 1
        features['ma20_ratio'] = close / ma20 - 1
        features['ma60_ratio'] = close / ma60 - 1
        features['ma_crossover'] = (ma5 > ma20).astype(int)
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 0.001)
        features['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9).mean()
        features['macd'] = macd
        features['macd_signal'] = signal
        features['macd_hist'] = macd - signal
        
        # 成交量特征
        features['volume_ratio'] = volume / volume.rolling(20).mean()
        features['volume_ma5'] = volume.rolling(5).mean()
        
        # 布林带
        bb_ma = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        features['bb_position'] = (close - bb_ma) / (2 * bb_std + 0.001)
        
        # ATR
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        features['atr'] = tr.rolling(14).mean()
        
        self.feature_data = features.dropna()
        self.feature_columns = self.feature_data.columns.tolist()
        
        # 构建标签（未来收益方向）- 与 feature_data 对齐索引
        self.labels = self._create_labels(close)
        self.labels = self.labels.loc[self.feature_data.index]
        
        logger.info(f"特征构建完成，共 {len(self.feature_columns)} 个特征")
    
    def _create_labels(self, close: pd.Series) -> pd.Series:
        """创建标签"""
        params = self.parameters
        
        # 计算未来收益
        future_returns = close.pct_change(params['forward_periods']).shift(-params['forward_periods'])
        
        # 分类标签：1=涨, 0=震荡, -1=跌
        labels = pd.Series(0, index=future_returns.index)
        labels[future_returns > 0.01] = 1      # 涨幅超过1%
        labels[future_returns < -0.01] = -1    # 跌幅超过1%
        
        return labels
    
    def _train_model(self, train_data: pd.DataFrame, train_labels: pd.Series):
        """训练模型"""
        params = self.parameters
        
        try:
            if params['model_type'] == 'xgboost':
                import xgboost as xgb
                
                self.model = xgb.XGBClassifier(
                    n_estimators=100,
                    max_depth=5,
                    learning_rate=0.1,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    random_state=42
                )
            else:
                import lightgbm as lgb
                
                self.model = lgb.LGBMClassifier(
                    n_estimators=100,
                    max_depth=5,
                    learning_rate=0.1,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    random_state=42,
                    verbose=-1
                )
            
            self.model.fit(train_data, train_labels)
            logger.info("模型训练完成")
            
        except ImportError as e:
            logger.warning(f"未安装机器学习库: {e}，使用简化规则")
            self.model = None
    
    def next(self, index: int) -> Optional[Order]:
        """执行逻辑"""
        params = self.parameters
        
        if index < params['lookback']:
            return None
        
        # 定期重新训练
        if index - self.last_train_idx >= params['retrain_interval']:
            self._retrain_model(index)
            self.last_train_idx = index
        
        # 获取特征
        feature_vec = self._get_features(index)
        
        if feature_vec is None:
            return None
        
        # 预测
        prediction = self._predict(feature_vec)
        
        # 生成信号
        if prediction == 1 and self._position <= 0:
            return self.buy(
                symbol=self._data.name if self._data else "",
                quantity=params['position_size'] * 1000,
                reason="ML预测上涨"
            )
        elif prediction == -1 and self._position > 0:
            return self.sell(
                symbol=self._data.name if self._data else "",
                quantity=self._position,
                reason="ML预测下跌"
            )
        
        return None
    
    def _get_features(self, index: int) -> Optional[np.ndarray]:
        """获取特征向量"""
        if self.feature_data is None:
            return None
        
        try:
            # 使用位置索引获取对应行的特征
            if index < len(self.feature_data):
                features = self.feature_data.iloc[index].values
                # 检查是否有NaN
                if np.any(np.isnan(features)):
                    return None
                return features.reshape(1, -1)
            return None
        except Exception:
            return None
    
    def _predict(self, features: np.ndarray) -> int:
        """预测"""
        if self.model is None:
            # 简化规则：使用RSI
            try:
                rsi_idx = self.feature_columns.index('rsi')
                rsi = features[0, rsi_idx]
                
                if rsi < 30:
                    return 1
                elif rsi > 70:
                    return -1
                else:
                    return 0
            except (ValueError, IndexError):
                # 如果没有RSI特征，默认观望
                return 0
        
        proba = self.model.predict_proba(features)
        confidence = proba.max()
        
        if confidence < self.parameters['confidence_threshold']:
            return 0  # 低置信度，观望
        
        pred = self.model.predict(features)[0]
        return int(pred)
    
    def _retrain_model(self, current_idx: int):
        """重新训练模型"""
        params = self.parameters
        
        start_idx = max(0, current_idx - params['train_window'])
        
        train_data = self.feature_data.iloc[start_idx:current_idx]
        train_labels = self.labels.iloc[start_idx:current_idx]
        
        # 过滤无效标签（对齐索引）
        valid_mask = (train_labels != 0).values
        train_data = train_data[valid_mask]
        train_labels = train_labels[valid_mask]
        
        if len(train_data) >= params['min_samples']:
            self._train_model(train_data, train_labels)
        else:
            logger.warning(f"样本不足，跳过训练: {len(train_data)} < {params['min_samples']}")


class StatisticalArbitrageStrategy(BaseStrategy):
    """
    统计套利策略
    
    利用相关性资产间的价差回归特性：
    - 配对交易
    - 均值回归
    - 协整检验
    """
    
    def __init__(self, **kwargs):
        default_params = {
            # 配对参数
            'pair_stock': None,           # 配对股票代码
            'lookback_window': 60,        # 相关性计算窗口
            
            # 交易参数
            'entry_zscore': 2.0,          # 入场Z-score阈值
            'exit_zscore': 0.5,           # 出场Z-score阈值
            'position_size': 0.5,         # 单次仓位
            
            # 风控
            'max_holding_days': 20,       # 最大持仓天数
            'stop_loss_zscore': 3.0,      # 止损Z-score
        }
        
        if kwargs:
            default_params.update(kwargs)
        
        super().__init__(name="StatArb", parameters=default_params)
        
        self.pair_spread = None
        self.hedge_ratio = 1.0
        self.entry_price = None
        self.holding_days = 0
    
    def init(self):
        """计算价差序列 - 从 self._data 获取数据"""
        if self._data is None:
            raise ValueError("策略数据未设置")
        
        data = self._data.data
        
        # 如果有配对股票，计算价差
        if self.parameters['pair_stock'] is not None:
            logger.info("计算配对交易价差...")
            # 简化：使用自身数据模拟配对
            # 实际应用中需要获取配对股票数据
            self.pair_spread = data['close'] / data['close'].rolling(20).mean()
        else:
            self.pair_spread = data['close']
    
    def next(self, index: int) -> Optional[Order]:
        """执行逻辑"""
        params = self.parameters
        
        if index < params['lookback_window']:
            return None
        
        # 计算Z-score
        mean = self.pair_spread.iloc[index-params['lookback_window']:index].mean()
        std = self.pair_spread.iloc[index-params['lookback_window']:index].std()
        zscore = (self.pair_spread.iloc[index] - mean) / (std + 0.001)
        
        # 交易逻辑
        if self._position == 0:
            # 无持仓
            if zscore > params['entry_zscore']:
                # 价差过高，预期回归，做空价差
                return self.sell(
                    symbol=self._data.name if self._data else "",
                    quantity=params['position_size'] * 1000,
                    reason=f"套利-Z={zscore:.2f}"
                )
            elif zscore < -params['entry_zscore']:
                # 价差过低，预期回归，做多价差
                return self.buy(
                    symbol=self._data.name if self._data else "",
                    quantity=params['position_size'] * 1000,
                    reason=f"套利-Z={zscore:.2f}"
                )
        
        elif self._position > 0:
            # 持有多头
            self.holding_days += 1
            
            if zscore > -params['exit_zscore'] or zscore < -params['stop_loss_zscore']:
                return self.sell(
                    symbol=self._data.name if self._data else "",
                    quantity=self._position,
                    reason="套利平仓"
                )
            
            if self.holding_days >= params['max_holding_days']:
                return self.sell(
                    symbol=self._data.name if self._data else "",
                    quantity=self._position,
                    reason="到期平仓"
                )
        
        elif self._position < 0:
            # 持有空头
            self.holding_days += 1
            
            if zscore < params['exit_zscore'] or zscore > params['stop_loss_zscore']:
                return self.buy(
                    symbol=self._data.name if self._data else "",
                    quantity=abs(self._position),
                    reason="套利平仓"
                )
            
            if self.holding_days >= params['max_holding_days']:
                return self.buy(
                    symbol=self._data.name if self._data else "",
                    quantity=abs(self._position),
                    reason="到期平仓"
                )
        
        return None


class MarketMakingStrategy(BaseStrategy):
    """
    做市商策略
    
    为市场提供流动性，赚取买卖价差：
    - 挂单管理
    - 价差动态调整
    - 库存风险管理
    """
    
    def __init__(self, **kwargs):
        default_params = {
            # 价差参数
            'base_spread': 0.001,         # 基础价差（0.1%）
            'min_spread': 0.0005,          # 最小价差
            'max_spread': 0.005,           # 最大价差
            
            # 挂单参数
            'order_size': 100,             # 挂单数量
            'cancel_threshold': 0.002,     # 撤单阈值
            
            # 风控
            'max_position': 10000,         # 最大持仓
            'inventory_limit': 50000,      # 库存限额
        }
        
        if kwargs:
            default_params.update(kwargs)
        
        super().__init__(name="MarketMaking", parameters=default_params)
        
        self.bid_orders = []
        self.ask_orders = []
        self.inventory = 0
        self.pnl = 0
    
    def init(self):
        """初始化 - 从 self._data 获取数据"""
        if self._data is None:
            raise ValueError("策略数据未设置")
        
        data = self._data.data
        # 计算市场特征用于动态价差
        self.returns = data['close'].pct_change()
        self.volatility = self.returns.rolling(20).std()
        logger.info("做市商策略初始化完成")
    
    def next(self, index: int) -> Optional[Order]:
        """执行逻辑"""
        params = self.parameters
        
        mid_price = self._data.close.iloc[index]
        
        # 根据波动率动态调整价差
        vol = self.volatility.iloc[index] if index > 0 else 0.001
        dynamic_spread = max(
            params['min_spread'],
            min(params['max_spread'], vol * 2)
        )
        
        # 计算挂单价格
        bid_price = mid_price * (1 - dynamic_spread)
        ask_price = mid_price * (1 + dynamic_spread)
        
        # 库存管理
        if self.inventory > params['inventory_limit']:
            # 库存过多，降低买入
            return self.sell(
                symbol=self._data.name if self._data else "",
                quantity=500,
                reason="库存清理"
            )
        elif self.inventory < -params['inventory_limit']:
            # 库存过少，降低卖出
            return self.buy(
                symbol=self._data.name if self._data else "",
                quantity=500,
                reason="库存回补"
            )
        
        # 简单策略：持有小仓位
        return None
    
    def place_orders(self, bid_price: float, ask_price: float, size: int):
        """挂单"""
        # 实际实现需要对接交易所API
        self.bid_orders.append({'price': bid_price, 'size': size})
        self.ask_orders.append({'price': ask_price, 'size': size})
    
    def cancel_orders(self):
        """撤单"""
        self.bid_orders = []
        self.ask_orders = []
