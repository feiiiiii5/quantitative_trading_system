#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略管理器
负责策略的加载、注册、管理和运行
"""

import os
import sys
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Type, Optional

from strategies.base_strategy import BaseStrategy
from utils.logger import get_logger

logger = get_logger(__name__)


class StrategyManager:
    """
    策略管理器
    
    功能：
    - 自动发现和加载策略
    - 策略注册和注销
    - 策略参数管理
    - 策略性能跟踪
    """
    
    def __init__(self, strategy_dir: str = None):
        """
        初始化策略管理器
        
        Args:
            strategy_dir: 策略文件目录，默认使用内置策略目录
        """
        self.strategies: Dict[str, Type[BaseStrategy]] = {}
        self.active_strategy: Optional[BaseStrategy] = None
        
        # 策略目录
        if strategy_dir is None:
            self.strategy_dir = Path(__file__).parent
        else:
            self.strategy_dir = Path(strategy_dir)
        
        # 自动加载内置策略
        self._load_builtin_strategies()
        
        logger.info(f"策略管理器初始化完成，已加载 {len(self.strategies)} 个策略")
    
    def _load_builtin_strategies(self):
        """加载内置策略"""
        try:
            from strategies.example_ma_cross import MACrossStrategy, RSIStrategy, BollingerBandsStrategy
            
            self.register_strategy("ma_cross", MACrossStrategy)
            self.register_strategy("rsi", RSIStrategy)
            self.register_strategy("bollinger", BollingerBandsStrategy)
            
            logger.info("内置策略加载成功")
        except Exception as e:
            logger.error(f"加载内置策略失败: {e}")
    
    def register_strategy(self, name: str, strategy_class: Type[BaseStrategy]):
        """
        注册策略
        
        Args:
            name: 策略名称
            strategy_class: 策略类（必须继承BaseStrategy）
        """
        if not issubclass(strategy_class, BaseStrategy):
            raise ValueError(f"策略类必须继承BaseStrategy: {strategy_class}")
        
        self.strategies[name] = strategy_class
        logger.info(f"策略已注册: {name}")
    
    def unregister_strategy(self, name: str):
        """
        注销策略
        
        Args:
            name: 策略名称
        """
        if name in self.strategies:
            del self.strategies[name]
            logger.info(f"策略已注销: {name}")
    
    def load_strategy(self, name: str, parameters: Dict = None) -> BaseStrategy:
        """
        加载策略实例
        
        Args:
            name: 策略名称
            parameters: 策略参数
            
        Returns:
            策略实例
        """
        if name not in self.strategies:
            raise ValueError(f"策略不存在: {name}，可用策略: {list(self.strategies.keys())}")
        
        strategy_class = self.strategies[name]
        strategy = strategy_class(parameters=parameters)
        
        self.active_strategy = strategy
        logger.info(f"策略已加载: {name}")
        
        return strategy
    
    def list_strategies(self) -> List[str]:
        """
        获取所有可用策略列表
        
        Returns:
            策略名称列表
        """
        return list(self.strategies.keys())
    
    def get_strategy_info(self, name: str) -> Dict:
        """
        获取策略信息
        
        Args:
            name: 策略名称
            
        Returns:
            策略信息字典
        """
        if name not in self.strategies:
            return {}
        
        strategy_class = self.strategies[name]
        
        # 获取类的文档字符串
        doc = strategy_class.__doc__ or "暂无描述"
        
        # 获取默认参数
        try:
            instance = strategy_class()
            default_params = instance.get_parameters()
        except:
            default_params = {}
        
        return {
            'name': name,
            'class': strategy_class.__name__,
            'description': doc.strip(),
            'default_parameters': default_params
        }
    
    def discover_strategies(self, directory: str = None):
        """
        从目录自动发现策略
        
        扫描指定目录下的Python文件，自动注册继承BaseStrategy的类
        
        Args:
            directory: 要扫描的目录
        """
        if directory is None:
            directory = self.strategy_dir
        
        directory = Path(directory)
        
        if not directory.exists():
            logger.warning(f"策略目录不存在: {directory}")
            return
        
        # 添加目录到Python路径
        if str(directory) not in sys.path:
            sys.path.insert(0, str(directory))
        
        # 扫描Python文件
        for file_path in directory.glob("*.py"):
            if file_path.name.startswith("_"):
                continue
            
            try:
                # 动态导入模块
                module_name = file_path.stem
                module = importlib.import_module(module_name)
                
                # 查找策略类
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseStrategy) and 
                        obj is not BaseStrategy):
                        
                        # 使用类名作为策略名（小写）
                        strategy_name = name.lower()
                        self.register_strategy(strategy_name, obj)
                        
            except Exception as e:
                logger.warning(f"加载策略文件失败 {file_path}: {e}")
    
    def create_strategy_template(self, name: str, output_dir: str = None):
        """
        创建策略模板文件
        
        为新手提供策略开发模板
        
        Args:
            name: 策略名称
            output_dir: 输出目录
        """
        if output_dir is None:
            output_dir = self.strategy_dir
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = output_dir / f"{name.lower()}_strategy.py"
        
        template = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
{name}策略

策略描述：
- 在此处添加策略的详细说明
- 策略逻辑、适用场景、优缺点

作者：
创建日期：
"""

import pandas as pd
from typing import Dict

from strategies.base_strategy import BaseStrategy
from utils.logger import get_logger

logger = get_logger(__name__)


class {name}Strategy(BaseStrategy):
    """
    {name}策略
    
    参数:
    - param1: 参数1说明
    - param2: 参数2说明
    """
    
    def __init__(self, parameters: Dict = None):
        """
        初始化策略
        
        Args:
            parameters: 策略参数
        """
        default_params = {{
            'param1': 10,
            'param2': 20
        }}
        
        if parameters:
            default_params.update(parameters)
        
        super().__init__(name="{name}", parameters=default_params)
    
    def init(self, data: pd.DataFrame):
        """
        初始化指标计算
        
        Args:
            data: 历史数据
        """
        # TODO: 在此处计算技术指标
        # 示例：计算移动平均线
        # self.ma = data['close'].rolling(window=self.parameters['param1']).mean()
        
        logger.info("策略指标计算完成")
    
    def next(self, index: int, current_data: pd.Series) -> Dict:
        """
        每个周期的交易逻辑
        
        Args:
            index: 当前索引
            current_data: 当前数据
            
        Returns:
            交易信号
        """
        # TODO: 实现交易逻辑
        
        # 示例：简单的买入逻辑
        # if self.position <= 0:
        #     return self.buy(weight=1.0, reason="买入信号")
        
        # 示例：简单的卖出逻辑
        # if self.position > 0:
        #     return self.sell(weight=1.0, reason="卖出信号")
        
        return self.hold(reason="无交易信号")
'''
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(template)
        
        logger.info(f"策略模板已创建: {file_path}")
        return file_path
