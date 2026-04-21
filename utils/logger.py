#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志工具模块
提供统一的日志记录功能，支持控制台和文件输出
"""

import sys
from pathlib import Path
from loguru import logger
from config.settings import LOGGING


def setup_logger():
    """
    初始化日志系统
    配置日志格式、级别、输出位置
    """
    # 移除默认的logger配置
    logger.remove()
    
    # 添加控制台输出
    logger.add(
        sys.stdout,
        level=LOGGING["level"],
        format=LOGGING["format"],
        colorize=True
    )
    
    # 添加文件输出
    logger.add(
        LOGGING["file"],
        level=LOGGING["level"],
        format=LOGGING["format"],
        rotation="100 MB",      # 文件大小超过100MB时自动轮转
        retention="30 days",    # 保留30天日志
        compression="zip"       # 压缩旧日志
    )
    
    return logger


def get_logger(name=None):
    """
    获取指定名称的logger
    
    Args:
        name: logger名称，通常使用__name__
        
    Returns:
        logger对象
    """
    if name:
        return logger.bind(name=name)
    return logger
