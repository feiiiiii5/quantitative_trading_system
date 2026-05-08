"""
机器学习工具模块 - 提供PyTorch和MPS加速支持
包含设备检测、张量管理和内存优化功能
"""
import logging
from functools import lru_cache
from typing import TYPE_CHECKING, Optional, Union

import numpy as np

if TYPE_CHECKING:
    import torch

logger = logging.getLogger(__name__)

__all__ = [
    'get_device',
    'is_torch_available',
    'safe_to_tensor',
    'safe_to_numpy',
    'clear_gpu_memory',
    'MemoryEfficientTensor',
    'get_device_info',
    'optimize_numpy_memory',
    'batch_process_with_memory_control',
    'DeviceType',
]

# 全局变量跟踪当前设备
_current_device = None
_device_initialized = False


DeviceType = str
_DEVICE_TYPES = frozenset({'cpu', 'cuda', 'mps'})


def get_device(force_cpu: bool = False) -> DeviceType:
    """
    获取最佳计算设备

    Args:
        force_cpu: 强制使用CPU

    Returns:
        设备标识符，如 'mps', 'cuda', 'cpu'
    """
    global _current_device, _device_initialized

    if _device_initialized and not force_cpu and _current_device in _DEVICE_TYPES:
        return _current_device

    try:
        import torch

        if force_cpu:
            device: DeviceType = 'cpu'
        elif torch.backends.mps.is_available():
            device = 'mps'
            logger.info("使用 Apple Silicon MPS 加速")
        elif torch.cuda.is_available():
            device = 'cuda'
            logger.info("使用 CUDA 加速: %s", torch)
        else:
            device = 'cpu'
            logger.info("使用 CPU 计算")

        _current_device = device
        _device_initialized = True
        return device

    except ImportError:
        logger.debug("PyTorch 未安装，仅支持 CPU 模式")
        _current_device = 'cpu'
        _device_initialized = True
        return 'cpu'


def is_torch_available() -> bool:
    """检查PyTorch是否可用"""
    try:
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


def safe_to_tensor(data: np.ndarray | list,
                   dtype: Optional = None,
                   device: str | None = None) -> Union[np.ndarray, 'torch.Tensor']:
    """
    安全转换数据为张量（如果PyTorch可用）

    Args:
        data: 输入数据
        dtype: 数据类型
        device: 目标设备

    Returns:
        PyTorch张量或numpy数组（如果PyTorch不可用）
    """
    if not is_torch_available():
        return np.asarray(data)

    import torch

    target_device = device or get_device()
    try:
        tensor = torch.tensor(data, dtype=dtype, device=target_device)
        return tensor
    except Exception as e:
        logger.warning("张量转换失败，回退到numpy: %s", e)
        return np.asarray(data)


def safe_to_numpy(data: Union[np.ndarray, 'torch.Tensor']) -> np.ndarray:
    """
    安全转换数据为numpy数组

    Args:
        data: 输入数据

    Returns:
        numpy数组
    """
    if isinstance(data, np.ndarray):
        return data

    try:
        import torch
        if isinstance(data, torch.Tensor):
            if data.device.type in ['mps', 'cuda']:
                data = data.cpu()
            return data.numpy()
    except ImportError:
        pass

    return np.asarray(data)


def clear_gpu_memory() -> None:
    """清理GPU/MPS内存"""
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            logger.info("CUDA 内存已清理")
        if torch.backends.mps.is_available():
            # MPS 自动管理，但可以触发GC
            import gc
            gc.collect()
            logger.info("MPS 内存触发GC")
    except ImportError:
        pass


