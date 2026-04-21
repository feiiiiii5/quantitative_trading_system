#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据获取与处理模块
支持多种数据源（akshare、tushare、baostock）
提供股票数据的获取、清洗、缓存功能
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import Optional, List, Union

try:
    import akshare as ak
except ImportError:
    ak = None

from utils.logger import get_logger
from config.settings import DATA_SOURCE, DATA_DIR

logger = get_logger(__name__)


class DataManager:
    """
    数据管理器
    
    负责：
    - 从多个数据源获取金融数据
    - 数据清洗和标准化
    - 本地缓存管理
    """
    
    def __init__(self, cache_enabled=True):
        """
        初始化数据管理器
        
        Args:
            cache_enabled: 是否启用本地缓存
        """
        self.cache_enabled = cache_enabled
        self.daily_cache = DATA_SOURCE["akshare"]["daily_data_cache"]
        self.minute_cache = DATA_SOURCE["akshare"]["minute_data_cache"]
        
        # 确保缓存目录存在
        self.daily_cache.mkdir(parents=True, exist_ok=True)
        self.minute_cache.mkdir(parents=True, exist_ok=True)
        
        logger.info("数据管理器初始化完成")
    
    def get_stock_data(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        data_type: str = "daily",
        source: str = "akshare"
    ) -> pd.DataFrame:
        """
        获取股票数据
        
        Args:
            stock_code: 股票代码（如 '000001.XSHE'）
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            data_type: 数据类型 ('daily' 或 'minute')
            source: 数据源 ('akshare' 或 'baostock')
            
        Returns:
            DataFrame，包含OHLCV等标准字段
        """
        # 尝试从缓存加载
        if self.cache_enabled:
            cached_data = self._load_from_cache(stock_code, data_type)
            if cached_data is not None:
                # 筛选日期范围
                cached_data['date'] = pd.to_datetime(cached_data['date'])
                mask = (cached_data['date'] >= start_date) & (cached_data['date'] <= end_date)
                if mask.sum() > 0:
                    logger.info(f"从缓存加载 {stock_code} 数据")
                    return cached_data[mask].reset_index(drop=True)
        
        # 从数据源获取数据
        if source == "akshare":
            data = self._fetch_from_akshare(stock_code, start_date, end_date, data_type)
        elif source == "baostock":
            data = self._fetch_from_baostock(stock_code, start_date, end_date)
        else:
            raise ValueError(f"不支持的数据源: {source}")
        
        # 保存到缓存
        if self.cache_enabled and data is not None:
            self._save_to_cache(data, stock_code, data_type)
        
        return data
    
    def _fetch_from_akshare(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        data_type: str = "daily"
    ) -> Optional[pd.DataFrame]:
        """
        从akshare获取数据
        
        akshare是免费的Python财经数据接口库
        无需注册即可使用大部分功能
        """
        if ak is None:
            logger.error("请先安装akshare: pip install akshare")
            return None
        
        try:
            # 格式化日期（移除横杠）
            start_str = start_date.replace("-", "")
            end_str = end_date.replace("-", "")
            
            # 判断交易所代码
            if stock_code.endswith(".XSHG"):
                symbol = stock_code.replace(".XSHG", "")
                adjust = "qfq"  # 前复权
            elif stock_code.endswith(".XSHE"):
                symbol = stock_code.replace(".XSHE", "")
                adjust = "qfq"
            else:
                symbol = stock_code
                adjust = "qfq"
            
            if data_type == "daily":
                # 获取日线数据
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start_str,
                    end_date=end_str,
                    adjust=adjust
                )
                
                # 标准化列名
                df = self._normalize_columns(df)
                
            elif data_type == "minute":
                # 获取分钟数据
                df = ak.stock_zh_a_minute(
                    symbol=stock_code,
                    period="30",
                    adjust="qfq"
                )
            
            logger.info(f"成功获取 {stock_code} 数据，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.error(f"从akshare获取 {stock_code} 数据失败: {e}")
            return None
    
    def _fetch_from_baostock(
        self,
        stock_code: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """从baostock获取数据（另一免费数据源）"""
        try:
            import baostock as bs
            
            # 登录系统
            lg = bs.login()
            if lg.error_code != '0':
                logger.error(f"baostock登录失败: {lg.error_msg}")
                return None
            
            # 转换股票代码格式
            if stock_code.endswith(".XSHG"):
                bs_code = "sh." + stock_code.replace(".XSHG", "")
            elif stock_code.endswith(".XSHE"):
                bs_code = "sz." + stock_code.replace(".XSHE", "")
            else:
                bs_code = stock_code
            
            # 获取数据
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,volume,amount",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="2"  # 前复权
            )
            
            # 转换为DataFrame
            data_list = []
            while rs.error_code == '0' and rs.next():
                data_list.append(rs.get_row_data())
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            
            # 登出系统
            bs.logout()
            
            # 数值类型转换
            for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
            
        except ImportError:
            logger.error("请先安装baostock: pip install baostock")
            return None
        except Exception as e:
            logger.error(f"从baostock获取数据失败: {e}")
            return None
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化数据列名
        
        统一不同数据源的列名格式
        """
        # akshare的列名映射
        column_mapping = {
            '日期': 'date',
            '股票代码': 'code',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount',
            '振幅': 'amplitude',
            '涨跌幅': 'pct_change',
            '涨跌额': 'change',
            '换手率': 'turnover'
        }
        
        df = df.rename(columns=column_mapping)
        
        # 确保date列是datetime类型
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        
        return df
    
    def _load_from_cache(self, stock_code: str, data_type: str) -> Optional[pd.DataFrame]:
        """从本地缓存加载数据"""
        try:
            cache_dir = self.daily_cache if data_type == "daily" else self.minute_cache
            cache_file = cache_dir / f"{stock_code}.csv"
            
            if cache_file.exists():
                return pd.read_csv(cache_file, parse_dates=['date'])
            
            return None
        except Exception as e:
            logger.warning(f"加载缓存失败: {e}")
            return None
    
    def _save_to_cache(self, df: pd.DataFrame, stock_code: str, data_type: str):
        """保存数据到本地缓存"""
        try:
            cache_dir = self.daily_cache if data_type == "daily" else self.minute_cache
            cache_file = cache_dir / f"{stock_code}.csv"
            
            df.to_csv(cache_file, index=False)
            logger.debug(f"数据已缓存至: {cache_file}")
            
        except Exception as e:
            logger.warning(f"保存缓存失败: {e}")
    
    def get_realtime_quote(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        获取实时行情
        
        Args:
            stock_codes: 股票代码列表
            
        Returns:
            实时行情数据
        """
        if ak is None:
            logger.error("请先安装akshare")
            return pd.DataFrame()
        
        try:
            # 获取实时行情
            df = ak.stock_zh_a_spot_em()
            
            # 筛选指定股票
            df = df[df['代码'].isin([c.split('.')[0] for c in stock_codes])]
            
            return df
            
        except Exception as e:
            logger.error(f"获取实时行情失败: {e}")
            return pd.DataFrame()
    
    def calculate_returns(self, df: pd.DataFrame, column: str = 'close') -> pd.Series:
        """
        计算收益率序列
        
        Args:
            df: 包含价格数据的DataFrame
            column: 价格列名
            
        Returns:
            收益率Series
        """
        prices = df[column]
        returns = prices.pct_change()
        return returns
    
    def calculate_volatility(
        self,
        df: pd.DataFrame,
        window: int = 20,
        column: str = 'close'
    ) -> pd.Series:
        """
        计算历史波动率
        
        Args:
            df: 包含价格数据的DataFrame
            window: 计算窗口
            column: 价格列名
            
        Returns:
            波动率Series
        """
        returns = self.calculate_returns(df, column)
        volatility = returns.rolling(window=window).std() * np.sqrt(252)
        return volatility
    
    def resample_data(
        self,
        df: pd.DataFrame,
        freq: str,
        agg_dict: dict = None
    ) -> pd.DataFrame:
        """
        重采样数据（如从日线合成周线、月线）
        
        Args:
            df: 原始数据
            freq: 目标频率 ('W', 'M', 'Q', 'Y')
            agg_dict: 聚合规则
            
        Returns:
            重采样后的数据
        """
        if agg_dict is None:
            agg_dict = {
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }
        
        df = df.set_index('date')
        resampled = df.resample(freq).agg(agg_dict)
        resampled = resampled.dropna()
        
        return resampled.reset_index()
    
    def get_index_components(self, index_code: str = "000300.XSHG") -> List[str]:
        """
        获取指数成分股
        
        Args:
            index_code: 指数代码（如沪深300）
            
        Returns:
            成分股代码列表
        """
        if ak is None:
            logger.error("请先安装akshare")
            return []
        
        try:
            # 获取沪深300成分股
            df = ak.index_zh_a_hist(period="季度", start_date="20230101")
            
            # 获取最新的成分股列表
            df = ak.stock_list_sz50()  # 上证50
            
            return df['代码'].tolist()
            
        except Exception as e:
            logger.error(f"获取指数成分股失败: {e}")
            return []
