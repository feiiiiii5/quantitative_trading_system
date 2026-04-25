import numpy as np
import pytest


class TestPortfolioModule:
    def test_capital_allocator(self):
        from core.portfolio.capital_allocator import CapitalAllocator
        allocator = CapitalAllocator()
        strategies = [
            {"name": "strat_a", "sharpe": 1.5, "volatility": 0.15, "return_rate": 0.20},
            {"name": "strat_b", "sharpe": 0.8, "volatility": 0.10, "return_rate": 0.08},
        ]
        result = allocator.allocate(strategies, 100000, "sharpe")
        assert result is not None
        assert "allocations" in result

    def test_rebalance_engine(self):
        from core.portfolio.rebalance import RebalanceEngine
        engine = RebalanceEngine()
        positions = {"AAPL": {"value": 60000, "weight": 0.6}, "GOOG": {"value": 40000, "weight": 0.4}}
        targets = {"AAPL": 0.5, "GOOG": 0.5}
        orders = engine.check_threshold_rebalance(positions, targets, threshold=0.05)
        assert isinstance(orders, list)

    def test_attribution(self):
        from core.portfolio.attribution import PerformanceAttribution
        attr = PerformanceAttribution()
        pr = {"AAPL": 0.01, "GOOG": 0.005}
        br = {"AAPL": 0.008, "GOOG": 0.006}
        pw = {"AAPL": 0.6, "GOOG": 0.4}
        bw = {"AAPL": 0.5, "GOOG": 0.5}
        result = attr.daily_attribution(pr, br, pw, bw)
        assert result is not None
        assert hasattr(result, "to_dict")

    def test_derivatives_manager(self):
        from core.portfolio.derivatives import DerivativesManager, FuturesPosition
        mgr = DerivativesManager()
        pos = FuturesPosition(symbol="IF2401", contract="202401", quantity=1, entry_price=3800.0, multiplier=300, margin_rate=0.1)
        mgr.add_future(pos)
        assert "IF2401" in mgr.get_all_positions()["futures"]
        result = mgr.calculate_hedge_ratio(0.0)
        assert isinstance(result, dict)
        assert "current_delta" in result

    def test_tearsheet_generator(self):
        from core.portfolio.tearsheet import TearsheetGenerator
        gen = TearsheetGenerator()
        ec = (np.cumsum(np.random.randn(252) * 0.01) + 100).tolist()
        result = gen.generate(ec)
        assert result is not None
        assert hasattr(result, "to_dict")


class TestMonitorModule:
    def test_heartbeat_monitor(self):
        from core.monitor.heartbeat import StrategyHeartbeatMonitor
        monitor = StrategyHeartbeatMonitor()
        monitor.register("test_strat", 30)
        result = monitor.report("test_strat")
        assert result.get("success", False)
        status = monitor.get_status("test_strat")
        assert status is not None

    def test_alert_system(self):
        from core.monitor.alert_system import SmartAlertSystem, AlertLevel, AlertChannel
        system = SmartAlertSystem()
        alert = system.send_alert(
            "测试告警", "这是一条测试告警",
            AlertLevel.WARNING, "test",
            [AlertChannel.EMAIL],
        )
        assert alert is not None
        assert hasattr(alert, "to_dict")

    def test_anomaly_detector(self):
        from core.monitor.anomaly_detect import AnomalyDetector
        detector = AnomalyDetector()
        for i in range(25):
            detector.check_volume_anomaly("TEST", 1000.0 + np.random.randn() * 100)
        event = detector.check_volume_anomaly("TEST", 5000.0)
        stats = detector.get_anomaly_stats()
        assert "total_anomalies" in stats

    def test_perf_dashboard(self):
        from core.monitor.perf_dashboard import PerformanceDashboard
        dashboard = PerformanceDashboard()
        dashboard.record_api_latency("/api/test", 50.0, 200)
        dashboard.record_api_latency("/api/test", 100.0, 200)
        stats = dashboard.get_api_latency_stats()
        assert isinstance(stats, dict)

    def test_audit_log(self):
        from core.monitor.audit_log import ComplianceAuditLog
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            log = ComplianceAuditLog(base_dir=tmpdir)
            log.log_signal("strat_a", "AAPL", "buy", 0.8)
            log.log_order("executor", "AAPL", "buy", 100, 150.0)
            entries = log.query(event_type="signal")
            assert len(entries) >= 1