class MemoryEfficientTensor:
    """
    内存高效张量包装器，支持自动卸载到CPU
    """

    def __init__(self, data: Union[np.ndarray, 'torch.Tensor'],
                 name: str = "",
                 keep_on_gpu: bool = False):
        """
        Args:
            data: 输入数据
            name: 张量名称（用于日志）
            keep_on_gpu: 是否保持在GPU上
        """
        self._name = name
        self._keep_on_gpu = keep_on_gpu
        self._data_cpu = None
        self._data_gpu = None
        self._device = get_device()

        if is_torch_available():
            import torch
            if isinstance(data, torch.Tensor):
                if keep_on_gpu:
                    self._data_gpu = data.to(self._device)
                else:
                    self._data_cpu = data.cpu().numpy()
            else:
                self._data_cpu = np.asarray(data)
        else:
            self._data_cpu = np.asarray(data)

    def get(self, device: str | None = None) -> Union[np.ndarray, 'torch.Tensor']:
        """
        获取数据，自动移动到目标设备

        Args:
            device: 目标设备

        Returns:
            数据
        """
        target_device = device or self._device

        if self._data_gpu is not None:
            if target_device == 'cpu' and self._data_cpu is None:
                self._data_cpu = safe_to_numpy(self._data_gpu)
            return self._data_gpu

        if target_device != 'cpu' and self._data_cpu is not None:
            self._data_gpu = safe_to_tensor(self._data_cpu, device=target_device)
            if not self._keep_on_gpu:
                # 不保持在GPU上，获取后清理
                result = self._data_gpu
                self._data_gpu = None
                return result

        return self._data_cpu if self._data_cpu is not None else self._data_gpu

    @property
    def numpy(self) -> np.ndarray:
        """获取numpy数组"""
        return safe_to_numpy(self.get(device='cpu'))

    @property
    def tensor(self) -> Optional['torch.Tensor']:
        """获取张量（如果可用）"""
        if is_torch_available():
            return self.get()
        return None

    def free_gpu(self) -> None:
        """释放GPU内存"""
        if self._data_gpu is not None:
            if self._data_cpu is None:
                self._data_cpu = safe_to_numpy(self._data_gpu)
            del self._data_gpu
            self._data_gpu = None
            clear_gpu_memory()
            logger.debug("已释放张量 '%s' 的GPU内存", self)


@lru_cache(maxsize=1)
def get_device_info() -> dict:
    """
    获取设备信息

    Returns:
        设备信息字典
    """
    info = {
        'torch_available': is_torch_available(),
        'device': get_device(),
    }

    if is_torch_available():
        import torch
        info['torch_version'] = torch.__version__
        info['mps_available'] = torch.backends.mps.is_available()
        info['cuda_available'] = torch.cuda.is_available()

        if torch.cuda.is_available():
            info['cuda_device_count'] = torch.cuda.device_count()
            info['cuda_device_name'] = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            info['cuda_memory_total_gb'] = round(props.total_memory / 1024**3, 1)

    return info


def optimize_numpy_memory(arr: np.ndarray, dtype: Optional = None) -> np.ndarray:
    """
    优化numpy数组内存使用

    Args:
        arr: 输入数组
        dtype: 目标数据类型（默认自动选择）

    Returns:
        优化后的数组
    """
    if dtype is not None:
        return arr.astype(dtype, copy=False)

    # 尝试自动选择更紧凑的数据类型
    if np.issubdtype(arr.dtype, np.floating):
        # 检查是否可以降精度
        max_val = np.max(np.abs(arr))
        if max_val < 1e6 and max_val > 1e-6:
            return arr.astype(np.float32, copy=False)

    elif np.issubdtype(arr.dtype, np.integer):
        min_val, max_val = np.min(arr), np.max(arr)
        if np.iinfo(np.int16).min <= min_val and max_val <= np.iinfo(np.int16).max:
            return arr.astype(np.int16, copy=False)
        elif np.iinfo(np.int32).min <= min_val and max_val <= np.iinfo(np.int32).max:
            return arr.astype(np.int32, copy=False)

    return arr


def batch_process_with_memory_control(data_list: list,
                                      processor: callable,
                                      batch_size: int = 100,
                                      max_memory_mb: int = 512,
                                      **kwargs) -> list:
    """
    带内存控制的批处理函数

    Args:
        data_list: 数据列表
        processor: 处理函数
        batch_size: 批大小
        max_memory_mb: 最大内存使用（MB）
        **kwargs: 传递给processor的参数

    Returns:
        处理结果列表
    """
    from core.memory_guard import check_and_reclaim_if_needed, is_memory_critical

    results = []
    total = len(data_list)

    for i in range(0, total, batch_size):
        # 检查内存
        if is_memory_critical():
            logger.warning("内存临界，暂停处理并回收")
            check_and_reclaim_if_needed()

        batch = data_list[i:i + batch_size]

        # 处理批次
        try:
            batch_result = processor(batch, **kwargs)
            if isinstance(batch_result, list):
                results.extend(batch_result)
            else:
                results.append(batch_result)
        except Exception as e:
            logger.error("批次处理失败 [%s-%s): %s", i, i, e)
            raise

        # 定期内存检查
        if (i // batch_size) % 5 == 0:
            check_and_reclaim_if_needed()

    return results
