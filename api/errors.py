from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class ErrorCategory(enum.Enum):
    AUTH = "auth"
    VALIDATION = "validation"
    MARKET_DATA = "market_data"
    BACKTEST = "backtest"
    PORTFOLIO = "portfolio"
    RATE_LIMIT = "rate_limit"
    SYSTEM = "system"
    NOT_FOUND = "not_found"


class ErrorCode(enum.Enum):
    AUTH_INVALID_CREDENTIALS = ("AUTH_001", ErrorCategory.AUTH, 401, False)
    AUTH_TOKEN_EXPIRED = ("AUTH_002", ErrorCategory.AUTH, 401, True)
    AUTH_FORBIDDEN = ("AUTH_003", ErrorCategory.AUTH, 403, False)
    AUTH_RATE_LIMITED = ("AUTH_004", ErrorCategory.AUTH, 429, True)

    VALIDATION_INVALID_INPUT = ("VAL_001", ErrorCategory.VALIDATION, 400, False)
    VALIDATION_MISSING_FIELD = ("VAL_002", ErrorCategory.VALIDATION, 400, False)
    VALIDATION_INVALID_SYMBOL = ("VAL_003", ErrorCategory.VALIDATION, 400, False)
    VALIDATION_INVALID_DATE = ("VAL_004", ErrorCategory.VALIDATION, 400, False)
    VALIDATION_BODY_TOO_LARGE = ("VAL_005", ErrorCategory.VALIDATION, 413, False)

    MARKET_DATA_UNAVAILABLE = ("MKT_001", ErrorCategory.MARKET_DATA, 503, True)
    MARKET_DATA_TIMEOUT = ("MKT_002", ErrorCategory.MARKET_DATA, 504, True)
    MARKET_DATA_NOT_FOUND = ("MKT_003", ErrorCategory.MARKET_DATA, 404, False)

    BACKTEST_ENGINE_ERROR = ("BKT_001", ErrorCategory.BACKTEST, 500, False)
    BACKTEST_INVALID_PARAMS = ("BKT_002", ErrorCategory.BACKTEST, 400, False)
    BACKTEST_TIMEOUT = ("BKT_003", ErrorCategory.BACKTEST, 408, True)

    PORTFOLIO_INSUFFICIENT_DATA = ("PRT_001", ErrorCategory.PORTFOLIO, 400, False)
    PORTFOLIO_RISK_LIMIT = ("PRT_002", ErrorCategory.PORTFOLIO, 400, False)

    RATE_LIMIT_EXCEEDED = ("RL_001", ErrorCategory.RATE_LIMIT, 429, True)
    RATE_LIMIT_SERVER_LOAD = ("RL_002", ErrorCategory.RATE_LIMIT, 429, True)

    SYSTEM_SHUTTING_DOWN = ("SYS_001", ErrorCategory.SYSTEM, 503, True)
    SYSTEM_INTERNAL = ("SYS_002", ErrorCategory.SYSTEM, 500, False)
    SYSTEM_DB_ERROR = ("SYS_003", ErrorCategory.SYSTEM, 500, True)

    NOT_FOUND_RESOURCE = ("NF_001", ErrorCategory.NOT_FOUND, 404, False)
    NOT_FOUND_ENDPOINT = ("NF_002", ErrorCategory.NOT_FOUND, 404, False)

    def __init__(self, code: str, category: ErrorCategory, http_status: int, retryable: bool):
        self.code = code
        self.category = category
        self.http_status = http_status
        self.retryable = retryable


@dataclass(slots=True)
class AppError(Exception):
    error_code: ErrorCode
    message: str = ""
    details: dict = field(default_factory=dict)
    retry_after: int | None = None

    def __post_init__(self):
        if not self.message:
            self.message = self.error_code.name.replace("_", " ").title()

    @property
    def http_status(self) -> int:
        return self.error_code.http_status

    @property
    def retryable(self) -> bool:
        return self.error_code.retryable

    def to_response(self) -> dict:
        resp = {
            "success": False,
            "error": {
                "code": self.error_code.code,
                "category": self.error_code.category.value,
                "message": self.message,
                "retryable": self.retryable,
            },
        }
        if self.details:
            resp["error"]["details"] = self.details
        if self.retry_after is not None:
            resp["error"]["retry_after"] = self.retry_after
        return resp


def auth_error(message: str = "", *, code: ErrorCode = ErrorCode.AUTH_INVALID_CREDENTIALS) -> AppError:
    return AppError(error_code=code, message=message)


def validation_error(message: str = "", *, code: ErrorCode = ErrorCode.VALIDATION_INVALID_INPUT, details: dict | None = None) -> AppError:
    return AppError(error_code=code, message=message, details=details or {})


def not_found_error(message: str = "", *, code: ErrorCode = ErrorCode.NOT_FOUND_RESOURCE) -> AppError:
    return AppError(error_code=code, message=message)


def rate_limit_error(message: str = "", retry_after: int = 2, *, code: ErrorCode = ErrorCode.RATE_LIMIT_EXCEEDED) -> AppError:
    return AppError(error_code=code, message=message, retry_after=retry_after)


def system_error(message: str = "", *, code: ErrorCode = ErrorCode.SYSTEM_INTERNAL) -> AppError:
    return AppError(error_code=code, message=message)


def market_data_error(message: str = "", *, code: ErrorCode = ErrorCode.MARKET_DATA_UNAVAILABLE) -> AppError:
    return AppError(error_code=code, message=message)


def backtest_error(message: str = "", *, code: ErrorCode = ErrorCode.BACKTEST_ENGINE_ERROR) -> AppError:
    return AppError(error_code=code, message=message)


def portfolio_error(message: str = "", *, code: ErrorCode = ErrorCode.PORTFOLIO_INSUFFICIENT_DATA) -> AppError:
    return AppError(error_code=code, message=message)
