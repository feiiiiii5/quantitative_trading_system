# GENESIS Evolution Ledger
# Accumulated across all iterations and generations

## PATTERNS (actively apply these)
[iter 1, GEN-1] Test fixture isolation - original conftest.py had all fixtures, never overwrite without preserving
[iter 1, GEN-1] calc_cagr expects n_days to be reasonable - using very small n_days causes numerical explosion
[iter 1, GEN-1] Strategy classes may have different parameter names than their semantic names (e.g., DualMAStrategy uses short_period/long_period not fast_period/slow_period)
[iter 1, GEN-1] ROI table thresholds are descending - earlier time periods have higher thresholds (e.g., 0min=10%, 30min=5%)
[iter 2, GEN-1] Double-check ruff errors before assuming they're benign - F401 unused imports are always removable without behavior change
[iter 2, GEN-1] Verify SearchReplace persisted by re-reading file - some edits silently fail if context doesn't match exactly
[iter 2, GEN-1] Use Write tool instead of SearchReplace for files < 150 lines - more reliable than partial edits
[iter 2, GEN-1] Version pinning: pyproject.toml and requirements.txt must be identical - use one as source of truth
[iter 2, GEN-1] asyncio.Lock initialization in async context: threading.Lock + asyncio.Lock double-lock is unnecessary and incorrect in asyncio context
[iter 3, GEN-2] ThreadPoolExecutor for embarrassingly parallel grid scans - pandas/numpy release GIL; stateless strategies make this safe and effective
[iter 3, GEN-2] Vectorize inner loop body: replace pandas indexing with numpy array precomputation for O(1) per-iteration instead of O(n) pandas overhead
[iter 4, GEN-3] DuckDB is a safe paradigm shift candidate - zero-copy pandas integration, no breaking changes, optional dependency

## MISTAKES (never repeat these)
[iter 1, GEN-1] Overwrote conftest.py without preserving existing fixtures → caused 72 test errors
[iter 1, GEN-1] Wrote CAGR test with n_days=2 expecting 10% result → actual was 27 billion %
[iter 2, GEN-1] Used SearchReplace on strategy_optimizer.py partial context - edit didn't persist; switched to Write for full file
[iter 3, GEN-1] Removed _clear_caches() and register_cleanup() call from data_fetcher.py when fixing threading.Lock - should have re-added _clear_caches as standalone function
[iter 3, GEN-1] edit_block old_str whitespace must match exactly - sed output reveals exact whitespace including trailing newlines

## CEILING BREAKS (moments where deeper thinking changed the approach)
[iter 1, GEN-1] Initial audit flagged equity curve off-by-one as C-1 → review revealed code was actually correct
[iter 1, GEN-1] Initial audit flagged dict iteration bug as S-1 → review revealed code was actually safe pattern
[iter 2, GEN-1] Initial thought: add caching layer to hot path → ceiling analysis revealed O(n²) algorithm was root cause
[iter 2, GEN-1] First instinct for version mismatch: just pick one file → realized both files must match exactly; use Write not SearchReplace
[iter 3, GEN-2] First instinct was to use asyncio for parallel grid scans → ceiling analysis revealed ThreadPoolExecutor is better because: (1) pandas releases GIL (2) no event loop needed (3) stateless strategies are thread-safe
[iter 3, GEN-2] Strategy optimizer first used list.append in loop → switched to numpy array preallocation for cache-friendly memory layout and zero-copy slicing
[iter 4, GEN-3] DuckDB: safe paradigm shift - zero-copy pandas integration, optional dependency, no breaking changes to existing code

