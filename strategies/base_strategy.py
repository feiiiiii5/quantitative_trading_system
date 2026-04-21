#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略基类模块 - 从核心引擎导入

此文件提供向后兼容性，实际实现位于 core.engine 中
"""

from core.engine import BaseStrategy, Order, DataFeed

__all__ = ['BaseStrategy', 'Order', 'DataFeed']
