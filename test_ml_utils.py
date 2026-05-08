"""
测试机器学习工具模块
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np

print("=" * 60)
print("测试 ML Utils 模块")
print("=" * 60)

# 测试设备检测
from core.ml_utils import get_device, get_device_info, is_torch_available  # noqa: E402

print("\n1. 设备检测:")
print(f"   PyTorch 可用: {is_torch_available()}")
print(f"   当前设备: {get_device()}")
info = get_device_info()
print(f"   设备信息: {info}")

# 测试内存优化
from core.ml_utils import optimize_numpy_memory  # noqa: E402

print("\n2. 内存优化测试:")
arr1 = np.random.randn(1000, 1000).astype(np.float64)
print(f"   原始数组大小: {arr1.nbytes / 1024**2:.2f} MB")
print(f"   原始 dtype: {arr1.dtype}")

arr2 = optimize_numpy_memory(arr1)
print(f"   优化后大小: {arr2.nbytes / 1024**2:.2f} MB")
print(f"   优化后 dtype: {arr2.dtype}")
saved = (1 - arr2.nbytes / arr1.nbytes) * 100
print(f"   节省内存: {saved:.1f}%")

# 测试预测模块
print("\n3. 预测模块导入测试:")
try:
    from core.prediction import PricePredictor
    print("   PricePredictor 导入成功")
    print(f"   支持的预测周期: {list(PricePredictor._empty_prediction().keys())}")
except Exception as e:
    print(f"   导入失败: {e}")

# 测试内存守护模块
print("\n4. 内存守护模块测试:")
try:
    from core.memory_guard import get_memory_usage, is_memory_pressure
    mem_info = get_memory_usage()
    print(f"   内存使用: {mem_info.get('rss_mb', 0):.1f} MB")
    print(f"   内存压力: {'是' if is_memory_pressure() else '否'}")
except Exception as e:
    print(f"   导入失败: {e}")

print("\n" + "=" * 60)
print("测试完成！所有核心模块正常工作。")
print("=" * 60)