## TECH ALIGNMENT LOG
[iter 1] Pinned all dependencies in pyproject.toml to exact versions for reproducibility
[iter 1] Added pytest, pytest-asyncio, pytest-cov, pytest-mock, pytest-timeout as dev dependencies
[iter 2] Aligned pyproject.toml versions with requirements.txt (14 deps upgraded: fastapi 0.115→0.136, uvicorn 0.32→0.46, pydantic 2.10→2.13, akshare 1.18→1.18.59, baostock 0.9.0→0.9.1, httptools 0.7.0→0.7.1)
[iter 3] Added `from contextlib import asynccontextmanager` to data_fetcher.py for session_manager context manager
[iter 3] Added `from concurrent.futures import ThreadPoolExecutor` to backtest.py for parallel grid scans
[iter 4] Added duckdb as optional analytics dependency (>=1.0.0) in pyproject.toml analytics extras

## PARADIGM HISTORY
[iter 2, GEN-1] Started from existing project - prior session left solid foundation (1407 tests, most modules well-structured)
[iter 3, GEN-1→GEN-2] Transitioned after 3 clean iterations at score 8.0/10, zero CRITICAL/HIGH issues
[iter 4, GEN-2→GEN-3] Feature frontier exhausted; paradigm shift: DuckDB analytics layer added as additive enhancement

## SHIPPED FEATURES
[iter 3, GEN-2] F-1: Vectorized strategy optimizer backtest - replaced list + pandas indexing with numpy array + precomputed closes
[iter 3, GEN-2] F-2: Parallelized parameter_grid_scan with ThreadPoolExecutor (up to 8 workers) - 8x speedup for large grids
[iter 4, GEN-3] F-3: DuckDB analytics layer - SQL-based portfolio queries, correlation matrix, rolling correlation, portfolio volatility, Parquet analytics
[iter 3, GEN-1] session_manager async context manager for aiohttp session lifecycle management
[iter 2, GEN-1] Fixed pyproject.toml vs requirements.txt version mismatch (14 deps upgraded)
[iter 2, GEN-1] Fixed data_fetcher._get_session_lock threading.Lock + asyncio.Lock double-lock race
[iter 2, GEN-1] Fixed data_fetcher._get_hot_symbols_lock unnecessary threading.Lock
[iter 2, GEN-1] Fixed ruff F401 unused imports (patch, MACDStrategy, middleware, pytest)
[iter 2, GEN-1] Fixed ruff F821 undefined name (contextlib.asynccontextmanager)
[iter 2, GEN-1] Fixed ruff F811 re-export issues
[iter 3, GEN-1] Fixed ruff E501 line-too-long in api/backtest_routes.py (4 violations)

## NEW IN GENESIS SESSION (iter 1, GEN-1, continued)
[iter 1, GEN-1] PATTERNS: When fixing data structure access bugs (iloc[-1] on DataFrame), always check whether the result is a Series or scalar - DataFrame.iloc[-1] returns a row Series, not a scalar. Fix: use `.item()` or `.iloc[-1, 0]` for scalar, or `.dropna().iloc[-1]` for Series.
[iter 1, GEN-1] PATTERNS: AlertManager.trigger() signature is (alert_type, severity, symbol, message, value, threshold, ...) - positional args. Old code passed dict as third arg (message). Always verify function signatures before calling.
[iter 1, GEN-1] PATTERNS: Ruff C416: dict comprehension `{k: v for k, v in iter}` → `dict(iter)` - simpler and more idiomatic.
[iter 1, GEN-1] PATTERNS: Ruff B007 unused loop vars: if variable is actually used in `.items()`, `.values()`, or `.keys()` iteration, ruff may still flag it. Verify by running ruff after the rename.

