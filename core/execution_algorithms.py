from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MarketState:
    current_price: float
    current_volume: float
    vwap: float
    time_in_session_pct: float
    adv_20d: float
    bid_ask_spread: float


@dataclass(frozen=True)
class OrderSlice:
    quantity: int
    limit_price: float | None = None
    time_offset_seconds: float = 0.0
    algorithm_name: str = ""


@dataclass(frozen=True)
class FillResult:
    filled_quantity: int
    fill_price: float
    venue: str
    savings_bps: float


class ExecutionAlgorithm(ABC):
    @abstractmethod
    def next_slice(self, current_time: datetime, market_state: MarketState) -> OrderSlice | None:
        ...

    @abstractmethod
    def is_complete(self) -> bool:
        ...


class TWAPAlgorithm(ExecutionAlgorithm):
    def __init__(
        self,
        total_qty: int,
        start_time: datetime,
        end_time: datetime,
        n_slices: int = 10,
        jitter_pct: float = 0.0,
    ) -> None:
        if total_qty <= 0:
            raise ValueError(f"total_qty must be positive, got {total_qty}")
        if n_slices <= 0:
            raise ValueError(f"n_slices must be positive, got {n_slices}")
        if end_time <= start_time:
            raise ValueError("end_time must be after start_time")

        self._total_qty = total_qty
        self._start_time = start_time
        self._end_time = end_time
        self._n_slices = n_slices
        self._jitter_pct = max(0.0, min(jitter_pct, 0.5))
        self._filled_qty = 0
        self._slice_idx = 0

        base = total_qty // n_slices
        remainder = total_qty % n_slices
        self._slice_quantities = [base + (1 if i < remainder else 0) for i in range(n_slices)]

        interval = (end_time - start_time).total_seconds() / n_slices
        rng = np.random.default_rng()
        self._scheduled_times: list[datetime] = []
        for i in range(n_slices):
            offset = interval * (i + 0.5)
            if self._jitter_pct > 0:
                jitter = offset * self._jitter_pct * rng.uniform(-1, 1)
                offset += jitter
            self._scheduled_times.append(start_time + timedelta(seconds=offset))

    def next_slice(self, current_time: datetime, market_state: MarketState) -> OrderSlice | None:
        if self.is_complete():
            return None

        while self._slice_idx < self._n_slices and self._slice_quantities[self._slice_idx] <= 0:
            self._slice_idx += 1

        if self._slice_idx >= self._n_slices:
            return None

        scheduled = self._scheduled_times[self._slice_idx]
        if current_time < scheduled:
            return None

        qty = self._slice_quantities[self._slice_idx]
        remaining = self._total_qty - self._filled_qty
        qty = min(qty, remaining)
        self._filled_qty += qty
        self._slice_idx += 1

        logger.debug("TWAP slice %d: qty=%d, scheduled=%s", self._slice_idx, qty, scheduled.isoformat())

        return OrderSlice(
            quantity=qty,
            limit_price=None,
            time_offset_seconds=(scheduled - self._start_time).total_seconds(),
            algorithm_name="TWAP",
        )

    def is_complete(self) -> bool:
        return self._filled_qty >= self._total_qty


