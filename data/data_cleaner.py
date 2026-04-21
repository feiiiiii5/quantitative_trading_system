#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据清洗模块

- 异常值处理
- 缺失值填充
- 除权除息复权
- 数据有效性验证
- 时区标准化
"""

import numpy as np
import pandas as pd
from typing import Tuple, List
from datetime import timezone, timedelta


class DataCleaner:
    """数据清洗器"""

    @staticmethod
    def remove_outliers(df: pd.DataFrame, method: str = 'zscore',
                        threshold: float = 3) -> pd.DataFrame:
        """
        异常值处理

        Args:
            df: OHLCV数据
            method: 'zscore' 或 'iqr'
            threshold: zscore阈值

        Returns:
            清洗后的DataFrame
        """
        df = df.copy()
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']

        for col in numeric_cols:
            if col not in df.columns:
                continue

            if method == 'zscore':
                z = np.abs((df[col] - df[col].mean()) / (df[col].std() + 1e-8))
                df.loc[z > threshold, col] = np.nan
            elif method == 'iqr':
                q1 = df[col].quantile(0.25)
                q3 = df[col].quantile(0.75)
                iqr = q3 - q1
                lower = q1 - threshold * iqr
                upper = q3 + threshold * iqr
                df.loc[(df[col] < lower) | (df[col] > upper), col] = np.nan

        return df

    @staticmethod
    def fill_missing(df: pd.DataFrame, method: str = 'ffill') -> pd.DataFrame:
        """
        缺失值填充

        Args:
            df: 数据
            method: 'ffill', 'bfill', 'linear'

        Returns:
            填充后的DataFrame
        """
        df = df.copy()

        if method == 'ffill':
            df = df.ffill()
        elif method == 'bfill':
            df = df.bfill()
        elif method == 'linear':
            df = df.interpolate(method='linear')

        return df

    @staticmethod
    def adjust_splits(df: pd.DataFrame, factor_series: pd.Series) -> pd.DataFrame:
        """
        除权除息复权

        Args:
            df: OHLCV数据
            factor_series: 复权因子序列（与df同索引）

        Returns:
            复权后的DataFrame
        """
        df = df.copy()
        price_cols = ['open', 'high', 'low', 'close']

        for col in price_cols:
            if col in df.columns:
                df[col] = df[col] * factor_series

        if 'volume' in df.columns:
            df['volume'] = (df['volume'] / factor_series).astype(int)

        return df

    @staticmethod
    def validate_ohlcv(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        数据有效性验证

        规则：
        - high >= low
        - open/close在[low, high]范围内
        - volume >= 0
        - 无NaN

        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []

        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                errors.append(f"缺少必要列: {col}")

        if errors:
            return False, errors

        # high >= low
        invalid_hl = df[df['high'] < df['low']]
        if len(invalid_hl) > 0:
            errors.append(f"high < low: {len(invalid_hl)} 行")

        # open/close在[low, high]范围内
        invalid_open = df[(df['open'] < df['low']) | (df['open'] > df['high'])]
        if len(invalid_open) > 0:
            errors.append(f"open超出[low,high]范围: {len(invalid_open)} 行")

        invalid_close = df[(df['close'] < df['low']) | (df['close'] > df['high'])]
        if len(invalid_close) > 0:
            errors.append(f"close超出[low,high]范围: {len(invalid_close)} 行")

        # volume >= 0
        invalid_vol = df[df['volume'] < 0]
        if len(invalid_vol) > 0:
            errors.append(f"volume < 0: {len(invalid_vol)} 行")

        # 检查NaN
        nan_count = df[required_cols].isna().sum().sum()
        if nan_count > 0:
            errors.append(f"存在 {nan_count} 个NaN值")

        return len(errors) == 0, errors

    @staticmethod
    def standardize_timezone(df: pd.DataFrame, market: str = "CN") -> pd.DataFrame:
        """
        统一时区

        Args:
            df: 数据（索引为DatetimeIndex）
            market: CN/HK/US

        Returns:
            带时区的DataFrame
        """
        df = df.copy()

        tz_map = {
            "CN": timezone(timedelta(hours=8)),
            "HK": timezone(timedelta(hours=8)),
            "US": timezone(timedelta(hours=-5)),  # EST
        }

        tz = tz_map.get(market, timezone.utc)

        if isinstance(df.index, pd.DatetimeIndex):
            df.index = df.index.tz_localize(None).tz_localize(tz)

        return df