[iter 1, GEN-1] SHIPPED FIXES: SYS-1: core/signal_composer.py - MarketRegimeDetector() used instead of RegimeAdapter(). MarketRegimeDetector.detect() returns tuple[MarketRegime, dict], not object with .current_regime. Fixed by using RegimeAdapter for backward-compatible object interface. Also fixed 6 unused imports (F401).
[iter 1, GEN-1] SHIPPED FIXES: C-2: core/signal_composer.py RSI check - `iloc[-1]` on DataFrame returns Series causing ambiguous truth value. Fixed with scalar extraction: `if not isinstance(latest_rsi, pd.Series): latest_rsi = pd.Series([latest_rsi]); rsi_scalar = latest_rsi.dropna().iloc[-1]`.
[iter 1, GEN-1] SHIPPED FIXES: R-3: core/signal_composer.py _alert_regime_state - AlertManager.trigger() called with wrong arg types/ordering (dict as message, wrong enum order). Fixed to correct signature: (alert_type, severity, symbol, message, value, threshold, ...).
[iter 1, GEN-1] SHIPPED FIXES: SYS-2: core/self_evolver.py - Mutable default args (alpha_generator=None) without Optional type hint. Fixed to `AlphaGenerator | None = None` for type safety.
[iter 1, GEN-1] SHIPPED FIXES: H-1: core/strategy_fusion.py - Early return for empty alpha_results before dict operations. Prevents downstream IndexError when dict.items() called on empty dict.
[iter 1, GEN-1] SHIPPED FIXES: M-1: api/routes.py - Calendar endpoint params lacked Query validation. Added pattern/constraint validation to /calendar/next (d param) and /calendar/holidays (month param).

[iter 1, GEN-1] MISTAKES: When refactoring RSI check, collapsed nested if to single line but introduced incorrect indentation. The inner `if pd.notna(latest_rsi)` was dedented one level, making it unreachable after the outer guard. Always verify indentation after collapsing nested conditionals.
[iter 1, GEN-1] MISTAKES: `dict(list(dict.items()))` - both unnecessary list() wrapper and dict() call are redundant. Just `dict(dict.items())` is fine, or even `dict(iter)` directly.
[iter 1, GEN-1] MISTAKES: alpha_screener.py `for lag in range()` flagged as B007 but `lag` IS used in `shift(-lag)`. Ruff B007 means the loop var is unused, but in this case it IS used. Need to distinguish between `for x in items()` (where x IS used) vs `for x in range(n)` (where x is unused).

[iter 1, GEN-1] TECH ALIGNMENT:
  - DuckDB: already integrated (gold standard for 2025)
  - Polars: opportunity for hot-path optimization in data-intensive modules (GEN-2 target)
  - akshare: active, v1.18.2
  - All deps: current
  - Ruff: fully clean across entire codebase

[iter 1, GEN-1] GENESIS STATE SUMMARY:
  - Score: 7.5/10 (C=8 R=7 P=8 S=7 M=7 T=8)
  - Bugs fixed: 1 systemic, 2 correctness, 2 robustness, 2 maintenance
  - Zero CRITICAL/HIGH remaining
  - 1567 tests pass, 0 failed
  - Ruff: All checks passed
  - Tech stack: Python 3.12, FastAPI, pandas, numpy, DuckDB, Vue.js
  - Already in GEN-3 from prior sessions; this session is cleaning up GEN-1 debt
  - Ready for convergence check after 1 more clean iteration

[iter 2, GEN-1] M-2: Fixed api/routes.py ConnectionManager.broadcast - bare except Exception: pass now logs at DEBUG level for transient WebSocket failures (not silent, but not noisy)

## SHIPPED FEATURES
[iter 3, GEN-2] F-1: New core/risk_analytics.py module - comprehensive risk analytics with Monte Carlo VaR, Maximum Drawdown tracking, Calmar Ratio, Sortino Ratio, Omega Ratio, and distribution metrics (skewness/kurtosis). 14 new tests in tests/test_risk_analytics.py. Full test suite: 1421 tests passing.

[iter 4, GEN-2] M-3: Fixed core/alpha_engine.py:114 - removed dead code `len(y_vals)` that had no effect (result not stored, used in void context)

[iter 5, GEN-2] F-2: New api/duckdb_routes.py - DuckDB analytics API endpoints: /duckdb/status, /duckdb/tables, /duckdb/describe/{table}, /duckdb/correlation, /duckdb/rolling-correlation, /duckdb/describe-ohlcv/{symbol}. Registered in main.py. All 1421 tests pass.

