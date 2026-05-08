"""Tests for core.ml_utils module."""
from unittest.mock import patch

import numpy as np
import pytest

from core.ml_utils import (
    batch_process_with_memory_control,
    get_device,
    get_device_info,
    is_torch_available,
    optimize_numpy_memory,
    safe_to_numpy,
)


def _reset_device_state():
    """Reset global device caching state so tests are isolated."""
    import core.ml_utils as _mod
    _mod._current_device = None
    _mod._device_initialized = False
    get_device_info.cache_clear()


@pytest.fixture(autouse=True)
def reset_state():
    _reset_device_state()
    yield
    _reset_device_state()


class TestGetDevice:
    def test_returns_string(self):
        result = get_device()
        assert isinstance(result, str)
        assert result in ("mps", "cuda", "cpu")

    def test_force_cpu_returns_cpu(self):
        result = get_device(force_cpu=True)
        assert result == "cpu"


class TestIsTorchAvailable:
    def test_returns_bool(self):
        result = is_torch_available()
        assert isinstance(result, bool)


class TestSafeToNumpy:
    def test_numpy_passthrough(self):
        arr = np.array([1.0, 2.0, 3.0])
        result = safe_to_numpy(arr)
        assert isinstance(result, np.ndarray)
        np.testing.assert_array_equal(result, arr)

    def test_list_input(self):
        data = [1, 2, 3]
        result = safe_to_numpy(data)
        assert isinstance(result, np.ndarray)
        np.testing.assert_array_equal(result, np.array(data))

    def test_torch_tensor_converts(self):
        try:
            import torch
        except ImportError:
            pytest.skip("PyTorch not installed")
        t = torch.tensor([1.0, 2.0, 3.0])
        result = safe_to_numpy(t)
        assert isinstance(result, np.ndarray)
        np.testing.assert_array_almost_equal(result, np.array([1.0, 2.0, 3.0]))

    def test_gpu_tensor_converts(self):
        try:
            import torch
        except ImportError:
            pytest.skip("PyTorch not installed")
        device = get_device()
        if device == "cpu":
            pytest.skip("No GPU available")
        t = torch.tensor([1.0, 2.0, 3.0], device=device)
        result = safe_to_numpy(t)
        assert isinstance(result, np.ndarray)
        np.testing.assert_array_almost_equal(result, np.array([1.0, 2.0, 3.0]))


class TestOptimizeNumpyMemory:
    def test_float64_small_values_to_float32(self):
        arr = np.array([1.5, 2.3, 0.7], dtype=np.float64)
        result = optimize_numpy_memory(arr)
        assert result.dtype == np.float32

    def test_float64_large_values_stays(self):
        arr = np.array([1e8, 2e8], dtype=np.float64)
        result = optimize_numpy_memory(arr)
        assert result.dtype == np.float64

    def test_int16_range_downscaled(self):
        """Bug fix test: int64 values in int16 range must become int16.

        Previously int32 was checked first, making int16 unreachable.
        """
        arr = np.array([0, 100, -100, 32767, -32768], dtype=np.int64)
        result = optimize_numpy_memory(arr)
        assert result.dtype == np.int16, (
            f"Expected int16 for int16-range values, got {result.dtype}"
        )

    def test_int32_range_downscaled(self):
        arr = np.array([0, 100000, -100000], dtype=np.int64)
        result = optimize_numpy_memory(arr)
        assert result.dtype == np.int32

    def test_int64_large_stays(self):
        arr = np.array([0, 2**40], dtype=np.int64)
        result = optimize_numpy_memory(arr)
        assert result.dtype == np.int64

    def test_explicit_dtype_override(self):
        arr = np.array([1.0, 2.0], dtype=np.float32)
        result = optimize_numpy_memory(arr, dtype=np.float64)
        assert result.dtype == np.float64

    def test_float32_stays(self):
        arr = np.array([1.0, 2.0], dtype=np.float32)
        result = optimize_numpy_memory(arr)
        assert result.dtype == np.float32


class TestGetDeviceInfo:
    def test_returns_dict_with_expected_keys(self):
        info = get_device_info()
        assert isinstance(info, dict)
        assert "torch_available" in info
        assert "device" in info
        assert isinstance(info["torch_available"], bool)
        assert info["device"] in ("mps", "cuda", "cpu")

    def test_torch_keys_when_available(self):
        if not is_torch_available():
            pytest.skip("PyTorch not installed")
        info = get_device_info()
        assert "torch_version" in info
        assert "mps_available" in info
        assert "cuda_available" in info


class TestBatchProcessWithMemoryControl:
    @patch("core.memory_guard.is_memory_critical", return_value=False)
    @patch("core.memory_guard.check_and_reclaim_if_needed", return_value=True)
    def test_basic_batch_processing(self, mock_reclaim, mock_critical):
        data = list(range(10))
        results = batch_process_with_memory_control(
            data,
            processor=lambda batch: [x * 2 for x in batch],
            batch_size=3,
            max_memory_mb=256,
        )
        assert results == [x * 2 for x in range(10)]

    @patch("core.memory_guard.is_memory_critical", return_value=False)
    @patch("core.memory_guard.check_and_reclaim_if_needed", return_value=True)
    def test_single_item_batches(self, mock_reclaim, mock_critical):
        data = [1, 2, 3]
        results = batch_process_with_memory_control(
            data,
            processor=lambda batch: sum(batch),
            batch_size=1,
            max_memory_mb=256,
        )
        assert results == [1, 2, 3]
