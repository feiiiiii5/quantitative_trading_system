#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高性能异步数据管理模块

特性：
- 异步并发获取多只股票数据
- 多级缓存策略（内存+磁盘）
- 向量化数据处理
- 增量更新机制
"""

import asyncio
import aiohttp
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
import warnings

from utils.logger import get_logger

logger = get_logger(__name__)


class DataCache:
    """多级缓存系统"""
    
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 内存缓存
        self._memory_cache = {}
        self._cache_ttl = {}  # 缓存过期时间
        
        # 磁盘缓存索引
        self._disk_index_file = self.cache_dir / "cache_index.json"
        self._disk_index = self._load_disk_index()
    
    def _load_disk_index(self) -> Dict:
        """加载磁盘缓存索引"""
        if self._disk_index_file.exists():
            try:
                with open(self._disk_index_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_disk_index(self):
        """保存磁盘缓存索引"""
        with open(self._disk_index_file, 'w') as f:
            json.dump(self._disk_index, f)
    
    def _get_cache_key(self, symbol: str, start_date: str, end_date: str, **kwargs) -> str:
        """生成缓存键"""
        key_str = f"{symbol}_{start_date}_{end_date}_{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, symbol: str, start_date: str, end_date: str, **kwargs) -> Optional[pd.DataFrame]:
        """获取缓存数据"""
        cache_key = self._get_cache_key(symbol, start_date, end_date, **kwargs)
        
        # 检查内存缓存
        if cache_key in self._memory_cache:
            if datetime.now() < self._cache_ttl.get(cache_key, datetime.min):
                logger.debug(f"内存缓存命中: {symbol}")
                return self._memory_cache[cache_key].copy()
        
        # 检查磁盘缓存
        cache_file = self.cache_dir / f"{cache_key}.parquet"
        if cache_file.exists():
            try:
                data = pd.read_parquet(cache_file)
                # 存入内存缓存
                self._memory_cache[cache_key] = data.copy()
                self._cache_ttl[cache_key] = datetime.now() + timedelta(hours=1)
                logger.debug(f"磁盘缓存命中: {symbol}")
                return data
            except Exception as e:
                logger.warning(f"读取磁盘缓存失败: {e}")
        
        return None
    
    def set(self, data: pd.DataFrame, symbol: str, start_date: str, end_date: str, **kwargs):
        """设置缓存"""
        cache_key = self._get_cache_key(symbol, start_date, end_date, **kwargs)
        
        # 存入内存缓存
        self._memory_cache[cache_key] = data.copy()
        self._cache_ttl[cache_key] = datetime.now() + timedelta(hours=1)
        
        # 存入磁盘缓存
        cache_file = self.cache_dir / f"{cache_key}.parquet"
        try:
            data.to_parquet(cache_file, compression='zstd')
            self._disk_index[cache_key] = {
                'symbol': symbol,
                'start_date': start_date,
                'end_date': end_date,
                'created_at': datetime.now().isoformat(),
                'rows': len(data)
            }
            self._save_disk_index()
        except Exception as e:
            logger.warning(f"写入磁盘缓存失败: {e}")
    
    def clear_memory_cache(self):
        """清理内存缓存"""
        self._memory_cache.clear()
        self._cache_ttl.clear()
        logger.info("内存缓存已清理")
    
    def clear_disk_cache(self):
        """清理磁盘缓存"""
        for cache_file in self.cache_dir.glob("*.parquet"):
            cache_file.unlink()
        self._disk_index.clear()
        self._save_disk_index()
        logger.info("磁盘缓存已清理")

    def cache_stats(self) -> dict:
        """
        缓存统计信息

        Returns:
            dict: 命中率、总大小、条目数
        """
        total_hits = sum(1 for k in self._memory_cache if k in self._cache_ttl)
        total_size = sum(
            df.memory_usage(deep=True).sum()
            for df in self._memory_cache.values()
        ) if self._memory_cache else 0

        disk_size = sum(
            f.stat().st_size
            for f in self.cache_dir.glob("*.parquet")
        ) if self.cache_dir.exists() else 0

        return {
            "memory_entries": len(self._memory_cache),
            "disk_entries": len(self._disk_index),
            "memory_size_mb": round(total_size / (1024 * 1024), 2),
            "disk_size_mb": round(disk_size / (1024 * 1024), 2),
            "total_entries": len(self._memory_cache) + len(self._disk_index),
        }


class AsyncDataManager:
    """
    高性能异步数据管理器
    
    支持：
    - 异步并发获取多只股票数据
    - 自动缓存管理
    - 数据清洗和标准化
    - 增量更新
    """
    
    def __init__(self, cache_dir: str = "data/cache", max_workers: int = 10):
        self.cache = DataCache(cache_dir)
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 数据源配置
        self.data_sources = {
            'akshare': self._fetch_from_akshare,
            'baostock': self._fetch_from_baostock,
            'yfinance': self._fetch_from_yfinance,
            'akshare_hk': self._fetch_hk_from_akshare,
            'akshare_us': self._fetch_us_from_akshare,
        }
        
        logger.info(f"异步数据管理器初始化完成，最大工作线程: {max_workers}")
    
    async def get_stock_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        source: str = 'akshare',
        use_cache: bool = True,
        market: str = None,
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        异步获取单只股票数据

        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            source: 数据源
            use_cache: 是否使用缓存
            market: 市场代码 CN/HK/US（自动检测）
            **kwargs: 额外参数

        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        # 检查缓存
        if use_cache:
            cached_data = self.cache.get(symbol, start_date, end_date, source=source)
            if cached_data is not None:
                return cached_data
        
        # 自动检测市场并选择数据源
        if market is None:
            from data.market_detector import MarketDetector
            market = MarketDetector.detect(symbol)

        # 根据市场自动选择数据源
        if source == 'akshare' and market == 'HK':
            source = 'akshare_hk'
        elif source == 'akshare' and market == 'US':
            source = 'akshare_us'
        elif source == 'yfinance' and market in ('HK', 'US'):
            source = 'yfinance'

        # 异步获取数据
        try:
            if source in self.data_sources:
                # 在线程池中执行同步IO操作
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(
                    self.executor,
                    self.data_sources[source],
                    symbol,
                    start_date,
                    end_date
                )

                if data is not None and not data.empty:
                    # 标准化列名
                    data = self._normalize_columns(data)

                    # 存入缓存
                    if use_cache:
                        self.cache.set(data, symbol, start_date, end_date, source=source)

                    return data
            else:
                logger.error(f"未知数据源: {source}")

        except Exception as e:
            logger.error(f"获取数据失败 {symbol}: {e}")

        return None
    
    async def get_multiple_stocks(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        source: str = 'akshare',
        use_cache: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        异步并发获取多只股票数据
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            source: 数据源
            use_cache: 是否使用缓存
        
        Returns:
            Dict[symbol, DataFrame]
        """
        # 创建并发任务
        tasks = [
            self.get_stock_data(
                symbol, start_date, end_date,
                source=source, use_cache=use_cache
            )
            for symbol in symbols
        ]
        
        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 整理结果
        data_dict = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                logger.error(f"获取 {symbol} 数据失败: {result}")
            elif result is not None:
                data_dict[symbol] = result
        
        logger.info(f"成功获取 {len(data_dict)}/{len(symbols)} 只股票数据")
        return data_dict
    
    def _fetch_from_akshare(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从akshare获取数据"""
        try:
            import akshare as ak
            
            # 转换日期格式
            start = start_date.replace("-", "")
            end = end_date.replace("-", "")
            
            # 获取日K数据
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start,
                end_date=end,
                adjust="qfq"  # 前复权
            )
            
            if df is not None and not df.empty:
                df['日期'] = pd.to_datetime(df['日期'])
                df.set_index('日期', inplace=True)
                return df
                
        except Exception as e:
            logger.warning(f"akshare获取失败: {e}")
        
        return None
    
    def _fetch_from_baostock(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从baostock获取数据"""
        try:
            import baostock as bs
            
            # 登录
            bs.login()
            
            # 转换股票代码格式为baostock所需的9位格式
            if len(symbol) == 6:
                # 判断是沪市还是深市
                if symbol.startswith('6'):
                    baostock_symbol = f"sh.{symbol}"
                else:
                    baostock_symbol = f"sz.{symbol}"
            else:
                baostock_symbol = symbol
            
            # 查询数据
            rs = bs.query_history_k_data_plus(
                baostock_symbol,
                "date,code,open,high,low,close,volume",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="3"  # 复权
            )
            
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            
            bs.logout()
            
            if data_list:
                df = pd.DataFrame(data_list, columns=rs.fields)
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                
                # 转换数值类型
                numeric_cols = ['open', 'high', 'low', 'close', 'volume']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                return df
                
        except Exception as e:
            logger.warning(f"baostock获取失败: {e}")
        
        return None
    
    def _fetch_from_yfinance(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从yfinance获取美股/港股数据"""
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)

            if df is not None and not df.empty:
                df.columns = [c.lower().replace(' ', '_') for c in df.columns]
                # yfinance列名: open, high, low, close, volume, dividends, stock_splits
                return df

        except Exception as e:
            logger.warning(f"yfinance获取失败: {e}")

        return None

    def _fetch_hk_from_akshare(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从akshare获取港股数据"""
        try:
            import akshare as ak

            start = start_date.replace("-", "")
            end = end_date.replace("-", "")

            df = ak.stock_hk_hist(symbol=symbol, period="daily",
                                   start_date=start, end_date=end)

            if df is not None and not df.empty:
                df['日期'] = pd.to_datetime(df['日期'])
                df.set_index('日期', inplace=True)
                return df

        except Exception as e:
            logger.warning(f"akshare港股获取失败: {e}")

        return None

    def _fetch_us_from_akshare(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从akshare获取美股数据"""
        try:
            import akshare as ak

            start = start_date.replace("-", "")
            end = end_date.replace("-", "")

            df = ak.stock_us_hist(symbol=symbol, period="daily",
                                   start_date=start, end_date=end)

            if df is not None and not df.empty:
                df['日期'] = pd.to_datetime(df['日期'])
                df.set_index('日期', inplace=True)
                return df

        except Exception as e:
            logger.warning(f"akshare美股获取失败: {e}")

        return None

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        # 列名映射
        column_mapping = {
            '日期': 'date',
            '开盘': 'open',
            '最高': 'high',
            '最低': 'low',
            '收盘': 'close',
            '成交量': 'volume',
            '成交额': 'amount',
            '振幅': 'amplitude',
            '涨跌幅': 'pct_change',
            '涨跌额': 'change',
            '换手率': 'turnover',
        }

        # 重命名列
        df = df.rename(columns=column_mapping)

        # 确保必要列存在
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                logger.warning(f"缺少必要列: {col}")

        return df
    
    def get_data_sync(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        source: str = 'akshare',
        use_cache: bool = True,
        market: str = None
    ) -> Optional[pd.DataFrame]:
        """
        同步获取数据（macOS兼容版）

        修复：在已有事件循环的线程中（如Jupyter、macOS），
        使用 ThreadPoolExecutor 避免嵌套事件循环错误
        """
        try:
            asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(
                    asyncio.run,
                    self.get_stock_data(symbol, start_date, end_date, source, use_cache, market)
                ).result()
        except RuntimeError:
            return asyncio.run(
                self.get_stock_data(symbol, start_date, end_date, source, use_cache, market)
            )

    def get_multiple_stocks_sync(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        source: str = 'akshare',
        use_cache: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        同步批量获取多只股票数据（macOS兼容版）

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            source: 数据源
            use_cache: 是否使用缓存

        Returns:
            Dict[symbol, DataFrame]
        """
        try:
            asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(
                    asyncio.run,
                    self.get_multiple_stocks(symbols, start_date, end_date, source, use_cache)
                ).result()
        except RuntimeError:
            return asyncio.run(
                self.get_multiple_stocks(symbols, start_date, end_date, source, use_cache)
            )
    
    def update_data_incremental(
        self,
        symbol: str,
        source: str = 'akshare'
    ) -> Optional[pd.DataFrame]:
        """增量更新数据"""
        # 获取缓存中的最新日期
        # 简化为获取最近30天数据
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        return self.get_data_sync(symbol, start_date, end_date, source)
    
    def get_realtime_quote(self, symbol: str, market: str = None) -> Optional[Dict]:
        """
        获取实时行情

        Args:
            symbol: 股票代码
            market: 市场代码 CN/HK/US

        Returns:
            标准化字典: {price, change, change_pct, volume, high, low, open}
        """
        if market is None:
            from data.market_detector import MarketDetector
            market = MarketDetector.detect(symbol)

        try:
            import akshare as ak

            if market == "CN":
                df = ak.stock_zh_a_spot_em()
                row = df[df['代码'] == symbol]
                if row.empty:
                    return None
                r = row.iloc[0]
                return {
                    'price': float(r.get('最新价', 0)),
                    'change': float(r.get('涨跌额', 0)),
                    'change_pct': float(r.get('涨跌幅', 0)),
                    'volume': float(r.get('成交量', 0)),
                    'high': float(r.get('最高', 0)),
                    'low': float(r.get('最低', 0)),
                    'open': float(r.get('今开', 0)),
                }
            elif market == "HK":
                df = ak.stock_hk_spot_em()
                hk_code_col = '代码' if '代码' in df.columns else 'symbol'
                row = df[df[hk_code_col] == symbol]
                if row.empty:
                    return None
                r = row.iloc[0]
                return {
                    'price': float(r.get('最新价', r.get('last_price', 0))),
                    'change': float(r.get('涨跌额', r.get('change', 0))),
                    'change_pct': float(r.get('涨跌幅', r.get('change_pct', 0))),
                    'volume': float(r.get('成交量', r.get('volume', 0))),
                    'high': float(r.get('最高', r.get('high', 0))),
                    'low': float(r.get('最低', r.get('low', 0))),
                    'open': float(r.get('今开', r.get('open', 0))),
                }
            elif market == "US":
                try:
                    import yfinance as yf
                    ticker = yf.Ticker(symbol)
                    info = ticker.fast_info
                    return {
                        'price': float(info.get('lastPrice', 0)),
                        'change': 0,
                        'change_pct': float(info.get('previousClose', 0)),
                        'volume': float(info.get('regularMarketVolume', 0)),
                        'high': float(info.get('regularMarketDayHigh', 0)),
                        'low': float(info.get('regularMarketDayLow', 0)),
                        'open': float(info.get('regularMarketOpen', 0)),
                    }
                except Exception:
                    return None
        except Exception as e:
            logger.warning(f"获取实时行情失败: {e}")
            return None

    def close(self):
        """关闭资源"""
        self.executor.shutdown(wait=True)
        logger.info("数据管理器已关闭")


# 全局数据管理器实例
data_manager = AsyncDataManager()