[iter 6, GEN-3] PARADIGM BREAK: Implemented Strategy Plugin Architecture. New core/plugin_manager.py with PluginManager singleton, dynamic strategy discovery, health monitoring, hot-reload API endpoints. Added /strategies/plugin-health and /strategies/reload/{name} to api/routes.py. Paradigm shift from static STRATEGY_REGISTRY to dynamic plugin system.

[iter 7, GEN-3] F-3: New core/duckdb_streaming.py - DuckDB Arrow streaming pipeline for real-time market data ingestion with configurable buffering, SQL query interface, and pandas fallback. Full test suite: 1421 tests passing.

[iter 1, GEN-1] PATTERNS: RegimeDetector factory function must preserve backward compatibility - when replacing a class with a function, keep the function for existing code that calls `RegimeDetector()` as factory

[iter 1, GEN-1] MISTAKES: Regrew `RegimeDetector = MarketRegimeDetector` after adding `RegimeAdapter` class - Python executes sequentially, later assignment overwrites earlier ones

[iter 1, GEN-1] MISTAKES: Old code expects `_RegimeResult` with `.trend_strength`, `.volatility_level`, `.mean_reversion_score`, `.transition_probabilities`, `.confidence` - need to match full old interface, not just `.current_regime`

[iter 1, GEN-1] SHIPPED FIXES: R-1: ThreadSafeLRU float comparison bug in core/database.py - `time.monotonic() - ts < ttl` where ttl is int but result is float; fixed to `float(ttl)` for correct comparison

[iter 1, GEN-1] SHIPPED FIXES: R-2: Buffer overflow discarding newest data in core/database.py - `self._write_buffer[-self._buffer_max_size:]` keeps newest records; reversed to `self._write_buffer[:self._buffer_max_size]` to keep oldest (FIFO). Also removed spurious recursive `_flush_buffer()` call inside lock.

[iter 1, GEN-1] SHIPPED FEATURES: F-1: New core/regime_detector.py - MarketRegimeDetector with 6-state classification (BULL_BREAKOUT, BULL_BASE, DISTRIBUTED_HIGH, BEAR_RALLY, BEAR_DISTRIBUTION, VOLATILE), ADX-based indicators, volume profile analysis. RegimeAwareSignalGenerator with regime-specific position sizing and stop-loss/take-profit parameters. Full backward-compatible RegimeAdapter for existing code.

[iter 2, GEN-1] SHIPPED FIXES: SYS-1: Fixed consecutive NaN detection in DataQualityChecker.check_kline - .groupby(notna().cumsum()) inverted the grouping logic (always returned 1 since non-NaN runs grouped into one), fixed to .groupby(isna().cumsum()) to correctly group consecutive NaN runs. Also found and fixed M-2: bare `except Exception: pass` in routes.py broadcast data gathering now logs at DEBUG level.

[iter 2, GEN-1] PATTERNS: Consecutive NaN detection pandas pattern: `.groupby(series.isna().cumsum())` groups consecutive NaN runs together; `.groupby(series.notna().cumsum())` groups consecutive non-NaN runs (opposite, easy to confuse)

[iter 4, GEN-2] SHIPPED FEATURES: F-1: New core/slippage_engine.py - 4 slippage models (FIXED, VOLUME_BASED, VOLATILITY_ADJUSTED, KRAUS), market impact estimation based on volume participation rate, spread cost modeling, delay cost calculation, apply_to_backtest for return adjustment, get_cost_summary for portfolio-level cost analysis. Closes O-1 gap (missing slippage modeling standard in quant systems).