class VWAPAlgorithm(ExecutionAlgorithm):
    def __init__(
        self,
        total_qty: int,
        volume_profile: dict[str, float],
        start_time: datetime,
        end_time: datetime,
        n_slices: int = 10,
    ) -> None:
        if total_qty <= 0:
            raise ValueError(f"total_qty must be positive, got {total_qty}")
        if n_slices <= 0:
            raise ValueError(f"n_slices must be positive, got {n_slices}")
        if end_time <= start_time:
            raise ValueError("end_time must be after start_time")

        self._total_qty = total_qty
        self._start_time = start_time
        self._end_time = end_time
        self._n_slices = n_slices
        self._filled_qty = 0
        self._slice_idx = 0

        buckets = sorted(volume_profile.keys()) if volume_profile else []
        total_pct = sum(volume_profile.values()) if volume_profile else 0.0

        if total_pct < 1e-10 or not buckets:
            self._slice_pcts = [1.0 / n_slices] * n_slices
        else:
            raw_pcts = [volume_profile[b] / total_pct for b in buckets[:n_slices]]
            while len(raw_pcts) < n_slices:
                raw_pcts.append(raw_pcts[-1] if raw_pcts else 1.0 / n_slices)
            pct_sum = sum(raw_pcts)
            self._slice_pcts = [p / pct_sum for p in raw_pcts]

        self._slice_quantities = [max(1, int(total_qty * p)) for p in self._slice_pcts]
        diff = total_qty - sum(self._slice_quantities)
        for i in range(abs(diff)):
            idx = i % len(self._slice_quantities)
            if diff > 0:
                self._slice_quantities[idx] += 1
            elif self._slice_quantities[idx] > 1:
                self._slice_quantities[idx] -= 1

        interval = (end_time - start_time).total_seconds() / n_slices
        self._scheduled_times = [
            start_time + timedelta(seconds=interval * (i + 0.5))
            for i in range(n_slices)
        ]

    def next_slice(self, current_time: datetime, market_state: MarketState) -> OrderSlice | None:
        if self.is_complete():
            return None

        while self._slice_idx < self._n_slices and self._slice_quantities[self._slice_idx] <= 0:
            self._slice_idx += 1

        if self._slice_idx >= self._n_slices:
            return None

        scheduled = self._scheduled_times[self._slice_idx]
        if current_time < scheduled:
            return None

        remaining_qty = self._total_qty - self._filled_qty
        remaining_slices = self._n_slices - self._slice_idx

        if remaining_slices > 0 and market_state.adv_20d > 0 and market_state.current_volume > 0:
            expected_pct = self._slice_pcts[self._slice_idx]
            remaining_pct = sum(self._slice_pcts[self._slice_idx:])
            if remaining_pct > 1e-10:
                expected_bar_vol = market_state.adv_20d / self._n_slices
                volume_deviation = market_state.current_volume / expected_bar_vol if expected_bar_vol > 0 else 1.0
                adjusted_pct = (expected_pct / remaining_pct) * volume_deviation
                adjusted_pct = max(0.0, min(adjusted_pct, 1.0))
                qty = max(1, int(remaining_qty * adjusted_pct))
            else:
                qty = self._slice_quantities[self._slice_idx]
        else:
            qty = self._slice_quantities[self._slice_idx]

        qty = min(qty, remaining_qty)
        self._filled_qty += qty
        self._slice_idx += 1

        logger.debug(
            "VWAP slice %d: qty=%d, scheduled=%s, remaining=%d",
            self._slice_idx, qty, scheduled.isoformat(), remaining_qty - qty,
        )

        return OrderSlice(
            quantity=qty,
            limit_price=None,
            time_offset_seconds=(scheduled - self._start_time).total_seconds(),
            algorithm_name="VWAP",
        )

    def is_complete(self) -> bool:
        return self._filled_qty >= self._total_qty


class POVAlgorithm(ExecutionAlgorithm):
    def __init__(
        self,
        total_qty: int,
        participation_rate: float = 0.05,
    ) -> None:
        if total_qty <= 0:
            raise ValueError(f"total_qty must be positive, got {total_qty}")
        if participation_rate <= 0 or participation_rate >= 1.0:
            raise ValueError(f"participation_rate must be in (0, 1), got {participation_rate}")

        self._total_qty = total_qty
        self._participation_rate = participation_rate
        self._filled_qty = 0
        self._last_bar_volume: float | None = None

    def next_slice(self, current_time: datetime, market_state: MarketState) -> OrderSlice | None:
        if self.is_complete():
            return None

        remaining_qty = self._total_qty - self._filled_qty
        if remaining_qty <= 0:
            return None

        bar_volume = market_state.current_volume
        if bar_volume <= 0:
            return None

        if self._last_bar_volume is not None and abs(bar_volume - self._last_bar_volume) < 1e-10:
            return None
        self._last_bar_volume = bar_volume

        target_qty = int(bar_volume * self._participation_rate)
        qty = max(1, min(target_qty, remaining_qty))
        self._filled_qty += qty

        logger.debug(
            "POV slice: qty=%d, bar_vol=%.0f, participation=%.2f%%, remaining=%d",
            qty, bar_volume, self._participation_rate * 100, remaining_qty - qty,
        )

        return OrderSlice(
            quantity=qty,
            limit_price=None,
            time_offset_seconds=0.0,
            algorithm_name="POV",
        )

    def is_complete(self) -> bool:
        return self._filled_qty >= self._total_qty


