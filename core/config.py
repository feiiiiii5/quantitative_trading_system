"""
QuantCore 配置系统 - Pydantic Settings + YAML
"""
import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class DataConfig(BaseSettings):
    """数据配置"""
    model_config = SettingsConfigDict(env_prefix="QC_DATA_")

    cache_ttl: int = Field(default=300, description="缓存TTL(秒)")
    parquet_path: str = Field(default=str(BASE_DIR / "data" / "parquet"), description="Parquet存储路径")
    sqlite_path: str = Field(default=str(BASE_DIR / "data" / "quantvision.db"), description="SQLite路径")
    max_memory_mb: int = Field(default=512, description="最大内存缓存(MB)")
    local_test_mode: bool = Field(default=False, description="本地测试模式")
    enable_redis: bool = Field(default=False, description="启用Redis")
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis连接URL")


class TradingConfig(BaseSettings):
    """交易配置"""
    model_config = SettingsConfigDict(env_prefix="QC_TRADE_")

    initial_capital: float = Field(default=1000000.0, description="初始资金")
    commission_rate: float = Field(default=0.0003, description="佣金率")
    slippage: float = Field(default=0.001, description="滑点")
    max_position_ratio: float = Field(default=0.95, description="最大仓位比例")
    enable_t1: bool = Field(default=True, description="A股T+1规则")
    circuit_breaker_drawdown: float = Field(default=0.15, description="熔断回撤阈值")
    max_daily_loss: float = Field(default=0.05, description="日最大亏损")


class RiskConfig(BaseSettings):
    """风控配置"""
    model_config = SettingsConfigDict(env_prefix="QC_RISK_")

    var_confidence: float = Field(default=0.95, description="VaR置信度")
    var_window: int = Field(default=252, description="VaR计算窗口")
    max_single_position: float = Field(default=0.3, description="单票最大仓位")
    max_sector_exposure: float = Field(default=0.5, description="行业最大暴露")
    stop_loss_pct: float = Field(default=0.08, description="止损比例")
    take_profit_pct: float = Field(default=0.15, description="止盈比例")


class APIConfig(BaseSettings):
    """API配置"""
    model_config = SettingsConfigDict(env_prefix="QC_API_")

    host: str = Field(default="0.0.0.0", description="监听地址")
    port: int = Field(default=8080, description="监听端口")
    workers: int = Field(default=1, description="工作进程数")
    log_level: str = Field(default="info", description="日志级别")
    enable_docs: bool = Field(default=True, description="启用API文档")
    rate_limit: int = Field(default=100, description="每分钟请求限制")


class ProxyConfig(BaseSettings):
    """代理配置"""
    model_config = SettingsConfigDict(env_prefix="QC_PROXY_")

    enabled: bool = Field(default=False, description="启用代理")
    http_proxy: Optional[str] = Field(default=None, description="HTTP代理")
    https_proxy: Optional[str] = Field(default=None, description="HTTPS代理")


class QuantCoreConfig(BaseSettings):
    """QuantCore 全局配置"""
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    app_name: str = Field(default="QuantCore", description="应用名称")
    version: str = Field(default="2.0.0", description="版本号")
    debug: bool = Field(default=False, description="调试模式")

    data: DataConfig = Field(default_factory=DataConfig)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)

    # 数据源优先级
    data_sources: List[str] = Field(
        default=["akshare", "baostock", "tushare", "eastmoney"],
        description="数据源优先级"
    )

    # 支持的市场
    markets: List[str] = Field(
        default=["A", "HK", "US"],
        description="支持的市场"
    )


# 全局配置实例
settings = QuantCoreConfig()


def get_settings() -> QuantCoreConfig:
    """获取配置实例"""
    return settings
