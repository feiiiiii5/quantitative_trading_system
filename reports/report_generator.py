#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告生成器模块
支持HTML报告生成，可选依赖plotly/jinja2
"""

import os
from datetime import datetime
from pathlib import Path

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class ReportGenerator:
    """报告生成器"""

    def __init__(self):
        self.output_dir = Path("reports/output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_html_report(
        self,
        metrics=None,
        equity_curve=None,
        trades=None,
        output_path: str = None,
        symbol: str = "",
        strategy_name: str = "",
    ) -> str:
        """
        生成HTML报告

        Args:
            metrics: 回测指标对象
            equity_curve: 权益曲线数据
            trades: 交易记录
            output_path: 输出路径
            symbol: 股票代码
            strategy_name: 策略名称

        Returns:
            报告文件路径
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = str(self.output_dir / f"report_{symbol}_{timestamp}.html")

        metrics_html = self._build_metrics_section(metrics)
        chart_html = self._build_chart_section(equity_curve)
        trades_html = self._build_trades_section(trades)

        html = self._build_full_html(
            symbol=symbol,
            strategy_name=strategy_name,
            metrics_html=metrics_html,
            chart_html=chart_html,
            trades_html=trades_html,
        )

        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        return output_path

    def generate_text_report(
        self,
        metrics=None,
        equity_curve=None,
        trades=None,
        output_path: str = None,
        symbol: str = "",
        strategy_name: str = "",
    ) -> str:
        """
        生成纯文本报告（降级模式）
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = str(self.output_dir / f"report_{symbol}_{timestamp}.txt")

        lines = []
        lines.append("=" * 60)
        lines.append(f"QuantSystem Pro 回测报告")
        lines.append(f"股票: {symbol}  策略: {strategy_name}")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)

        if metrics:
            lines.append("\n--- 核心指标 ---")
            for attr in ['annual_return', 'sharpe_ratio', 'max_drawdown',
                         'win_rate', 'profit_factor', 'total_return',
                         'sortino_ratio', 'calmar_ratio']:
                val = getattr(metrics, attr, None)
                if val is not None:
                    if isinstance(val, float):
                        if attr in ('win_rate', 'annual_return', 'total_return', 'max_drawdown'):
                            lines.append(f"  {attr}: {val:.2%}")
                        else:
                            lines.append(f"  {attr}: {val:.4f}")
                    else:
                        lines.append(f"  {attr}: {val}")

        if trades and HAS_PANDAS and isinstance(trades, pd.DataFrame):
            lines.append(f"\n--- 交易记录 ({len(trades)}笔) ---")
            lines.append(trades.to_string())

        lines.append("\n" + "=" * 60)
        lines.append("免责声明：本报告仅供学习研究，不构成投资建议")
        lines.append("=" * 60)

        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return output_path

    def _build_metrics_section(self, metrics) -> str:
        """构建指标部分HTML"""
        if metrics is None:
            return "<p>无指标数据</p>"

        rows = []
        for attr in ['annual_return', 'sharpe_ratio', 'max_drawdown',
                     'win_rate', 'profit_factor', 'total_return',
                     'sortino_ratio', 'calmar_ratio', 'sqn', 'omega_ratio']:
            val = getattr(metrics, attr, None)
            if val is not None:
                if isinstance(val, float):
                    if attr in ('win_rate', 'annual_return', 'total_return', 'max_drawdown'):
                        display = f"{val:.2%}"
                    else:
                        display = f"{val:.4f}"
                else:
                    display = str(val)
                label = attr.replace('_', ' ').title()
                rows.append(f'<tr><td>{label}</td><td>{display}</td></tr>')

        if not rows:
            return "<p>无指标数据</p>"

        return f'<table class="metrics-table"><thead><tr><th>指标</th><th>值</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'

    def _build_chart_section(self, equity_curve) -> str:
        """构建图表部分HTML"""
        if equity_curve is None or not HAS_PLOTLY:
            return "<p>无图表数据</p>"

        try:
            if HAS_PANDAS and isinstance(equity_curve, pd.DataFrame):
                fig = go.Figure()
                if 'equity' in equity_curve.columns:
                    fig.add_trace(go.Scatter(
                        x=equity_curve.index if hasattr(equity_curve, 'index') else list(range(len(equity_curve))),
                        y=equity_curve['equity'],
                        mode='lines',
                        name='权益曲线',
                    ))
                elif 'close' in equity_curve.columns:
                    fig.add_trace(go.Scatter(
                        x=equity_curve.index if hasattr(equity_curve, 'index') else list(range(len(equity_curve))),
                        y=equity_curve['close'],
                        mode='lines',
                        name='收盘价',
                    ))
                fig.update_layout(title="权益曲线", height=400)
                return fig.to_html(full_html=False, include_plotlyjs='cdn')
        except Exception:
            pass

        return "<p>图表生成失败</p>"

    def _build_trades_section(self, trades) -> str:
        """构建交易记录部分HTML"""
        if trades is None:
            return "<p>无交易记录</p>"

        if HAS_PANDAS and isinstance(trades, pd.DataFrame):
            return f'<div class="trades-table">{trades.to_html(classes="trades-data", index=False)}</div>'

        return f"<p>交易记录: {len(trades) if hasattr(trades, '__len__') else 'N/A'} 笔</p>"

    def _build_full_html(self, symbol, strategy_name, metrics_html, chart_html, trades_html) -> str:
        """构建完整HTML页面"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QuantSystem Pro 回测报告 - {symbol}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f7; color: #1d1d1f; padding: 40px 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 8px; }}
        h2 {{ font-size: 20px; font-weight: 600; margin: 24px 0 12px; color: #0071e3; }}
        .subtitle {{ color: #86868b; font-size: 15px; margin-bottom: 32px; }}
        .metrics-table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .metrics-table th, .metrics-table td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid #f0f0f0; }}
        .metrics-table th {{ background: #fafafa; font-weight: 600; font-size: 13px; color: #86868b; text-transform: uppercase; }}
        .metrics-table td {{ font-size: 15px; }}
        .chart-section {{ background: white; border-radius: 12px; padding: 20px; margin: 16px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .trades-table {{ background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .trades-data {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        .trades-data th, .trades-data td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #f0f0f0; }}
        .trades-data th {{ background: #fafafa; font-weight: 600; }}
        .disclaimer {{ margin-top: 32px; padding: 16px; background: #fff3cd; border-radius: 8px; font-size: 13px; color: #856404; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>QuantSystem Pro 回测报告</h1>
        <p class="subtitle">股票: {symbol} | 策略: {strategy_name or 'N/A'} | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <h2>📊 核心指标</h2>
        {metrics_html}

        <h2>📈 权益曲线</h2>
        <div class="chart-section">
            {chart_html}
        </div>

        <h2>📋 交易记录</h2>
        {trades_html}

        <div class="disclaimer">
            ⚠️ 免责声明：本报告基于历史数据生成，仅供学习研究参考，不构成任何投资建议。市场有风险，投资需谨慎。
        </div>
    </div>
</body>
</html>"""