class ISAlgorithm(ExecutionAlgorithm):
    def __init__(
        self,
        total_qty: int,
        risk_aversion: float,
        volatility: float,
        time_horizon: int,
        n_slices: int = 10,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> None:
        if total_qty <= 0:
            raise ValueError(f"total_qty must be positive, got {total_qty}")
        if risk_aversion < 0:
            raise ValueError(f"risk_aversion must be non-negative, got {risk_aversion}")
        if volatility < 0:
            raise ValueError(f"volatility must be non-negative, got {volatility}")
        if time_horizon <= 0:
            raise ValueError(f"time_horizon must be positive, got {time_horizon}")
        if n_slices <= 0:
            raise ValueError(f"n_slices must be positive, got {n_slices}")

        self._total_qty = total_qty
        self._risk_aversion = risk_aversion
        self._volatility = volatility
        self._time_horizon = time_horizon
        self._n_slices = n_slices
        self._start_time = start_time or datetime.now()
        self._end_time = end_time or (self._start_time + timedelta(seconds=time_horizon))
        self._filled_qty = 0
        self._slice_idx = 0

        self._trajectory = self.compute_optimal_trajectory()

        self._slice_quantities = [max(1, int(total_qty * f)) for f in self._trajectory]
        diff = total_qty - sum(self._slice_quantities)
        for i in range(abs(diff)):
            idx = i % len(self._slice_quantities)
            if diff > 0:
                self._slice_quantities[idx] += 1
            elif self._slice_quantities[idx] > 1:
                self._slice_quantities[idx] -= 1

        interval = (self._end_time - self._start_time).total_seconds() / n_slices
        self._scheduled_times = [
            self._start_time + timedelta(seconds=interval * (i + 0.5))
            for i in range(n_slices)
        ]

    def compute_optimal_trajectory(self) -> list[float]:
        kappa = self._risk_aversion * self._volatility * np.sqrt(self._time_horizon)
        n_slices = self._n_slices

        if kappa < 1e-10:
            return [1.0 / n_slices] * n_slices

        fractions: list[float] = []
        for k in range(1, n_slices + 1):
            remaining_before = np.sinh(kappa * (n_slices - k + 1)) / np.sinh(kappa * n_slices)
            remaining_after = np.sinh(kappa * (n_slices - k)) / np.sinh(kappa * n_slices)
            fractions.append(float(remaining_before - remaining_after))

        total = sum(fractions)
        if total < 1e-10:
            return [1.0 / n_slices] * n_slices

        return [f / total for f in fractions]

    def next_slice(self, current_time: datetime, market_state: MarketState) -> OrderSlice | None:
        if self.is_complete():
            return None

        while self._slice_idx < self._n_slices and self._slice_quantities[self._slice_idx] <= 0:
            self._slice_idx += 1

        if self._slice_idx >= self._n_slices:
            return None

        scheduled = self._scheduled_times[self._slice_idx]
        if current_time < scheduled:
            return None

        remaining_qty = self._total_qty - self._filled_qty
        qty = min(self._slice_quantities[self._slice_idx], remaining_qty)
        self._filled_qty += qty
        self._slice_idx += 1

        logger.debug(
            "IS slice %d: qty=%d, scheduled=%s, risk_aversion=%.2f",
            self._slice_idx, qty, scheduled.isoformat(), self._risk_aversion,
        )

        return OrderSlice(
            quantity=qty,
            limit_price=market_state.current_price,
            time_offset_seconds=(scheduled - self._start_time).total_seconds(),
            algorithm_name="IS",
        )

    def is_complete(self) -> bool:
        return self._filled_qty >= self._total_qty


class DarkPoolRouter:
    def __init__(
        self,
        internal_match_rate: float = 0.15,
        max_match_pct: float = 0.30,
    ) -> None:
        if internal_match_rate < 0 or internal_match_rate > 1.0:
            raise ValueError(f"internal_match_rate must be in [0, 1], got {internal_match_rate}")
        if max_match_pct <= 0 or max_match_pct > 1.0:
            raise ValueError(f"max_match_pct must be in (0, 1], got {max_match_pct}")

        self._internal_match_rate = internal_match_rate
        self._max_match_pct = max_match_pct
        self._rng = np.random.default_rng()
        self._total_matched_qty = 0
        self._total_attempted_qty = 0

    def try_internal_match(
        self,
        order: OrderSlice,
        market_state: MarketState | None = None,
    ) -> FillResult | None:
        if order.quantity <= 0:
            return None

        self._total_attempted_qty += order.quantity

        size_factor = np.exp(-order.quantity / 10000.0)
        fill_probability = self._internal_match_rate * size_factor

        if self._rng.random() > fill_probability:
            logger.debug("DarkPool: no match for qty=%d (prob=%.4f)", order.quantity, fill_probability)
            return None

        max_fill = max(1, int(order.quantity * self._max_match_pct))
        fill_qty = int(self._rng.integers(1, max_fill + 1))
        fill_qty = min(fill_qty, order.quantity)

        fill_price = 0.0
        savings_bps = 0.0
        if market_state is not None and market_state.current_price > 0:
            mid_price = market_state.current_price
            if market_state.bid_ask_spread > 0:
                mid_price = market_state.current_price - market_state.bid_ask_spread / 2.0
            fill_price = mid_price
            savings_bps = (market_state.bid_ask_spread / 2.0 / market_state.current_price) * 10000.0

        self._total_matched_qty += fill_qty

        logger.info(
            "DarkPool matched: qty=%d/%d, price=%.4f, savings=%.1fbps",
            fill_qty, order.quantity, fill_price, savings_bps,
        )

        return FillResult(
            filled_quantity=fill_qty,
            fill_price=round(fill_price, 4),
            venue="dark_pool",
            savings_bps=round(savings_bps, 2),
        )

    @property
    def match_rate(self) -> float:
        if self._total_attempted_qty <= 0:
            return 0.0
        return self._total_matched_qty / self._total_attempted_qty


class SmartOrderRouter:
    _SMALL_ADV_PCT = 0.01
    _MEDIUM_ADV_PCT = 0.05
    _LARGE_ADV_PCT = 0.10

    def __init__(self, dark_pool_router: DarkPoolRouter | None = None) -> None:
        self._dark_pool = dark_pool_router or DarkPoolRouter()

    def route_order(
        self,
        total_qty: int,
        symbol: str,
        adv_20d: float,
        urgency: float = 0.5,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        volume_profile: dict[str, float] | None = None,
        volatility: float = 0.02,
        n_slices: int = 10,
    ) -> ExecutionAlgorithm:
        if total_qty <= 0:
            raise ValueError(f"total_qty must be positive, got {total_qty}")
        if urgency < 0 or urgency > 1.0:
            raise ValueError(f"urgency must be in [0, 1], got {urgency}")

        now = start_time or datetime.now()
        default_end = end_time or (now + timedelta(hours=4))

        if adv_20d <= 0:
            logger.warning("ADV is zero for %s, defaulting to TWAP", symbol)
            return TWAPAlgorithm(total_qty, now, default_end, n_slices=n_slices)

        order_pct_adv = total_qty / adv_20d

        if order_pct_adv < self._SMALL_ADV_PCT:
            logger.info(
                "Routing %s: small order (%.2f%% ADV) → market (single-slice TWAP)",
                symbol, order_pct_adv * 100,
            )
            return TWAPAlgorithm(
                total_qty, now,
                now + timedelta(seconds=5),
                n_slices=1,
            )

        if order_pct_adv < self._MEDIUM_ADV_PCT:
            logger.info(
                "Routing %s: medium order (%.2f%% ADV) → VWAP",
                symbol, order_pct_adv * 100,
            )
            profile = volume_profile or self._default_volume_profile(n_slices)
            return VWAPAlgorithm(
                total_qty, profile, now, default_end, n_slices=n_slices,
            )

        if order_pct_adv < self._LARGE_ADV_PCT:
            if urgency > 0.5:
                risk_aversion = 0.5 + urgency * 4.5
                logger.info(
                    "Routing %s: large order (%.2f%% ADV), high urgency → IS (λ=%.2f)",
                    symbol, order_pct_adv * 100, risk_aversion,
                )
                return ISAlgorithm(
                    total_qty, risk_aversion, volatility,
                    time_horizon=int((default_end - now).total_seconds()),
                    n_slices=n_slices, start_time=now, end_time=default_end,
                )
            else:
                participation_rate = 0.03 + urgency * 0.07
                logger.info(
                    "Routing %s: large order (%.2f%% ADV), low urgency → POV (rate=%.2f%%)",
                    symbol, order_pct_adv * 100, participation_rate * 100,
                )
                return POVAlgorithm(total_qty, participation_rate=participation_rate)

        risk_aversion = 1.0 + urgency * 9.0
        logger.info(
            "Routing %s: very large order (%.2f%% ADV) → IS with dark pool (λ=%.2f)",
            symbol, order_pct_adv * 100, risk_aversion,
        )
        return ISAlgorithm(
            total_qty, risk_aversion, volatility,
            time_horizon=int((default_end - now).total_seconds()),
            n_slices=n_slices, start_time=now, end_time=default_end,
        )

    @property
    def dark_pool(self) -> DarkPoolRouter:
        return self._dark_pool

    @staticmethod
    def _default_volume_profile(n_slices: int) -> dict[str, float]:
        typical_u_shape = [0.06, 0.08, 0.09, 0.10, 0.11, 0.12, 0.11, 0.10, 0.10, 0.13]
        if n_slices <= len(typical_u_shape):
            raw = typical_u_shape[:n_slices]
        else:
            raw = typical_u_shape + [0.10] * (n_slices - len(typical_u_shape))
        total = sum(raw)
        return {f"bucket_{i}": v / total for i, v in enumerate(raw)}