class TestResearchModule:
    def test_fundamental_factor_library(self):
        from core.research.fundamental import FundamentalFactorLibrary
        lib = FundamentalFactorLibrary()
        data = {"price": 100.0, "eps": 5.0, "book_value_per_share": 20.0,
                "revenue_per_share": 30.0, "enterprise_value": 1000000, "ebitda": 200000,
                "revenue_growth": 0.2, "profit_growth": 0.25, "roe": 0.15,
                "roa": 0.08, "net_margin": 0.12, "debt_ratio": 0.4,
                "current_ratio": 1.5, "quick_ratio": 1.2, "interest_coverage": 8.0}
        result = lib.calculate_all_factors(data)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_sector_research(self):
        from core.research.sector import SectorResearch
        research = SectorResearch()
        chain = research.analyze_industry_chain("")
        assert isinstance(chain, dict)


class TestAIModule:
    def test_adaptive_param_optimizer(self):
        from core.ai.adaptive_params import AdaptiveParamOptimizer
        optimizer = AdaptiveParamOptimizer()
        returns = np.random.randn(100) * 0.02
        regime = optimizer.detect_regime(returns)
        assert regime is not None
        assert hasattr(regime, "to_dict")

    def test_nl_strategy_generator(self):
        from core.ai.nl_strategy import NLStrategyGenerator
        gen = NLStrategyGenerator()
        result = gen.generate("当MACD金叉时买入，死叉时卖出")
        assert result is not None
        assert "success" in result

    def test_pattern_detector(self):
        from core.ai.pattern_detect import AnomalyPatternDetector
        detector = AnomalyPatternDetector()
        prices = np.random.randn(50).cumsum() + 100
        volumes = np.random.randn(50) * 1000 + 5000
        results = detector.detect(prices, volumes)
        assert isinstance(results, list)

    def test_portfolio_ai_advisor(self):
        from core.ai.portfolio_ai import PortfolioAIAdvisor
        advisor = PortfolioAIAdvisor()
        positions = {"AAPL": {"value": 60000}, "GOOG": {"value": 40000}}
        returns_data = {"AAPL": np.random.randn(100) * 0.02, "GOOG": np.random.randn(100) * 0.015}
        suggestions = advisor.suggest_rebalance(positions, returns_data)
        assert isinstance(suggestions, list)

    def test_prediction_model_platform(self):
        from core.ai.prediction_models import PredictionModelPlatform
        platform = PredictionModelPlatform()
        models = platform.get_available_models()
        assert isinstance(models, list)


class TestPlatformModule:
    def test_microservice_manager(self):
        from core.platform.microservice import MicroserviceManager, ServiceStatus
        mgr = MicroserviceManager()
        status = mgr.get_status()
        assert status["code"] == 0
        topology = mgr.get_topology()
        assert topology["code"] == 0

    def test_task_scheduler(self):
        from core.platform.scheduler import TaskScheduler
        scheduler = TaskScheduler()
        task_id = scheduler.add_task(name="test_task", interval_seconds=60)
        assert task_id is not None
        tasks = scheduler.list_tasks()
        assert len(tasks) > 0

    def test_environment_manager(self):
        from core.platform.env_manager import EnvironmentManager
        mgr = EnvironmentManager()
        envs = mgr.list_envs()
        assert isinstance(envs, list)

    def test_auth_security_manager(self):
        from core.platform.auth_security import AuthSecurityManager
        mgr = AuthSecurityManager()
        result = mgr.create_user("test_user", "strategist")
        assert result is not None
        assert "api_key" in result
        user = mgr.authenticate(result["api_key"])
        assert user is not None
        assert user.username == "test_user"
        has_perm = mgr.check_permission("test_user", "read")
        assert has_perm
        new_key = mgr.rotate_api_key("test_user")
        assert new_key is not None

    def test_workspace_manager(self):
        from core.platform.workspace import WorkspaceManager
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            import core.platform.workspace as ws_mod
            orig_dir = ws_mod._WORKSPACE_DIR
            ws_mod._WORKSPACE_DIR = tmpdir
            mgr = WorkspaceManager()
            presets = mgr.get_presets()
            assert presets["code"] == 0
            result = mgr.create_layout("测试工作台", "research")
            assert result["code"] == 0
            shortcuts = mgr.get_shortcuts()
            assert shortcuts["code"] == 0
            ws_mod._WORKSPACE_DIR = orig_dir


class TestAPIRoutes:
    def test_portfolio_routes_import(self):
        from api.portfolio_routes import router
        assert router is not None

    def test_monitor_routes_import(self):
        from api.monitor_routes import router
        assert router is not None

    def test_research_routes_import(self):
        from api.research_routes import router
        assert router is not None

    def test_ai_routes_import(self):
        from api.ai_routes import router
        assert router is not None

    def test_platform_routes_import(self):
        from api.platform_routes import router
        assert router is not None
