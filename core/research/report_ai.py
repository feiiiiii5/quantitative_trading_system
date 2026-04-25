import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ReportSummary:
    title: str
    source: str = ""
    date: str = ""
    rating: str = ""
    target_price: float = 0.0
    core_points: List[str] = field(default_factory=list)
    sentiment: str = "neutral"
    sentiment_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "title": self.title, "source": self.source, "date": self.date,
            "rating": self.rating, "target_price": self.target_price,
            "core_points": self.core_points,
            "sentiment": self.sentiment, "sentiment_score": round(self.sentiment_score, 4),
        }


@dataclass
class ReportAggregation:
    symbol: str
    report_count: int = 0
    avg_target_price: float = 0.0
    rating_distribution: Dict[str, int] = field(default_factory=dict)
    sentiment_index: float = 0.0
    reports: List[ReportSummary] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol, "report_count": self.report_count,
            "avg_target_price": round(self.avg_target_price, 2),
            "rating_distribution": self.rating_distribution,
            "sentiment_index": round(self.sentiment_index, 4),
            "reports": [r.to_dict() for r in self.reports[-10:]],
        }


class ReportAIAssistant:
    def __init__(self):
        self._positive_keywords = ["看好", "推荐", "增持", "买入", "超预期", "增长", "突破", "新高", "强势", "领先"]
        self._negative_keywords = ["看淡", "减持", "卖出", "低于预期", "下滑", "风险", "亏损", "下降", "压力", "弱势"]
        self._rating_map = {"强烈推荐": 2, "推荐": 1, "增持": 1, "买入": 1, "中性": 0, "持有": 0, "减持": -1, "卖出": -1}
        self._reports: Dict[str, ReportSummary] = {}
        self._report_counter = 0

    def process_text(self, title: str, content: str, source: str = "") -> dict:
        self._report_counter += 1
        report_id = f"report_{self._report_counter:06d}"
        summary = self.extract_summary(content, title)
        summary.source = source
        summary.date = time.strftime("%Y-%m-%d")
        self._reports[report_id] = summary
        return {"success": True, "report_id": report_id, **summary.to_dict()}

    def list_reports(self, limit: int = 20) -> list:
        items = list(self._reports.items())[-limit:]
        return [{"report_id": rid, **s.to_dict()} for rid, s in reversed(items)]

    def get_summary(self, report_id: str) -> Optional[ReportSummary]:
        return self._reports.get(report_id)

    def get_aggregation(self, symbol: str = "", days: int = 30) -> dict:
        reports = list(self._reports.values())
        agg = self.aggregate_reports(symbol or "unknown", reports)
        return agg.to_dict()

    def get_sentiment_trend(self, days: int = 30) -> list:
        trend = []
        for rid, s in list(self._reports.items())[-days:]:
            trend.append({"date": s.date or "", "score": s.sentiment_score, "label": s.sentiment})
        return trend

    def extract_summary(self, text: str, title: str = "") -> ReportSummary:
        core_points = self._extract_core_points(text)
        rating = self._extract_rating(text)
        target_price = self._extract_target_price(text)
        sentiment, score = self._analyze_sentiment(text)

        return ReportSummary(
            title=title, rating=rating, target_price=target_price,
            core_points=core_points, sentiment=sentiment, sentiment_score=score,
        )

    def _extract_core_points(self, text: str) -> List[str]:
        points = []
        patterns = [
            r"核心观点[：:](.*?)(?:\n|$)",
            r"投资要点[：:](.*?)(?:\n|$)",
            r"主要结论[：:](.*?)(?:\n|$)",
            r"摘要[：:](.*?)(?:\n|$)",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if match.strip():
                    points.append(match.strip()[:200])

        if not points:
            sentences = re.split(r"[。！？\n]", text)
            for s in sentences:
                s = s.strip()
                if len(s) > 10 and any(kw in s for kw in self._positive_keywords + self._negative_keywords):
                    points.append(s[:200])
                if len(points) >= 5:
                    break

        return points[:5]

    def _extract_rating(self, text: str) -> str:
        for rating in ["强烈推荐", "推荐", "增持", "买入", "中性", "持有", "减持", "卖出"]:
            if rating in text:
                return rating
        return "中性"

    def _extract_target_price(self, text: str) -> float:
        patterns = [
            r"目标价[为：:\s]*(\d+\.?\d*)",
            r"目标价格[为：:\s]*(\d+\.?\d*)",
            r"合理估值[为：:\s]*(\d+\.?\d*)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass
        return 0.0

    def _analyze_sentiment(self, text: str) -> tuple:
        score = 0.0
        for kw in self._positive_keywords:
            score += text.count(kw) * 0.1
        for kw in self._negative_keywords:
            score -= text.count(kw) * 0.1

        score = max(-1, min(1, score))
        if score > 0.2:
            return "positive", score
        elif score < -0.2:
            return "negative", score
        return "neutral", score

    def aggregate_reports(self, symbol: str, reports: List[ReportSummary]) -> ReportAggregation:
        if not reports:
            return ReportAggregation(symbol=symbol)

        total_score = 0.0
        rating_dist = {}
        target_prices = []

        for report in reports:
            rating_val = self._rating_map.get(report.rating, 0)
            total_score += rating_val + report.sentiment_score
            rating_dist[report.rating] = rating_dist.get(report.rating, 0) + 1
            if report.target_price > 0:
                target_prices.append(report.target_price)

        avg_target = sum(target_prices) / len(target_prices) if target_prices else 0
        sentiment_index = total_score / len(reports)

        return ReportAggregation(
            symbol=symbol,
            report_count=len(reports),
            avg_target_price=avg_target,
            rating_distribution=rating_dist,
            sentiment_index=sentiment_index,
            reports=reports,
        )

    def process_pdf(self, pdf_path: str) -> Optional[ReportSummary]:
        try:
            import fitz
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            title = os.path.basename(pdf_path).replace(".pdf", "")
            return self.extract_summary(text, title)
        except ImportError:
            logger.warning("PDF processing requires PyMuPDF: pip install PyMuPDF")
            return None
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            return None