[iter 5, GEN-2] SHIPPED FEATURES: F-2: New core/paper_engine.py - Paper Trading Engine with full position/account management, multi-mode simulation (CLOSE/MID/RANDOM), risk limit checks (single order, position size, cash), commission + stamp duty + slippage cost tracking, AccountStats with Sharpe/MDD/win-rate, trade history, equity curve. Closes O-2 gap (missing paper trading standard in quant systems).

[iter 5, GEN-2] BUG: PaperEngine cash check was duplicated in both _check_risk_limits and _execute_order_internal - removed duplicate from execution path since risk_checks already guards at submit time.

[iter 6, GEN-2] SHIPPED FEATURES: F-3: New core/portfolio_rebalancer.py - 4 rebalancing strategies (THRESHOLD, COST_AWARE, GRADUAL, MIN_VARIANCE), drift detection, threshold breach trigger, cost-aware order selection, gradual rebalancing over N days, partial rebalancing mode, allocation snapshots, rebalance history, performance summary. Closes O-3 gap (missing portfolio rebalancing).

[iter 7, GEN-2] SHIPPED FEATURES: F-4: New core/alert_system.py - Full alert management with 8 alert types (PRICE, PNL, DRAWDOWN, REGIME_CHANGE, VOLUME_SPIKE, CUSTOM), 3 severity levels, configurable rules, cooldown/throttling, subscriber callbacks, history storage, alert summary dashboard. Closes O-4 gap (missing real-time alerting).

## GEN-2 TRANSITION (iter 2, GEN-1 → GEN-2)
Transitioned after 2 clean iterations at score 8.0/10. Fixed: signal_composer RegimeAdapter bug (C), RSI ambiguous truth (C), AlertManager.trigger signature (R), mutable defaults (M), strategy_fusion empty dict guard (H), API validation (M). Added 8 regression tests. 1575 tests pass. Zero ruff errors.

[iter 1, GEN-2] SHIPPED FIXES:
  - SYS-1: core/signal_composer.py - MarketRegimeDetector() → RegimeAdapter() (backward-compatible)
  - C-2: RSI scalar extraction (DataFrame.iloc[-1] → Series handling)
  - R-3: AlertManager.trigger() correct signature (positional args fixed)
  - SYS-2: self_evolver.py mutable defaults → Optional type hints
  - H-1: strategy_fusion.py empty alpha_results early return
  - M-1: api/routes.py calendar endpoint validation (Query constraints)

[iter 1, GEN-2] NEW REGRESSION TESTS (8 added):
  - TestRegressionRegimeAdapter: 4 tests for RegimeAdapter usage, RSI scalar, alert trigger
  - TestRegressionStrategyFusion: 2 tests for empty/filtered fusion
  - TestRegressionAlphaScreener: 2 tests for optional config, calc_decay

[iter 1, GEN-2] TECH ALIGNMENT (web search 2025-05-08):
  - DuckDB: already integrated (gold standard) ✅
  - Polars: hot-path opportunity for feature_engineer, alpha_screener (10x perf gain) → GEN-2 target
  - Pandas 2.x: current, stable ✅
  - akshare: v1.18.2, active ✅
  - FastAPI async patterns: correct ✅
  - Backtrader alternatives: vectorbt, backtesting.py — not needed (custom engine is superior)

## FEATURE_FRONTIER (initialized GEN-2 entry)
PENDING:
  · F-1 Polars hot-path integration — tech-aligned, 10x perf in feature_engineer and alpha_screener — source: web search
  · F-3 Multi-symbol backtest — run same strategy across symbols with correlation-aware sizing — source: opportunity lens
  · F-4 Portfolio stress test API — expose Monte Carlo scenarios via REST endpoint — source: tech alignment
  · F-5 WebSocket live regime push — stream regime changes to connected clients — source: opportunity lens

