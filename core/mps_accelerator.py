"""MPS Acceleration Module for Apple Silicon Mac.

Provides GPU acceleration using Metal Performance Shaders (MPS) on M1/M2/M3 chips.
Automatically detects available devices and falls back to CPU when MPS is unavailable.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)

TORCH_AVAILABLE = False
torch = None

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    logger.debug("PyTorch not installed, MPS acceleration disabled")

DeviceType = str

def get_device() -> tuple[DeviceType, str]:
    """Detect and return the best available compute device.

    Returns:
        Tuple of (device_type, device_name)
        device_type: 'mps', 'cuda', or 'cpu'
        device_name: Human-readable device name
    """
    if not TORCH_AVAILABLE:
        return 'cpu', 'CPU (PyTorch not installed)'

    if torch.backends.mps.is_available():
        return 'mps', 'Apple MPS (Metal GPU)'
    elif torch.cuda.is_available():
        return 'cuda', f'CUDA:{torch.cuda.current_device()}'
    else:
        return 'cpu', 'CPU'


def to_device(data: Any, device: DeviceType | None = None) -> Any:
    """Move tensor/array to specified device."""
    if not TORCH_AVAILABLE:
        return data

    if device is None:
        device, _ = get_device()

    if isinstance(data, torch.Tensor):
        return data.to(device)
    elif isinstance(data, dict):
        return {k: to_device(v, device) for k, v in data.items()}
    elif isinstance(data, (list, tuple)):
        return type(data)(to_device(x, device) for x in data)
    return data


def mps_synchronized() -> None:
    """Synchronize MPS operations. Call after MPS kernel launches."""
    if TORCH_AVAILABLE and torch.backends.mps.is_available():
        torch.mps.synchronize()


def create_tensor(data: Any, dtype: Any = torch.float32, device: DeviceType | None = None) -> Any:
    """Create a tensor on the specified device."""
    if not TORCH_AVAILABLE:
        raise RuntimeError("PyTorch not available")

    if device is None:
        device, _ = get_device()

    if device == 'mps':
        return torch.tensor(data, dtype=dtype, device='mps')
    elif device == 'cuda':
        return torch.tensor(data, dtype=dtype, device='cuda')
    return torch.tensor(data, dtype=dtype)


def moving_average_torch(data: Any, window: int, device: DeviceType | None = None) -> Any:
    """MPS-accelerated moving average computation."""
    import numpy as np

    if not TORCH_AVAILABLE:
        if len(data) < window:
            return np.array([])
        return np.convolve(data, np.ones(window)/window, mode='valid')

    if device is None:
        device, _ = get_device()

    if len(data) < window:
        return np.array([])

    tensor = torch.tensor(data, dtype=torch.float32)
    kernel = torch.ones(window, dtype=torch.float32) / window

    if device == 'mps':
        kernel = kernel.to('mps')
        tensor = tensor.to('mps')

    result = torch.nn.functional.conv1d(
        tensor.view(1, 1, -1),
        kernel.view(1, 1, -1),
        padding=0
    ).view(-1)

    mps_synchronized()
    return result.cpu().numpy()


def exponential_moving_average_torch(data: Any, span: int, device: DeviceType | None = None) -> Any:
    """MPS-accelerated EMA computation using optimized scan operation."""
    import numpy as np

    if not TORCH_AVAILABLE:
        alpha = 2 / (span + 1)
        ema = np.empty(len(data), dtype=np.float64)
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1]
        return ema.astype(np.float32)

    if device is None:
        device, _ = get_device()

    data_np = np.asarray(data, dtype=np.float32)
    if len(data_np) < 100:
        alpha = 2 / (span + 1)
        alpha_tensor = torch.tensor(alpha, dtype=torch.float32, device=device)
        tensor = torch.from_numpy(data_np).to(device)
        result = torch.empty_like(tensor)
        result[0] = tensor[0]
        for i in range(1, len(tensor)):
            result[i] = alpha_tensor * tensor[i] + (1 - alpha_tensor) * result[i - 1]
        if device != 'cpu':
            mps_synchronized()
        return result.cpu().numpy()

    alpha = 2 / (span + 1)
    k = torch.tensor([[alpha]], dtype=torch.float32, device=device)
    tensor = torch.from_numpy(data_np).to(device)

    ema_state = tensor[0:1]
    result = [ema_state]

    alpha_k = k
    ones_minus_alpha = torch.tensor([[1 - alpha]], dtype=torch.float32, device=device)

    chunk_size = min(64, len(tensor))
    n_chunks = (len(tensor) - 1 + chunk_size - 1) // chunk_size

    for chunk_idx in range(n_chunks):
        start = 1 + chunk_idx * chunk_size
        end = min(start + chunk_size, len(tensor))
        chunk = tensor[start:end]

        chunk_alpha = alpha_k.expand(chunk_size, 1)
        chunk_result = []

        for i in range(end - start):
            ema_state = chunk_alpha[i] * chunk[i:i+1] + ones_minus_alpha * ema_state
            chunk_result.append(ema_state)

        if chunk_result:
            result.append(torch.cat(chunk_result, dim=0))
            ema_state = chunk_result[-1]

    final_result = torch.cat(result, dim=0)
    if device != 'cpu':
        mps_synchronized()
    return final_result.cpu().numpy()


def cleanup_mps_memory() -> None:
    """Clean up MPS GPU memory if available."""
    if TORCH_AVAILABLE and torch.backends.mps.is_available():
        try:
            torch.mps.empty_cache()
            logger.debug("MPS memory cache cleared")
        except Exception as e:
            logger.debug("Failed to clear MPS memory: %s", e)


def rolling_std_torch(data: Any, window: int, device: DeviceType | None = None) -> Any:
    """MPS-accelerated rolling standard deviation."""
    if not TORCH_AVAILABLE:
        import pandas as pd
        return pd.Series(data).rolling(window).std().fillna(0).values

    if device is None:
        device, _ = get_device()

    tensor = torch.tensor(data, dtype=torch.float32)
    if device == 'mps':
        tensor = tensor.to('mps')

    kernel_size = window
    kernel = torch.ones(kernel_size, dtype=torch.float32)
    if device == 'mps':
        kernel = kernel.to('mps')

    padding = kernel_size - 1
    padded = torch.nn.functional.pad(tensor.view(1, 1, -1), (padding, 0))
    local_means = torch.nn.functional.conv1d(padded, kernel.view(1, 1, -1) / kernel_size)
    squared_diffs = (tensor.view(-1) - local_means.view(-1)[:len(tensor)]) ** 2

    if device == 'mps':
        squared_diffs = squared_diffs.to('mps')

    local_variances = torch.nn.functional.conv1d(
        squared_diffs.view(1, 1, -1),
        kernel.view(1, 1, -1) / kernel_size
    )

    mps_synchronized()
    return torch.sqrt(local_variances.view(-1)).cpu().numpy()


# Register MPS memory cleanup with memory guard
try:
    from core.memory_guard import register_cleanup
    register_cleanup(cleanup_mps_memory)
except ImportError:
    logger.debug("Memory guard not available, skipping MPS cleanup registration")
