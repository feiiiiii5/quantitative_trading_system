
from core.sector_rotation import (
    SectorRotationAnalyzer,
    SectorStrength,
    get_sector_rotation_analyzer,
)


class TestDetectRotationSignal:
    def test_empty_current_returns_empty(self):
        analyzer = SectorRotationAnalyzer()
        result = analyzer.detect_rotation_signal([])
        assert result == []

    def test_no_previous_and_no_history_returns_empty(self):
        analyzer = SectorRotationAnalyzer()
        current = [
            {"name": "半导体", "change_pct": 3.5},
            {"name": "新能源", "change_pct": 2.8},
            {"name": "医药", "change_pct": 2.1},
            {"name": "消费", "change_pct": 1.5},
            {"name": "金融", "change_pct": 1.0},
        ]
        result = analyzer.detect_rotation_signal(current)
        assert result == []

    def test_new_sector_entering_top5(self):
        analyzer = SectorRotationAnalyzer()
        previous = [
            {"name": "半导体", "change_pct": 3.5},
            {"name": "新能源", "change_pct": 2.8},
            {"name": "医药", "change_pct": 2.1},
            {"name": "消费", "change_pct": 1.5},
            {"name": "金融", "change_pct": 1.0},
        ]
        current = [
            {"name": "半导体", "change_pct": 4.0},
            {"name": "新能源", "change_pct": 3.0},
            {"name": "医药", "change_pct": 2.5},
            {"name": "消费", "change_pct": 2.0},
            {"name": "军工", "change_pct": 1.8},
        ]
        result = analyzer.detect_rotation_signal(current, previous)
        entering = [s for s in result if s["type"] == "sector_entering_top"]
        assert len(entering) == 1
        assert entering[0]["sector"] == "军工"
        assert entering[0]["change_pct"] == 1.8

    def test_sector_leaving_top5(self):
        analyzer = SectorRotationAnalyzer()
        previous = [
            {"name": "半导体", "change_pct": 3.5},
            {"name": "新能源", "change_pct": 2.8},
            {"name": "医药", "change_pct": 2.1},
            {"name": "消费", "change_pct": 1.5},
            {"name": "金融", "change_pct": 1.0},
        ]
        current = [
            {"name": "半导体", "change_pct": 4.0},
            {"name": "新能源", "change_pct": 3.0},
            {"name": "医药", "change_pct": 2.5},
            {"name": "消费", "change_pct": 2.0},
            {"name": "军工", "change_pct": 1.8},
        ]
        result = analyzer.detect_rotation_signal(current, previous)
        leaving = [s for s in result if s["type"] == "sector_leaving_top"]
        assert len(leaving) == 1
        assert leaving[0]["sector"] == "金融"

    def test_both_entering_and_leaving(self):
        analyzer = SectorRotationAnalyzer()
        previous = [
            {"name": "半导体", "change_pct": 3.5},
            {"name": "新能源", "change_pct": 2.8},
            {"name": "医药", "change_pct": 2.1},
            {"name": "消费", "change_pct": 1.5},
            {"name": "金融", "change_pct": 1.0},
        ]
        current = [
            {"name": "半导体", "change_pct": 4.0},
            {"name": "新能源", "change_pct": 3.0},
            {"name": "军工", "change_pct": 2.5},
            {"name": "地产", "change_pct": 2.0},
            {"name": "钢铁", "change_pct": 1.8},
        ]
        result = analyzer.detect_rotation_signal(current, previous)
        entering = [s for s in result if s["type"] == "sector_entering_top"]
        leaving = [s for s in result if s["type"] == "sector_leaving_top"]
        assert len(entering) == 3
        assert len(leaving) == 3
        entering_names = {s["sector"] for s in entering}
        leaving_names = {s["sector"] for s in leaving}
        assert entering_names == {"军工", "地产", "钢铁"}
        assert leaving_names == {"医药", "消费", "金融"}

    def test_no_change_returns_empty(self):
        analyzer = SectorRotationAnalyzer()
        sectors = [
            {"name": "半导体", "change_pct": 3.5},
            {"name": "新能源", "change_pct": 2.8},
            {"name": "医药", "change_pct": 2.1},
            {"name": "消费", "change_pct": 1.5},
            {"name": "金融", "change_pct": 1.0},
        ]
        result = analyzer.detect_rotation_signal(sectors, sectors)
        assert result == []

    def test_with_explicit_previous_parameter(self):
        analyzer = SectorRotationAnalyzer()
        previous = [
            {"name": "新能源", "change_pct": 3.0},
            {"name": "医药", "change_pct": 2.5},
            {"name": "消费", "change_pct": 2.0},
            {"name": "金融", "change_pct": 1.5},
            {"name": "地产", "change_pct": 1.0},
        ]
        current = [
            {"name": "半导体", "change_pct": 5.0},
            {"name": "新能源", "change_pct": 3.0},
            {"name": "医药", "change_pct": 2.5},
            {"name": "消费", "change_pct": 2.0},
            {"name": "军工", "change_pct": 1.8},
        ]
        result = analyzer.detect_rotation_signal(current, previous)
        entering = [s for s in result if s["type"] == "sector_entering_top"]
        leaving = [s for s in result if s["type"] == "sector_leaving_top"]
        assert len(entering) == 2
        assert len(leaving) == 2
        assert {s["sector"] for s in entering} == {"半导体", "军工"}
        assert {s["sector"] for s in leaving} == {"金融", "地产"}


class TestSectorStrength:
    def test_dataclass_creation_and_field_access(self):
        ss = SectorStrength(
            name="半导体",
            code="BK1036",
            change_pct=3.5,
            momentum_score=85.2,
            capital_flow=1.5e9,
            leading_stocks=[{"name": "中芯国际", "change_pct": 5.0}],
            rank=1,
        )
        assert ss.name == "半导体"
        assert ss.code == "BK1036"
        assert ss.change_pct == 3.5
        assert ss.momentum_score == 85.2
        assert ss.capital_flow == 1.5e9
        assert len(ss.leading_stocks) == 1
        assert ss.leading_stocks[0]["name"] == "中芯国际"
        assert ss.rank == 1

    def test_default_values(self):
        ss = SectorStrength(
            name="医药",
            code="BK0727",
            change_pct=1.2,
            momentum_score=40.0,
            capital_flow=-0.5e9,
        )
        assert ss.leading_stocks == []
        assert ss.rank == 0


class TestGetSectorRotationAnalyzer:
    def test_singleton_returns_same_instance(self):
        import core.sector_rotation as mod

        original_analyzer = mod._analyzer
        mod._analyzer = None
        try:
            a1 = get_sector_rotation_analyzer()
            a2 = get_sector_rotation_analyzer()
            assert a1 is a2
            assert isinstance(a1, SectorRotationAnalyzer)
        finally:
            mod._analyzer = original_analyzer
