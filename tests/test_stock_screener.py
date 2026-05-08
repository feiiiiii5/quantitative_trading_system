"""
stock_screener 模块单元测试
覆盖 FilterOperator 枚举、_apply_condition 函数、StockScreener 类核心方法
不测试异步增强方法（需要网络）
"""
import pytest

from core.stock_screener import (
    FilterCondition,
    FilterOperator,
    ScreeningPreset,
    StockScreener,
    _apply_condition,
    get_stock_screener,
)

# ============================================================
# 测试夹具：构造模拟股票数据
# ============================================================

@pytest.fixture
def sample_stocks():
    """构造一批模拟股票数据，覆盖多种字段取值"""
    return [
        {
            "symbol": "600519",
            "name": "贵州茅台",
            "change_pct": 5.2,
            "volume_ratio": 2.1,
            "turnover_rate": 4.5,
            "pe": 12.0,
            "pb": 1.2,
            "roe": 18.5,
            "total_market_cap": 800e8,
            "dividend_yield": 5.0,
            "revenue_yoy": 25.0,
            "pct_5d": 8.0,
            "pct_20d": -10.0,
            "high_60d_ratio": 0.95,
        },
        {
            "symbol": "000001",
            "name": "平安银行",
            "change_pct": -2.3,
            "volume_ratio": 0.8,
            "turnover_rate": 1.2,
            "pe": 6.5,
            "pb": 0.6,
            "roe": 10.0,
            "total_market_cap": 300e8,
            "dividend_yield": 3.0,
            "revenue_yoy": 5.0,
            "pct_5d": -3.0,
            "pct_20d": -20.0,
            "high_60d_ratio": 0.75,
        },
        {
            "symbol": "300750",
            "name": "宁德时代",
            "change_pct": 10.0,
            "volume_ratio": 3.0,
            "turnover_rate": 8.0,
            "pe": 50.0,
            "pb": 5.0,
            "roe": 12.0,
            "total_market_cap": 1200e8,
            "dividend_yield": 0.5,
            "revenue_yoy": 40.0,
            "pct_5d": 12.0,
            "pct_20d": 5.0,
            "high_60d_ratio": 1.0,
        },
    ]


@pytest.fixture
def screener():
    """创建 StockScreener 实例"""
    return StockScreener()


# ============================================================
# TestFilterCondition：测试 _apply_condition 各运算符
# ============================================================

