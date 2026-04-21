#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基准指数数据模块

获取各市场基准指数数据：
- A股：沪深300（000300）、中证500（000905）
- 港股：恒生指数（HSI）
- 美股：标普500（SPY）、纳斯达克（QQQ）
"""

import pandas as pd
from typing import Optional


class IndexData:
    """基准指数数据获取器"""

    # 指数代码映射
    INDEX_MAP = {
        "CN": {
            "沪深300": "000300",
            "中证500": "000905",
            "上证50": "000016",
        },
        "HK": {
            "恒生指数": "HSI",
            "恒生科技": "HSTECH",
        },
        "US": {
            "标普500": "SPY",
            "纳斯达克100": "QQQ",
            "道琼斯": "DIA",
        },
    }

    @classmethod
    def get_index_data(cls, index_name: str, start_date: str, end_date: str,
                       source: str = 'akshare') -> Optional[pd.DataFrame]:
        """
        获取指数数据

        Args:
            index_name: 指数名称或代码
            start_date: 开始日期
            end_date: 结束日期
            source: 数据源

        Returns:
            DataFrame
        """
        # 查找对应代码
        code = None
        for market, indices in cls.INDEX_MAP.items():
            if index_name in indices:
                code = indices[index_name]
                break

        if code is None:
            code = index_name  # 直接传入代码

        try:
            if source == 'akshare':
                import akshare as ak
                df = ak.index_zh_a_hist(symbol=code, period="daily",
                                        start_date=start_date.replace("-", ""),
                                        end_date=end_date.replace("-", ""))
                if df is not None and not df.empty:
                    df['日期'] = pd.to_datetime(df['日期'])
                    df.set_index('日期', inplace=True)
                    return df
            elif source == 'yfinance':
                import yfinance as yf
                ticker = yf.Ticker(code)
                df = ticker.history(start=start_date, end=end_date)
                if df is not None and not df.empty:
                    df.columns = [c.lower().replace(' ', '_') for c in df.columns]
                    return df
        except Exception as e:
            print(f"获取指数数据失败: {e}")

        return None

    @classmethod
    def get_benchmark_returns(cls, market: str, start_date: str, end_date: str) -> Optional[pd.Series]:
        """
        获取市场基准收益率

        Args:
            market: CN/HK/US
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            收益率序列
        """
        default_index = {
            "CN": "沪深300",
            "HK": "恒生指数",
            "US": "标普500",
        }

        index_name = default_index.get(market, "沪深300")
        df = cls.get_index_data(index_name, start_date, end_date)

        if df is not None and 'close' in df.columns:
            return df['close'].pct_change().dropna()

        return None
