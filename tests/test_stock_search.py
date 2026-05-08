"""
stock_search 模块单元测试
覆盖倒排索引构建、股票搜索、信息查询、行业列表、拼音首字母等核心功能
"""
from unittest.mock import MagicMock, patch

import pytest

import core.stock_search as mod


@pytest.fixture(autouse=True)
def reset_module_state():
    """每个测试前重置模块级全局状态，确保测试隔离"""
    mod._index_built = False
    mod._all_stocks = {}
    mod._code_index = {}
    mod._name_index = {}
    mod._pinyin_index = {}
    mod._PINYIN_MAP = None
    yield
    mod._index_built = False
    mod._all_stocks = {}
    mod._code_index = {}
    mod._name_index = {}
    mod._pinyin_index = {}
    mod._PINYIN_MAP = None


@pytest.fixture
def build_index_no_external():
    """构建索引，mock 掉外部数据源，仅使用 _STOCK_INDEX 硬编码数据"""
    with patch("core.stock_search._build_inverted_index", wraps=mod._build_inverted_index) as _, \
         patch.dict("sys.modules", {
             "core.market_data": MagicMock(
                 _all_a_stocks_cache=[],
                 get_stock_list=MagicMock(return_value=[]),
                 fetch_all_a_stocks_async=MagicMock(),
             ),
         }), patch.dict("sys.modules", {
        "core.database": MagicMock(
                get_db=MagicMock(return_value=MagicMock(
                    fetchall=MagicMock(return_value=[])
                )),
            ),
        }):
            mod._build_inverted_index()
            yield


class TestBuildInvertedIndex:
    """测试倒排索引构建"""

    def test_build_populates_all_stocks(self, build_index_no_external):
        assert len(mod._all_stocks) > 0

    def test_build_contains_hardcoded_stocks(self, build_index_no_external):
        codes = [s["code"] for s in mod._all_stocks.values()]
        assert "600519" in codes
        assert "AAPL" in codes
        assert "00700" in codes

    def test_build_sets_index_built_flag(self, build_index_no_external):
        assert mod._index_built is True

    def test_build_populates_code_index(self, build_index_no_external):
        assert len(mod._code_index) > 0
        assert "6" in mod._code_index

    def test_build_populates_name_index(self, build_index_no_external):
        assert len(mod._name_index) > 0
        assert "茅" in mod._name_index


class TestSearchStocks:
    """测试 search_stocks 搜索功能"""

    def test_search_by_code_prefix(self, build_index_no_external):
        results = mod.search_stocks("600519")
        assert len(results) > 0
        names = [r["name"] for r in results]
        assert "贵州茅台" in names

    def test_search_by_name_substring(self, build_index_no_external):
        results = mod.search_stocks("茅台")
        assert len(results) > 0
        names = [r["name"] for r in results]
        assert "贵州茅台" in names

    def test_search_empty_query_returns_empty(self, build_index_no_external):
        assert mod.search_stocks("") == []
        assert mod.search_stocks("   ") == []

    def test_search_limit_parameter(self, build_index_no_external):
        results = mod.search_stocks("中国", limit=2)
        assert len(results) <= 2

    def test_search_market_filter(self, build_index_no_external):
        results = mod.search_stocks("平安", market="A")
        assert all(r["market"] == "A" for r in results)
        results_hk = mod.search_stocks("平安", market="HK")
        assert all(r["market"] == "HK" for r in results_hk)

    def test_search_result_keys(self, build_index_no_external):
        results = mod.search_stocks("600519")
        assert len(results) > 0
        expected_keys = {"symbol", "code", "name", "market", "sector", "priority"}
        assert set(results[0].keys()) == expected_keys

    def test_search_us_stock_by_code(self, build_index_no_external):
        results = mod.search_stocks("AAPL")
        assert len(results) > 0
        names = [r["name"] for r in results]
        assert "苹果" in names


class TestGetStockInfo:
    """测试 get_stock_info"""

    def test_valid_symbol_returns_info(self, build_index_no_external):
        info = mod.get_stock_info("600519")
        assert info is not None
        assert info["name"] == "贵州茅台"
        assert info["market"] == "A"
        assert info["sector"] == "白酒"

    def test_valid_us_symbol(self, build_index_no_external):
        info = mod.get_stock_info("AAPL")
        assert info is not None
        assert info["name"] == "苹果"
        assert info["market"] == "US"

    def test_invalid_symbol_returns_none(self, build_index_no_external):
        assert mod.get_stock_info("NOTEXIST") is None


class TestGetStockName:
    """测试 get_stock_name"""

    def test_valid_symbol_returns_name(self, build_index_no_external):
        assert mod.get_stock_name("600519") == "贵州茅台"

    def test_invalid_symbol_returns_none(self, build_index_no_external):
        assert mod.get_stock_name("NOTEXIST") is None


class TestGetAllIndustries:
    """测试 get_all_industries"""

    def test_returns_sorted_list(self, build_index_no_external):
        industries = mod.get_all_industries()
        assert industries == sorted(industries)

    def test_contains_expected_entries(self, build_index_no_external):
        industries = mod.get_all_industries()
        assert "白酒" in industries
        assert "银行" in industries
        assert "科技" in industries

    def test_no_empty_strings(self, build_index_no_external):
        industries = mod.get_all_industries()
        assert "" not in industries


class TestGetPinyinInitial:
    """测试 _get_pinyin_initial"""

    def test_ascii_letters_pass_through(self):
        mod._PINYIN_MAP = {}
        assert mod._get_pinyin_initial("AAPL") == "aapl"

    def test_mixed_ascii_and_chinese_without_map(self):
        mod._PINYIN_MAP = {}
        result = mod._get_pinyin_initial("腾讯ABC")
        assert result == "abc"

    def test_empty_string(self):
        mod._PINYIN_MAP = {}
        assert mod._get_pinyin_initial("") == ""