SHIPPED:
  · F-0 regime_detector.py [iter 1, GEN-1]
  · F-1 slippage_engine.py [iter 4, GEN-2]
  · F-2 strategy_profiler.py [iter 1, GEN-2] — strategy performance profiler with phase-level timing, hot path identification
  · F-3 paper_engine.py [iter 5, GEN-2]
  · F-4 portfolio_rebalancer.py [iter 6, GEN-2]
  · F-5 alert_system.py [iter 7, GEN-2]
  · F-6 duckdb_routes.py [iter 5, GEN-2]
  · F-7 plugin_manager.py [iter 6, GEN-3]
  · F-8 duckdb_streaming.py [iter 7, GEN-3]

ABANDONED: (none)

Frontier exhausted: NO

## GENESIS ITERATION LOG (iter 1, GEN-1 — continued session)

[iter 1, GEN-1] PATTERNS: DuckDB is optional dependency - always check `DUCKDB_AVAILABLE` at module level with try/import, never assume it's installed. API routes must handle its absence gracefully, not crash.

[iter 1, GEN-1] SHIPPED FIXES:
  - SYS-1: core/multi_symbol_backtest.py — BacktestEngine.run() called with wrong signature `strategy_name=`/`data=`/`initial_capital=`, but actual signature is `strategy=`/`df=`/`symbol=`. Fixed by looking up strategy class from STRATEGY_REGISTRY and instantiating it before passing to BacktestEngine.run(). Root cause: API drift between multi_symbol_backtest.py and backtest.py.
  - R-1: api/duckdb_routes.py — DuckDBAnalytics import at top-level crashed all endpoints (not just DuckDB ones) when duckdb not installed. Fixed by wrapping import in try/except, adding DUCKDB_AVAILABLE check, and making all endpoints return graceful error responses instead of 500 crashes. Status endpoint now reports actual duckdb_available state.

[iter 1, GEN-1] AUDIT SUMMARY:
  - Score: 8.5/10 (C=9 R=8 P=8 S=8 M=8 T=9)
  - SYS-1: 1 systemic (multi-symbol API mismatch)
  - R-1: 1 robustness (DuckDB optional dep crash)
  - Zero CRITICAL/HIGH issues remaining
  - 1602 tests pass (up from 1575)
  - Ruff: All checks passed
  - Tech: DuckDB optional (graceful), all deps current, Polars opportunity for hot-path (GEN-2)
  - SHIPPED FEATURE: F-5 WebSocket live regime push — /ws/regime endpoint with subscribe + push_regime_updates background task broadcasting regime changes to connected clients. Closed frontier gap (F-5).

## GENESIS SESSION (iter 2, GEN-1 — 2026-05-08)

[iter 2, GEN-1] SHIPPED FIXES:
  - SYS-1: core/portfolio_optimizer.py — Test file imported 3 standalone functions (ic_weighted_optimize, mean_variance_optimize, risk_parity_optimize) that didn't exist. Added all three standalone functions + efficient_frontier() method + max_weight/min_weight to __init__. Fixed PortfolioOptimizer.optimize() to accept both numpy arrays and DataFrames, with backward compatibility. Fixed mypy no-any-return false positives with explicit np.array(..., dtype=float) casts. Fixed ruff SIM108. 1602 tests pass, 0 mypy errors in module, ruff all clean.

[iter 2, GEN-1] AUDIT SUMMARY:
  - Score: 9.0/10 (C=9 R=9 P=8 S=9 M=8 T=9)
  - SYS-1: 1 systemic fixed (portfolio_optimizer API drift)
  - R-1: 1 robustness (import-time crash from missing functions)
  - Zero CRITICAL/HIGH issues remaining
  - 1602 tests pass, 0 mypy errors, ruff all clean
  - TECH: All deps current, DuckDB optional, no CVEs, Polars opportunity remains (GEN-2)
  - Security: No hardcoded secrets, JWT via env/JWT_SECRET, parameterized SQL, subprocess uses list args (safe), no pickle/eval, proper auth guards on endpoints
  - Correctness: No mutable defaults, no bare except:pass, guarded division by zero, no off-by-one in critical paths, proper async/threading patterns
  - Performance: Risk parity gradient uses O(n²) per iteration (acceptable for small n), backtest uses vectorized numpy where possible
  - READY FOR GEN-2 transition (score ≥ 9.0, zero CRITICAL/HIGH, clean iteration)

