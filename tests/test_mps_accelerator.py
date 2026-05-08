"""Tests for MPS acceleration module."""
import numpy as np
import pytest

from core.mps_accelerator import (
    TORCH_AVAILABLE,
    create_tensor,
    exponential_moving_average_torch,
    get_device,
    moving_average_torch,
    rolling_std_torch,
    to_device,
)


class TestDeviceDetection:
    def test_get_device_returns_tuple(self):
        device_type, device_name = get_device()
        assert isinstance(device_type, str)
        assert isinstance(device_name, str)
        assert device_type in ('mps', 'cuda', 'cpu')

    def test_device_detection_cpu(self):
        device_type, device_name = get_device()
        if not TORCH_AVAILABLE:
            assert device_type == 'cpu'
        assert 'cpu' in device_name.lower() or 'mps' in device_name.lower() or 'cuda' in device_name.lower()


class TestMovingAverage:
    def test_moving_average_basic(self):
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = moving_average_torch(data, window=3)
        assert len(result) > 0
        assert result.dtype in (np.float32, np.float64)

    def test_moving_average_values(self):
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = moving_average_torch(data, window=3)
        expected_first = 2.0
        assert abs(result[0] - expected_first) < 0.01

    def test_moving_average_edge_cases(self):
        data = np.array([1.0])
        result = moving_average_torch(data, window=2)
        assert len(result) >= 0


class TestExponentialMovingAverage:
    def test_ema_basic(self):
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = exponential_moving_average_torch(data, span=3)
        assert len(result) == len(data)
        assert result[0] == data[0]

    def test_ema_decreasing_in_small_window(self):
        data = np.array([5.0, 4.0, 3.0, 2.0, 1.0])
        result = exponential_moving_average_torch(data, span=3)
        assert result[-1] < result[0]


class TestRollingStd:
    def test_rolling_std_basic(self):
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = rolling_std_torch(data, window=3)
        assert len(result) > 0
        assert np.all(result >= 0)


class TestToDevice:
    def test_to_device_dict(self):
        data = {"a": [1, 2, 3], "b": [4, 5, 6]}
        result = to_device(data, device='cpu')
        assert isinstance(result, dict)
        assert "a" in result
        assert "b" in result

    def test_to_device_list(self):
        data = [1, 2, 3]
        result = to_device(data, device='cpu')
        assert isinstance(result, list)
        assert len(result) == 3

    def test_to_device_primitive(self):
        data = 42
        result = to_device(data, device='cpu')
        assert result == 42


class TestCreateTensor:
    def test_create_tensor_cpu(self):
        if not TORCH_AVAILABLE:
            pytest.skip("PyTorch not available")
        data = [[1.0, 2.0], [3.0, 4.0]]
        result = create_tensor(data, device='cpu')
        assert result.device.type == 'cpu'
        assert result.shape == (2, 2)