class TestFilterCondition:
    """测试 _apply_condition 函数对每种运算符的处理"""

    # ---- GT 大于 ----
    def test_gt_true(self):
        cond = FilterCondition("change_pct", FilterOperator.GT, 5.0)
        assert _apply_condition({"change_pct": 5.2}, cond) is True

    def test_gt_false(self):
        cond = FilterCondition("change_pct", FilterOperator.GT, 5.0)
        assert _apply_condition({"change_pct": 4.9}, cond) is False

    def test_gt_equal_returns_false(self):
        """GT 严格大于，等于时应返回 False"""
        cond = FilterCondition("change_pct", FilterOperator.GT, 5.0)
        assert _apply_condition({"change_pct": 5.0}, cond) is False

    # ---- GTE 大于等于 ----
    def test_gte_true_equal(self):
        cond = FilterCondition("change_pct", FilterOperator.GTE, 5.0)
        assert _apply_condition({"change_pct": 5.0}, cond) is True

    def test_gte_true_greater(self):
        cond = FilterCondition("change_pct", FilterOperator.GTE, 5.0)
        assert _apply_condition({"change_pct": 6.0}, cond) is True

    def test_gte_false(self):
        cond = FilterCondition("change_pct", FilterOperator.GTE, 5.0)
        assert _apply_condition({"change_pct": 4.9}, cond) is False

    # ---- LT 小于 ----
    def test_lt_true(self):
        cond = FilterCondition("pe", FilterOperator.LT, 15.0)
        assert _apply_condition({"pe": 12.0}, cond) is True

    def test_lt_false(self):
        cond = FilterCondition("pe", FilterOperator.LT, 15.0)
        assert _apply_condition({"pe": 16.0}, cond) is False

    # ---- LTE 小于等于 ----
    def test_lte_true_equal(self):
        cond = FilterCondition("pe", FilterOperator.LTE, 15.0)
        assert _apply_condition({"pe": 15.0}, cond) is True

    def test_lte_false(self):
        cond = FilterCondition("pe", FilterOperator.LTE, 15.0)
        assert _apply_condition({"pe": 15.1}, cond) is False

    # ---- EQ 等于（浮点容差） ----
    def test_eq_true(self):
        cond = FilterCondition("pe", FilterOperator.EQ, 12.0)
        assert _apply_condition({"pe": 12.0}, cond) is True

    def test_eq_false(self):
        cond = FilterCondition("pe", FilterOperator.EQ, 12.0)
        assert _apply_condition({"pe": 12.1}, cond) is False

    # ---- BETWEEN 区间 ----
    def test_between_true(self):
        cond = FilterCondition("pe", FilterOperator.BETWEEN, [0, 15])
        assert _apply_condition({"pe": 12.0}, cond) is True

    def test_between_boundary(self):
        """BETWEEN 包含左右边界"""
        cond = FilterCondition("pe", FilterOperator.BETWEEN, [0, 15])
        assert _apply_condition({"pe": 0}, cond) is True
        assert _apply_condition({"pe": 15}, cond) is True

    def test_between_false(self):
        cond = FilterCondition("pe", FilterOperator.BETWEEN, [0, 15])
        assert _apply_condition({"pe": 16.0}, cond) is False

    # ---- IN 集合 ----
    def test_in_true(self):
        cond = FilterCondition("pe", FilterOperator.IN, [12.0, 6.5, 50.0])
        assert _apply_condition({"pe": 12.0}, cond) is True

    def test_in_false(self):
        cond = FilterCondition("pe", FilterOperator.IN, [6.5, 50.0])
        assert _apply_condition({"pe": 12.0}, cond) is False

    # ---- 边界情况：字段值为 None ----
    def test_none_field_returns_false(self):
        """字段不存在或值为 None 时，应返回 False"""
        cond = FilterCondition("missing_field", FilterOperator.GT, 0)
        assert _apply_condition({}, cond) is False
        assert _apply_condition({"missing_field": None}, cond) is False

    # ---- 边界情况：非数值字段 ----
    def test_non_numeric_value_returns_false(self):
        """非数值字段且非 IN 运算符时，应返回 False"""
        cond = FilterCondition("name", FilterOperator.GT, 0)
        assert _apply_condition({"name": "贵州茅台"}, cond) is False

    # ---- IN 运算符配合字符串值 ----
    def test_in_with_string_value(self):
        """IN 运算符支持字符串匹配"""
        cond = FilterCondition("name", FilterOperator.IN, ["贵州茅台", "宁德时代"])
        assert _apply_condition({"name": "贵州茅台"}, cond) is True
        assert _apply_condition({"name": "平安银行"}, cond) is False

    def test_in_with_string_non_list_value(self):
        """IN 运算符配合字符串（非列表）时做等值比较"""
        cond = FilterCondition("name", FilterOperator.IN, "贵州茅台")
        assert _apply_condition({"name": "贵州茅台"}, cond) is True
        assert _apply_condition({"name": "平安银行"}, cond) is False

    # ---- BETWEEN 长度不为2时返回 False ----
    def test_between_invalid_length(self):
        cond = FilterCondition("pe", FilterOperator.BETWEEN, [10])
        assert _apply_condition({"pe": 12.0}, cond) is False


# ============================================================
# TestStockScreener：测试 StockScreener 类各方法
# ============================================================