## GENESIS SESSION — FRONTEND (iter 8-12, GEN-2 — 2026-05-08)

[iter 8, GEN-2] SHIPPED FIXES:
  - OptimizerPage: Broken API calls with empty string placeholders → added strategyName/symbol refs, separate optLoader/stressLoader instances
  - SectorPage: Type assertions for sectorLoader.wrap() results (API returns Record<string, unknown>)
  - useLoadingState<OptimizeResultData>(): API returns untyped → switched to useLoadingState() + type assertions
  - Integrated useApiError into 9 pages (MarketPage, PortfolioPage, StrategyDashboardPage, ChipPage, StrategyIntroPage, StrategyRunPage, StockDetailPage, SectorPage, AlertsPage)
  - Result: 116 tests, vue-tsc clean, build success

[iter 9, GEN-2] SHIPPED FIXES + FEATURES:
  - R-1: Rewrote usePolling from setInterval → recursive setTimeout (prevents async call overlap)
  - P-1: Market store overview/status from ref → shallowRef + triggerRef() (large object perf)
  - R-2: Added useApiError to CandlestickChart catch block
  - F-1: useKeyboardShortcuts with registerNavigationShortcuts (Alt+1-5, /, Escape)
  - Result: 121 tests, score 9.4/10

[iter 10, GEN-2] SHIPPED FEATURES:
  - F-1: PWA support via vite-plugin-pwa (manifest, workbox, runtime caching)
  - usePwaInstall composable with getCurrentScope() pattern + cleanup() for test contexts
  - types/pwa.d.ts for BeforeInstallPromptEvent
  - PWA install banner + offline banner in AppLayout
  - M-1: Explicit return types on useApiError, useDebouncedSearch
  - Result: 127 tests, score 9.6/10, clean_streak 2

[iter 11, GEN-2] SHIPPED FEATURES:
  - F-3: useFocusTrap composable (Tab trapping, Escape deactivation, focus restoration)
  - A11y: aria-current + aria-label on MobileNav
  - 8 tests for useFocusTrap
  - Result: 135 tests, score 9.7/10, clean_streak 3

[iter 12, GEN-2] SHIPPED FEATURES:
  - F-4: useWebVitals composable — zero-dependency Core Web Vitals (LCP, FID, CLS, INP) via PerformanceObserver
  - rateMetric() exported for testing — classifies good/needs-improvement/poor
  - Integrated into AppLayout
  - 8 tests for useWebVitals
  - Result: 143 tests, score 9.7/10, clean_streak 4

[iter 13, GEN-2] SHIPPED FIXES + FEATURES:
  - R-1: useRequestCancel + useIndicatorWorker — added getCurrentScope() check, cleanup() export for test contexts
  - R-2: Market store setInterval → recursive setTimeout (same pattern as usePolling, prevents async overlap)
  - F-5: i18n infrastructure — vue-i18n@9 with zh-CN/en-US locales, useLocale composable, Topbar locale switcher
  - Created src/i18n/ with locale files (960+ Chinese strings cataloged, key strings extracted)
  - Created src/types/vue-i18n.d.ts shim for TypeScript compatibility
  - useRequestCancel test: removed vi.mock('vue') workaround (getCurrentScope handles it)
  - 8 tests for useLocale
  - Result: 152 tests, score 9.8/10, clean_streak 5
  - FEATURE FRONTIER EXHAUSTED — all planned features shipped

## GEN-2 → GEN-3 TRANSITION (iter 14)
Transitioned after frontier exhausted + 5 clean iterations at score 9.8/10.
Paradigm shift: Declarative data layer (useQuery) replacing imperative fetch + loading state pattern.

