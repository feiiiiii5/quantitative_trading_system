from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QUANTCORE_SERVER_")

    host: str = Field(default="0.0.0.0", description="服务器监听地址")
    port: int = Field(default=8080, ge=1024, le=65535, description="服务器端口")
    workers: int = Field(default=1, ge=1, le=16, description="工作进程数")
    log_level: str = Field(default="info", pattern="^(debug|info|warning|error)$")
    cors_origins: list[str] = Field(default_factory=list, description="CORS允许的来源")


class BacktestSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QUANTCORE_BACKTEST_")

    initial_capital: float = Field(default=1000000, ge=10000, description="回测初始资金")
    commission: float = Field(default=0.0003, ge=0, le=0.01, description="佣金费率")
    stamp_tax: float = Field(default=0.001, ge=0, le=0.01, description="印花税率")
    slippage_pct: float = Field(default=0.001, ge=0, le=0.01, description="滑点百分比")
    use_vectorized: bool = Field(default=True, description="使用向量化回测")


class RiskSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QUANTCORE_RISK_")

    max_concentration: float = Field(default=0.3, ge=0.05, le=1.0, description="最大持仓集中度")
    max_daily_loss: float = Field(default=0.05, ge=0.01, le=0.2, description="最大日损失比例")
    max_open_trades: int = Field(default=10, ge=1, le=50, description="最大同时持仓数")
    trailing_stop: float = Field(default=-0.05, ge=-0.2, le=0, description="移动止损比例")
    trailing_stop_positive: float = Field(default=0.02, ge=0, le=0.1, description="盈利移动止损")
    trailing_stop_positive_offset: float = Field(default=0.05, ge=0, le=0.2, description="盈利止损触发偏移")


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QUANTCORE_API_")

    auth_enabled: bool = Field(default=False, description="启用API认证")
    api_key: str = Field(default="", description="API密钥")
    rate_limit_per_minute: int = Field(default=120, ge=10, le=10000, description="每分钟请求限制")


class DataSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QUANTCORE_DATA_")

    cache_ttl_realtime: int = Field(default=8, ge=1, le=60, description="实时数据缓存TTL(秒)")
    cache_ttl_history: int = Field(default=120, ge=10, le=600, description="历史数据缓存TTL(秒)")
    max_concurrent_requests: int = Field(default=5, ge=1, le=20, description="最大并发请求数")


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="QUANTCORE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    config_path: Path = Field(
        default=Path(__file__).parent.parent / "config.json",
        description="配置文件路径",
    )
    server: ServerSettings = Field(default_factory=ServerSettings)
    backtest: BacktestSettings = Field(default_factory=BacktestSettings)
    risk: RiskSettings = Field(default_factory=RiskSettings)
    api: ApiSettings = Field(default_factory=ApiSettings)
    data: DataSettings = Field(default_factory=DataSettings)

    @field_validator("config_path")
    @classmethod
    def resolve_config_path(cls, v: Path) -> Path:
        return v.resolve()


_settings_instance: AppSettings | None = None


def get_settings() -> AppSettings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = AppSettings()
    return _settings_instance