class TestStockScreener:

    # ---- list_presets ----
    def test_list_presets_count(self, screener):
        """预设策略应返回 8 个"""
        presets = screener.list_presets()
        assert len(presets) == 8

    def test_list_presets_structure(self, screener):
        """每个预设应包含 id/name/description/category/conditions 字段"""
        presets = screener.list_presets()
        for p in presets:
            assert "id" in p
            assert "name" in p
            assert "description" in p
            assert "category" in p
            assert "conditions" in p
            assert isinstance(p["conditions"], list)
            # 每个 condition 应包含 field/operator/value/label
            for c in p["conditions"]:
                assert "field" in c
                assert "operator" in c
                assert "value" in c
                assert "label" in c

    # ---- get_preset ----
    def test_get_preset_valid(self, screener):
        """获取存在的预设应返回 ScreeningPreset 对象"""
        preset = screener.get_preset("breakout_high")
        assert preset is not None
        assert isinstance(preset, ScreeningPreset)
        assert preset.id == "breakout_high"
        assert preset.name == "突破新高"

    def test_get_preset_invalid(self, screener):
        """获取不存在的预设应返回 None"""
        assert screener.get_preset("nonexistent") is None

    # ---- screen_by_preset ----
    def test_screen_by_preset_valid(self, screener, sample_stocks):
        """使用有效预设筛选，应返回符合条件的股票"""
        # limit_up_pool 条件：change_pct >= 9.5，只有宁德时代满足
        result = screener.screen_by_preset(sample_stocks, "limit_up_pool")
        assert len(result) == 1
        assert result[0]["symbol"] == "300750"

    def test_screen_by_preset_invalid(self, screener, sample_stocks):
        """使用无效预设 ID 应返回空列表"""
        result = screener.screen_by_preset(sample_stocks, "nonexistent")
        assert result == []

    # ---- screen_by_conditions ----
    def test_screen_by_conditions_custom(self, screener, sample_stocks):
        """自定义条件筛选：PE 在 0-15 之间"""
        conditions = [
            {"field": "pe", "operator": "between", "value": [0, 15], "label": "低PE"},
        ]
        result = screener.screen_by_conditions(sample_stocks, conditions)
        # 贵州茅台(12.0) 和 平安银行(6.5) 满足
        assert len(result) == 2
        symbols = {s["symbol"] for s in result}
        assert "600519" in symbols
        assert "000001" in symbols

    def test_screen_by_conditions_invalid_operator_skipped(self, screener, sample_stocks):
        """无效运算符的条件应被跳过，不影响其他有效条件"""
        conditions = [
            {"field": "change_pct", "operator": "invalid_op", "value": 0, "label": ""},
            {"field": "change_pct", "operator": "gt", "value": 0, "label": "上涨"},
        ]
        result = screener.screen_by_conditions(sample_stocks, conditions)
        # 只有无效运算符被跳过，GT 条件仍生效
        # 贵州茅台(5.2) 和 宁德时代(10.0) 满足 change_pct > 0
        assert len(result) == 2

    def test_screen_by_conditions_missing_field_skipped(self, screener, sample_stocks):
        """缺少 field 的条件应被跳过"""
        conditions = [
            {"operator": "gt", "value": 0, "label": ""},
        ]
        result = screener.screen_by_conditions(sample_stocks, conditions)
        # 条件解析失败，parsed 为空，_screen 返回前 100 条
        assert len(result) == 3

    # ---- _screen ----
    def test_screen_empty_conditions_returns_first_100(self, screener):
        """空条件时返回前 100 条股票"""
        # 构造 150 只股票
        stocks = [{"symbol": f"test_{i}", "change_pct": float(i)} for i in range(150)]
        result = screener._screen(stocks, [])
        assert len(result) == 100

    def test_screen_matching_stocks(self, screener, sample_stocks):
        """筛选满足所有条件的股票"""
        conditions = [
            FilterCondition("change_pct", FilterOperator.GT, 0),
            FilterCondition("volume_ratio", FilterOperator.GT, 1.5),
        ]
        result = screener._screen(sample_stocks, conditions)
        # 贵州茅台(5.2, 2.1) 和 宁德时代(10.0, 3.0) 满足
        assert len(result) == 2

    def test_screen_no_match(self, screener, sample_stocks):
        """条件过于严格，无股票满足时返回空列表"""
        conditions = [
            FilterCondition("change_pct", FilterOperator.GT, 100),
        ]
        result = screener._screen(sample_stocks, conditions)
        assert result == []

    # ---- _screen_raw_only ----
    def test_screen_raw_only_filters_enriched_fields(self, screener, sample_stocks):
        """_screen_raw_only 应跳过需要增强的字段条件"""
        conditions = [
            FilterCondition("change_pct", FilterOperator.GT, 0),  # 非增强字段
            FilterCondition("pct_5d", FilterOperator.GT, 5),      # 增强字段，应被跳过
        ]
        result = screener._screen_raw_only(sample_stocks, conditions)
        # 只应用 change_pct > 0：贵州茅台(5.2) 和 宁德时代(10.0)
        assert len(result) == 2

    def test_screen_raw_only_empty_conditions(self, screener):
        """空条件时返回前 500 条"""
        stocks = [{"symbol": f"test_{i}"} for i in range(600)]
        result = screener._screen_raw_only(stocks, [])
        assert len(result) == 500

    def test_screen_raw_only_all_enriched_conditions(self, screener, sample_stocks):
        """所有条件都是增强字段时，应返回前 500 条（无 raw 条件可应用）"""
        conditions = [
            FilterCondition("pct_5d", FilterOperator.GT, 5),
            FilterCondition("roe", FilterOperator.GT, 15),
        ]
        result = screener._screen_raw_only(sample_stocks, conditions)
        # raw_conditions 为空，返回 stocks[:500]
        assert len(result) == 3


# ============================================================
# TestSingleton：测试 get_stock_screener 单例
# ============================================================

class TestSingleton:
    def test_singleton_returns_same_instance(self):
        """多次调用应返回同一实例"""
        s1 = get_stock_screener()
        s2 = get_stock_screener()
        assert s1 is s2
        assert isinstance(s1, StockScreener)
