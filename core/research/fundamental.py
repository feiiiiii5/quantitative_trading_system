import logging
from dataclasses import dataclass
from typing import Dict, List


logger = logging.getLogger(__name__)


@dataclass
class FundamentalFactor:
    name: str
    category: str
    value: float = 0.0
    industry_median: float = 0.0
    percentile: float = 0.0
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name, "category": self.category,
            "value": round(self.value, 4) if isinstance(self.value, float) else self.value,
            "industry_median": round(self.industry_median, 4),
            "percentile": round(self.percentile, 2),
            "description": self.description,
        }


class FundamentalFactorLibrary:
    def __init__(self):
        self._factors: Dict[str, List[FundamentalFactor]] = {}

    def calculate_valuation_factors(self, data: dict) -> List[FundamentalFactor]:
        factors = []
        price = data.get("price", 0)
        eps = data.get("eps", 0)
        bvps = data.get("book_value_per_share", 0)
        revenue_ps = data.get("revenue_per_share", 0)
        ev = data.get("enterprise_value", 0)
        ebitda = data.get("ebitda", 0)

        if eps > 0 and price > 0:
            factors.append(FundamentalFactor("PE", "估值", price / eps, description="市盈率"))
        if bvps > 0 and price > 0:
            factors.append(FundamentalFactor("PB", "估值", price / bvps, description="市净率"))
        if revenue_ps > 0 and price > 0:
            factors.append(FundamentalFactor("PS", "估值", price / revenue_ps, description="市销率"))
        if ebitda > 0 and ev > 0:
            factors.append(FundamentalFactor("EV_EBITDA", "估值", ev / ebitda, description="EV/EBITDA"))

        return factors

    def calculate_growth_factors(self, data: dict) -> List[FundamentalFactor]:
        factors = []
        rev_growth = data.get("revenue_growth", 0)
        profit_growth = data.get("profit_growth", 0)
        roe = data.get("roe", 0)
        roa = data.get("roa", 0)
        net_margin = data.get("net_margin", 0)

        if rev_growth:
            factors.append(FundamentalFactor("Revenue_Growth", "成长", rev_growth, description="营收增速"))
        if profit_growth:
            factors.append(FundamentalFactor("Profit_Growth", "成长", profit_growth, description="利润增速"))
        if roe:
            factors.append(FundamentalFactor("ROE", "成长", roe, description="净资产收益率"))
        if roa:
            factors.append(FundamentalFactor("ROA", "成长", roa, description="总资产收益率"))
        if net_margin:
            factors.append(FundamentalFactor("Net_Margin", "成长", net_margin, description="净利润率"))

        return factors

    def calculate_financial_health_factors(self, data: dict) -> List[FundamentalFactor]:
        factors = []
        debt_ratio = data.get("debt_ratio", 0)
        current_ratio = data.get("current_ratio", 0)
        quick_ratio = data.get("quick_ratio", 0)
        interest_coverage = data.get("interest_coverage", 0)

        if debt_ratio:
            factors.append(FundamentalFactor("Debt_Ratio", "财务健康", debt_ratio, description="资产负债率"))
        if current_ratio:
            factors.append(FundamentalFactor("Current_Ratio", "财务健康", current_ratio, description="流动比率"))
        if quick_ratio:
            factors.append(FundamentalFactor("Quick_Ratio", "财务健康", quick_ratio, description="速动比率"))
        if interest_coverage:
            factors.append(FundamentalFactor("Interest_Coverage", "财务健康", interest_coverage, description="利息保障倍数"))

        return factors

    def calculate_all_factors(self, data: dict) -> List[dict]:
        symbol = data.get("symbol", "unknown")
        all_factors = []
        all_factors.extend(self.calculate_valuation_factors(data))
        all_factors.extend(self.calculate_growth_factors(data))
        all_factors.extend(self.calculate_financial_health_factors(data))
        self._factors[symbol] = all_factors
        return [f.to_dict() for f in all_factors]

    def get_factors(self, symbol: str) -> List[dict]:
        factors = self._factors.get(symbol, [])
        return [f.to_dict() for f in factors]

    def get_factor_categories(self) -> List[str]:
        return ["估值", "成长", "财务健康"]

    def compare_with_industry(
        self, factor_name: str, factor_value: float,
        industry: str, industry_data: dict,
    ) -> dict:
        industry_median = industry_data.get(factor_name, 0)
        if industry_median > 0 and factor_value > 0:
            percentile = (factor_value / industry_median - 1) * 100
        else:
            percentile = 0

        return {
            "factor_name": factor_name,
            "factor_value": round(factor_value, 4),
            "industry": industry,
            "industry_median": round(industry_median, 4),
            "percentile": round(percentile, 2),
            "relative_position": "above" if factor_value > industry_median else "below" if factor_value < industry_median else "equal",
        }