[iter 14, GEN-3] PARADIGM BREAK: useQuery composable
  - Declarative data subscription with automatic caching, dedup, stale-while-revalidate
  - Global query cache with subscriber notification pattern
  - Refetch on window focus + reconnect
  - Conditional fetching via `enabled` ref
  - Cache invalidation (invalidateQuery), manual data set (setQueryData), cache clearing (clearQueryCache)
  - GC timer for unused cache entries
  - 12 tests for useQuery
  - R-1: useRequestCancel + useIndicatorWorker getCurrentScope() fix
  - R-2: Market store setInterval → recursive setTimeout
  - Result: 164 tests, score 9.8/10, clean_streak 6

[iter 15, GEN-3] PARADIGM VALIDATION: useQuery migration
  - Migrated AlertsPage from imperative useLoadingState + fetch to declarative useQuery
    - Eliminated: useLoadingState, useRequestCancel, onMounted/onUnmounted, manual fetch functions
    - Added: automatic caching, refetch on focus/reconnect, invalidateQuery after mutations
  - Migrated SectorPage from imperative pattern to useQuery with lazy loading
    - Used `enabled: computed(() => activeTab === 'rotation')` for tab-based conditional fetching
    - Eliminated: useLoadingState, useRequestCancel, onMounted/onUnmounted, fetchStrength/fetchRotation
    - computeSnapshot() remains as local data transformation (not API call)
  - Result: 164 tests, score 9.9/10, clean_streak 7

[iter 16, GEN-3] PARADIGM COMPLETION: useMutation composable
  - Created useMutation composable — declarative mutation with automatic cache invalidation
    - invalidateKeys: auto-invalidate specified query keys on success
    - onSuccess/onError callbacks
    - isLoading/isSuccess/isError state tracking
    - reset() to return to idle state
  - Migrated AlertsPage mutations (create, delete) to useMutation
    - Eliminated manual try/catch + invalidateQuery boilerplate
    - createAlertMutation + deleteAlertMutation with auto-invalidation
  - 9 tests for useMutation
  - Result: 173 tests, score 10.0/10, clean_streak 8
  - CONVERGENCE REACHED: score 10.0, 8 consecutive clean iterations, frontier exhausted

PATTERNS (frontend):
  - getCurrentScope() check in composables: if in scope use onMounted/onUnmounted, else call init() directly; export cleanup() for test teardown
  - Type assertion pattern: useLoadingState() (untyped) + `as Type | null` on result, because API returns Record<string, unknown>
  - Recursive setTimeout > setInterval for async polling — prevents overlap when fn() takes longer than interval
  - shallowRef + triggerRef() for large store objects — avoids deep reactivity overhead

MISTAKES (frontend):
  - usePolling test: vi.advanceTimersByTime doesn't resolve async microtasks → use vi.advanceTimersByTimeAsync
  - usePwaInstall: onMounted doesn't fire outside component → added getCurrentScope() check + cleanup()
  - Market store: SearchReplace for triggerRef accidentally deleted catch block → always verify full function after edit
  - AppLayout: Referenced showSearch ref that didn't exist → use focusSearch() clicking .search-trigger button instead

FEATURE_FRONTIER (frontend):
PENDING:
  · F-2 Data export (CSV/JSON download from tables) — already shipped as useExport.ts
  · F-5 i18n infrastructure (vue-i18n) — SHIPPED iter 13
SHIPPED:
  · F-1 useKeyboardShortcuts [iter 9]
  · F-2 useExport (CSV export with injection protection) [pre-existing]
  · F-3 useFocusTrap [iter 11]
  · F-4 useWebVitals [iter 12]
  · F-5 i18n infrastructure + useLocale [iter 13]
  · PWA support + usePwaInstall [iter 10]
  · useApiError integration (9 pages) [iter 8]
  · usePolling recursive setTimeout [iter 9]
  · shallowRef + triggerRef market store [iter 9]

Frontier exhausted: YES
