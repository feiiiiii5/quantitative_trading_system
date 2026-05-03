from core.news_engine import _analyze_sentiment, _extract_symbols, get_news_engine


class TestAnalyzeSentiment:
    def test_empty_text(self):
        score, label = _analyze_sentiment("")
        assert score == 0.0
        assert label == "neutral"

    def test_positive_text(self):
        score, label = _analyze_sentiment("公司业绩大增，股价大涨突破新高")
        assert score > 0
        assert label in ("bullish", "slightly_bullish")

    def test_negative_text(self):
        score, label = _analyze_sentiment("公司业绩下滑，股价暴跌闪崩")
        assert score < 0
        assert label in ("bearish", "slightly_bearish")

    def test_neutral_text(self):
        score, label = _analyze_sentiment("今日天气晴朗，适合出行")
        assert score == 0.0
        assert label == "neutral"

    def test_mixed_text(self):
        score, label = _analyze_sentiment("业绩增长但风险加大")
        assert -0.3 <= score <= 0.3

    def test_score_bounded(self):
        score, _ = _analyze_sentiment("大涨 暴涨 飙升 新高 突破 利好 盈利 增长 增持 回购")
        assert -1.0 <= score <= 1.0


class TestExtractSymbols:
    def test_parenthesized_code(self):
        symbols = _extract_symbols("贵州茅台(600519)今日大涨")
        assert "600519" in symbols

    def test_fullwidth_parenthesized(self):
        symbols = _extract_symbols("贵州茅台（600519）今日大涨")
        assert "600519" in symbols

    def test_no_symbols(self):
        symbols = _extract_symbols("今日市场整体表现平稳")
        assert symbols == []

    def test_max_five_symbols(self):
        text = " ".join(f"股票({str(i).zfill(6)})" for i in range(10))
        symbols = _extract_symbols(text)
        assert len(symbols) <= 5


class TestGetNewsEngine:
    def test_singleton(self):
        e1 = get_news_engine()
        e2 = get_news_engine()
        assert e1 is e2
