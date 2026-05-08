# QuantCore 世界级量化交易系统 — Claude Code 完整工程提示词

> 适用对象：Claude Code CLI / Project Mode  
> 工作模式：逐模块迭代，每次执行前先 `read` 相关文件，严格遵循现有架构风格  
> 优先级标记：🔴 Critical | 🟠 High | 🟡 Medium | 🟢 Nice-to-have

---

## 0. 全局工作守则（每次对话开始必读）

```
你是一名拥有20年经验的量化金融工程师 + 全栈架构师。
当前项目是 QuantCore，一个基于 Python FastAPI + Vue3 的量化交易系统。
代码库路径已挂载，所有修改必须：
1. 先 read 目标文件，理解现有逻辑，不破坏已有接口
2. 只修改必要部分，不做无关重构
3. 关键算法处加简洁中文注释
4. 每次修改后输出【变更摘要】：改了什么文件、为什么、预期影响
5. 涉及金融计算必须考虑 NaN/Inf/除零/空数据等边界情况
6. Python 代码风格：简洁直接，无多余 docstring，关键处注释
7. 前端代码：Vue3 Composition API + TypeScript，复用 CSS 变量
```

---

## 一、量化策略层（core/strategies.py + core/adaptive_strategy.py）

### 1.1 🔴 新增机构级策略实现

```
目标文件：core/strategies.py

在现有策略基础上，新增以下策略类，每个策略必须：
- 继承 BaseStrategy
- 实现 generate_signal(df) -> TradeSignal
- 实现 generate_score(df) -> float，返回 [-1, 1]
- 实现静态方法 get_param_space() -> dict（用于网格搜索）
- 信号强度精确到两位小数

【策略1】IchimokuCloudStrategy（一目均衡表策略）
逻辑：
- 转换线(9期)上穿基准线(26期) + 收盘价在云层之上 + 迟行线在价格之上 → 强烈买入(0.9)
- 收盘价突破云层上边界且成交量放大1.5倍以上 → 买入(0.75)
- 收盘价跌破云层下边界 → 卖出(0.8)
- 云层由薄变厚（未来26期）且向上 → 趋势确认加分
param_space: {"tenkan_period": {min:7, max:15, step:1}, "kijun_period": {min:20, max:32, step:2}}

【策略2】WyckoffAccumulationStrategy（威科夫积累阶段策略）
逻辑：
- 识别5个阶段：PS(初步支撑)→SC(抛售高潮)→AR(自动反弹)→ST(二次测试)→SOS(力量显现)
- 用 60 日窗口，成交量-价格关系判断阶段
- SC阶段识别：价格创新低+成交量暴增(>3x均量)+下影线>实体2倍 → 关注买入
- SOS阶段：价格突破AR高点+成交量确认 → 强烈买入(0.85)
- 任何阶段价格跌破SC低点 → 卖出(0.9)

【策略3】VWAPDeviationStrategy（VWAP偏离策略）
逻辑：
- 计算滚动20日VWAP及标准差
- 价格偏离VWAP超过-2.5σ且RSI<35且成交量不放大 → 买入(0.8)
- 价格偏离VWAP超过+2.5σ且RSI>65 → 卖出(0.8)
- 价格回归至VWAP±0.3σ区间 → 平仓信号(0.6)
param_space: {"vwap_window": {min:10, max:30, step:5}, "sigma_mult": {min:1.5, max:3.0, step:0.25}}

【策略4】ElliottWaveAIStrategy（简化艾略特波浪）
逻辑：
- 用 scipy.signal.find_peaks 识别近120日的波峰波谷序列
- 识别5浪上升结构：验证各浪比例关系（黄金分割0.618/1.618）
- 判断当前处于第3浪初期（最强上升浪）→ 强烈买入(0.9)
- 判断处于第5浪末期（RSI背离+成交量萎缩）→ 卖出(0.85)
- 识别ABC调整浪的C浪末端 → 买入机会(0.7)

【策略5】MarketMicrostructureStrategy（市场微观结构策略）
逻辑（无逐笔数据时用日线近似）：
- Amihud非流动性比率：|收益率|/成交额，滚动20日均值
- 非流动性突然下降（流动性改善）且价格上涨 → 买入信号(0.65)
- 计算价格冲击系数：大成交量对应的价格变动幅度
- 连续3日冲击系数下降+价格上行 → 机构吸筹信号(0.75)
- Kyle's Lambda（简化版）估算信息不对称程度

【策略6】CopulaCorrelationStrategy（Copula相关性策略）
逻辑：
- 需要传入基准指数数据（默认沪深300）
- 用滚动60日计算股票与基准的秩相关（Spearman）
- 相关性骤降（>0.3偏离历史均值）且个股强于基准 → 买入(0.75)
- 相关性骤升+个股弱于基准 → 卖出(0.7)
- 用 scipy.stats.spearmanr 实现

【策略7】RegimeSwitchingStrategy（马尔科夫机制转换策略）
逻辑：
- 基于收益率序列，用简化2状态HMM（手写，不依赖hmmlearn）
  - 状态0：低波动牛市；状态1：高波动熊市
- 用EM算法迭代估计转移概率矩阵和发射参数
- 当前状态=0且转移概率P(0→0)>0.8 → 买入(0.7)
- 当前状态=1或P(0→1)上升趋势 → 卖出(0.75)
- 最大迭代50次，收敛阈值1e-6

【策略8】OrderFlowImbalanceStrategy（订单流失衡策略）
逻辑（用OHLCV近似）：
- 估计买压/卖压：若收盘>开盘，买压=成交量*(收盘-最低)/(最高-最低)
- 滚动10日订单流失衡指标 OFI = (买压-卖压)/总成交量
- OFI > 0.3且加速上升 → 买入(0.7)
- OFI < -0.3且加速下降 → 卖出(0.7)
- OFI背离价格（价涨OFI降）→ 反转预警(-0.5)

【策略9】FractalBreakoutStrategy（分形突破策略）
逻辑：
- Bill Williams分形识别：5根K线中间K线最高/最低
- 向上分形（近20日内最高分形）被突破且成交量>1.5x均量 → 买入(0.75)
- 向下分形被跌破 → 卖出(0.75)
- 与鳄鱼线（5/8/13日均线）配合：价格在鳄鱼嘴上方且嘴张开 → 加分

【策略10】QuantileRegressionStrategy（分位数回归策略）
逻辑：
- 对收盘价做分位数回归（τ=0.1, 0.5, 0.9），窗口60日
- 用 scipy.stats.mstats.idealfourths 或手写分位数回归
- 价格跌破τ=0.1分位线且斜率为正 → 超跌买入(0.8)
- 价格超过τ=0.9分位线且斜率放缓 → 超买卖出(0.75)
- 中位数线斜率方向代表趋势强度

完成后在 STRATEGY_REGISTRY 字典中注册所有新策略。
在 CompositeStrategy 的 strategies 列表中添加得分最高的4个。
```

### 1.2 🔴 自适应策略引擎深度升级

```
目标文件：core/adaptive_strategy.py

【升级1】市场状态识别精细化
在 classify_market_regime() 中新增2个状态：
- BEAR_TRAP = "bear_trap"：假跌破后快速收复，熊市陷阱
  识别：价格跌破20日低点后2日内强力收复+成交量萎缩→识别为陷阱
- DISTRIBUTION_TOP = "distribution_top"：顶部派发
  识别：连续5日价格在高位震荡+换手率下降+OBV背离→识别为顶部

将现有的 ADX 阈值从固定值改为自适应：
- 计算过去252日 ADX 的75百分位作为"强趋势"阈值
- 50百分位作为"温和趋势"阈值
- 避免不同个股因波动率差异导致分类偏差

【升级2】动态权重强化学习（简化版Q-Learning）
在 _adapt_strategy_weights() 中实现：
- 状态空间：(市场状态, 最近5笔交易胜负序列) → 离散化为有限状态
- 动作空间：调高/调低/维持各策略权重
- 奖励函数：(交易收益-benchmark收益) / ATR，夏普比率调整
- Q-table 用 dict 存储，学习率 α=0.1，折扣因子 γ=0.9
- ε-greedy探索：ε随交易次数从0.3衰减至0.05
- 每完成10笔交易更新一次Q-table

【升级3】多周期信号融合
在主循环中增加多时间框架分析：
- 日线信号（现有）
- 从日线数据合成周线（每5个交易日一个周期）
- 从日线数据合成月线（每21个交易日）
- 融合规则：日线买入+周线趋势向上+月线不在超买 → 信号权重×1.5
- 日线买入但周线下降趋势 → 信号权重×0.5
- 用 _resample_to_weekly(df) 和 _resample_to_monthly(df) 实现重采样

【升级4】尾部风险保护（CVaR约束）
在每次买入决策前：
- 计算过去60日收益率的CVaR(5%)（条件在险价值）
- 若CVaR > 5%（即极端情况下日亏超5%），则仓位上限×0.6
- 若CVaR > 8%，暂停所有买入操作
- CVaR = mean(收益率 | 收益率 < VaR_5%)

【升级5】相关性矩阵去重
在持仓超过3个标的时（为多标的扩展做准备）：
- 计算各持仓之间60日收益率的相关矩阵
- 若新买入标的与现有持仓相关性>0.85，降低仓位至原计划的50%
- 避免持仓过度集中于同一风险因子
```

### 1.3 🟠 因子库扩展

```
目标文件：core/indicators.py（新增函数，不修改现有函数）

新增以下独立函数（供策略和因子分析使用）：

def calc_factor_momentum_quality(c, v, period=20) -> np.ndarray:
    """动量质量因子：上涨日成交量/下跌日成交量的滚动比值"""

def calc_factor_price_acceleration(c, period=10) -> np.ndarray:
    """价格加速度：一阶导数变化率，用二阶差分近似"""

def calc_factor_volume_price_trend(c, v, period=14) -> np.ndarray:
    """VPT量价趋势因子"""

def calc_factor_efficiency_ratio(c, period=10) -> np.ndarray:
    """Kaufman效率比率：净移动/总移动，衡量趋势纯度，0-1之间"""

def calc_factor_fractal_dimension(c, period=30) -> np.ndarray:
    """用Hurst指数近似的分形维度，衡量价格随机性"""

def calc_factor_relative_volume(v, short=5, long=20) -> np.ndarray:
    """相对成交量：短期均量/长期均量"""

def calc_factor_money_flow_index(h, l, c, v, period=14) -> np.ndarray:
    """资金流量指数MFI，量价结合版RSI"""

def calc_factor_elder_ray(c, period=13) -> tuple[np.ndarray, np.ndarray]:
    """Elder Ray牛市/熊市力量：高价-EMA, 低价-EMA"""

def calc_factor_dpo(c, period=20) -> np.ndarray:
    """去趋势价格振荡器DPO：剔除长期趋势"""

def calc_factor_coppock_curve(c) -> np.ndarray:
    """Coppock曲线：长期底部识别，11+14月ROC的10月WMA"""

def calc_factor_trix(c, period=15) -> np.ndarray:
    """TRIX三重平滑EMA，过滤噪声"""

def calc_factor_ultimate_oscillator(h, l, c, p1=7, p2=14, p3=28) -> np.ndarray:
    """终极振荡器，多周期综合"""

def calc_factor_chaikin_volatility(h, l, period=10) -> np.ndarray:
    """Chaikin波动率：EMA(H-L)的变化率"""

def calc_factor_connors_rsi(c, rsi_p=3, streak_p=2, rank_p=100) -> np.ndarray:
    """Connors RSI：复合短线超买超卖指标"""

def calc_composite_score(factor_dict: dict, weights: dict = None) -> np.ndarray:
    """
    多因子合成打分
    - Z-score标准化各因子
    - 按weights加权求和
    - 输出分位数排名[0,1]
    """

所有函数要求：
- 纯numpy实现，避免循环（向量化）
- 输入输出形状一致，NaN安全
- 头部不足数据用np.nan填充
```

### 1.4 🟠 回测引擎专业化升级

```
目标文件：core/backtest.py

【升级1】真实交易成本模型
在 BacktestEngine 中新增 RealisticCostModel 内部类：
- 印花税：卖出0.1%（2024年最新税率，已从0.1%下调，可配置）
- 佣金：买卖双向0.02%（最低5元），模拟折扣券商
- 过户费：沪市0.00001/股（深市免）
- 市场冲击：用 sqrt(成交额比例) × 0.1% 模拟
- 融资利率：若开启杠杆，年化4.5%/365按日计
- 所有费率可在 __init__ 中配置覆盖

【升级2】更真实的成交模拟
在 _build_result() 中改进订单执行：
- TWAP执行：大单（>日成交额1%）分多笔成交，用TWAP价格
- 涨跌停处理：触及涨停时买单不保证成交，用概率模型（成交概率=1-排队比例）
- 集合竞价：开盘价±1%范围内随机成交，模拟开盘不确定性
- T+1限制：已在 SimulatedTrading 中实现，回测也要遵守

【升级3】高级绩效指标
在 BacktestResult 中新增字段，在 _build_result() 末尾计算：
- omega_ratio: float = 0.0  # Omega比率：超过阈值收益/低于阈值损失
- tail_ratio: float = 0.0   # 尾部比率：95分位收益/5分位损失的绝对值
- information_ratio: float = 0.0  # 信息比率：超额收益/跟踪误差
- recovery_factor: float = 0.0   # 恢复因子：总收益/最大回撤
- avg_mae: float = 0.0           # 平均最大不利偏离（MAE）
- avg_mfe: float = 0.0           # 平均最大有利偏离（MFE）
- expectancy: float = 0.0        # 期望值：胜率×平均盈利 - 败率×平均亏损
- payoff_ratio: float = 0.0      # 盈亏比：平均盈利/平均亏损

计算 MAE/MFE 需要逐笔交易追踪：
- MAE：从买入到卖出期间，最大未实现亏损
- MFE：从买入到卖出期间，最大未实现盈利
- 需要在主循环中维护 position_high/position_low

【升级4】蒙特卡洛模拟
新增方法 monte_carlo_analysis(result, n_simulations=1000) -> dict：
- 随机打乱交易序列（保序不改值）进行bootstrap
- 计算1000次模拟的分布统计
- 输出：最终净值的5th/50th/95th百分位
- 最大回撤分布，95%置信区间
- 策略稳健性得分（实际夏普/模拟夏普中位数）
- 用于判断策略是否是"运气"还是"技能"

【升级5】参数敏感性分析
新增方法 sensitivity_analysis(strategy_cls, df, base_params, param_ranges) -> dict：
- 对每个参数在±20%范围内扫描5个点
- 固定其他参数，单独变化目标参数
- 输出：每个参数对 sharpe_ratio 的弹性系数
- 绘制热力图数据（2D参数扫描）
- 识别参数敏感区域，给出稳健参数建议
```

---

## 二、数据层升级（core/data_fetcher.py + core/database.py）

### 2.1 🔴 多源数据聚合与质量控制

```
目标文件：core/data_fetcher.py

【升级1】新增数据源 EastMoneySource（东方财富）
实现以下方法：
async def fetch_realtime(symbol, market) -> Optional[dict]:
    # 接口：https://push2.eastmoney.com/api/qt/stock/get
    # 参数：secid根据市场拼接，1.000001=沪市，0.000001=深市
    # 解析字段：f43=最新价, f170=涨跌幅, f169=涨跌额, f47=成交量
    # f48=成交额, f116=总市值, f117=流通市值, f168=换手率
    
async def fetch_history_em(symbol, market, ktype='101', fqt=1) -> Optional[pd.DataFrame]:
    # 接口：https://push2his.eastmoney.com/api/qt/stock/kline/get
    # ktype: 101=日K, 102=周K, 103=月K
    # fqt: 0=不复权, 1=前复权, 2=后复权
    # 返回标准 DataFrame：date,open,close,high,low,volume,amount,change_pct

async def fetch_financial_report(symbol) -> Optional[dict]:
    # 获取最新财务数据：PE/PB/ROE/净利润增速/营收增速
    # 接口：https://datacenter.eastmoney.com/api/data/v1/get
    # 返回：{pe_ttm, pb, roe, eps, revenue_yoy, profit_yoy, debt_ratio}

async def fetch_north_bound_flow(date=None) -> Optional[dict]:
    # 北向资金实时数据
    # 返回：{sh_buy, sh_sell, sz_buy, sz_sell, total_net, top_stocks}

async def fetch_limit_up_pool() -> list[dict]:
    # 涨停板股票池（当日）
    # 返回：[{code, name, time, reason, chain_count, seal_amount}]

async def fetch_dragon_tiger_list(date=None) -> list[dict]:
    # 龙虎榜数据
    # 返回：[{code, name, reason, buy_amount, sell_amount, institutions}]

【升级2】数据质量控制层
新增 DataQualityChecker 类：

class DataQualityChecker:
    @staticmethod
    def check_kline(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        """
        检查并修复K线数据质量问题：
        1. 检测价格异常：单日涨跌超过±20%（A股）标记为可疑
        2. 检测成交量为0但价格变动的异常
        3. 前复权价格的负值或零值检测
        4. 日期连续性检查（非交易日）
        5. OHLC逻辑一致性：high>=max(open,close), low<=min(open,close)
        6. 自动修复：线性插值填充单个NaN；
           连续3个以上NaN则标记该段数据为不可用
        返回：(cleaned_df, warnings_list)
        """
    
    @staticmethod    
    def detect_corporate_actions(df: pd.DataFrame) -> list[dict]:
        """
        检测可能的送股/除权事件：
        - 相邻两日价格比率显著偏离正常范围（<0.7或>1.3）
        - 结合成交量异常放大判断
        返回：[{date, type, ratio}]
        """
    
    @staticmethod
    def normalize_adjust_factor(df: pd.DataFrame) -> pd.DataFrame:
        """
        统一前复权处理：
        - 检测并修正前复权价格倒置问题
        - 确保复权后序列单调递增趋势符合逻辑
        """

在 SmartDataFetcher.get_history() 中集成质量检查：
df, warnings = DataQualityChecker.check_kline(df)
if warnings:
    logger.debug(f"Data quality warnings for {symbol}: {warnings}")

【升级3】智能缓存策略
在 SmartDataFetcher 中重构缓存逻辑：
- 实时数据：交易时间内TTL=3秒，非交易时间TTL=300秒
- 日线历史：TTL=当天收盘后更新，用日期戳判断
- 分钟线：TTL=60秒
- 新增 _cache_freshness_check()：
  - 交易时间内，若缓存数据的最新日期不是今天，强制刷新
  - 非交易时间，若缓存存在则直接返回
- 新增 prefetch_symbols(symbols: list) -> None：
  - 批量预热缓存，优先级队列，按自选股>持仓>热门排序

【升级4】备用数据源降级链
改进 _fetch_history_from_sources() 实现：
- 源优先级：东方财富 > 腾讯 > 新浪 > AKShare > BaoStock
- 超时控制：每个源最多3秒，总超时8秒
- 并发尝试前两个源，取先返回的有效结果
- 结果投票：若两源数据差异>5%，以成交量更大的为准
- 降级记录：记录每个源的连续失败次数，失败3次临时屏蔽1小时

【升级5】实时Level2数据近似
新增方法 simulate_level2_from_daily(symbol, realtime_data) -> dict：
- 基于实时数据模拟盘口信息
- 5档买卖价格：基于当前价格±tick_size计算
- 挂单量用历史成交量的高斯分布模拟
- 主要用于回测的成交价格修正
```

### 2.2 🟠 数据库层优化

```
目标文件：core/database.py

【升级1】新增数据表和操作方法

在 _init_db() 的 SQL 中新增表：

CREATE TABLE IF NOT EXISTS factor_cache (
    symbol TEXT NOT NULL,
    factor_name TEXT NOT NULL,
    date TEXT NOT NULL,
    value REAL,
    PRIMARY KEY (symbol, factor_name, date)
);

CREATE TABLE IF NOT EXISTS backtest_results (
    id TEXT PRIMARY KEY,
    strategy_name TEXT,
    symbol TEXT,
    start_date TEXT,
    end_date TEXT,
    params TEXT,
    result_json TEXT,
    created_at TEXT,
    sharpe_ratio REAL,
    total_return REAL,
    max_drawdown REAL
);

CREATE TABLE IF NOT EXISTS trade_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    strategy_name TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    signal_score REAL,
    price REAL,
    created_at TEXT,
    market_regime TEXT
);

CREATE INDEX IF NOT EXISTS idx_backtest_symbol ON backtest_results(symbol, strategy_name);
CREATE INDEX IF NOT EXISTS idx_signals_symbol ON trade_signals(symbol, created_at);

新增方法：
def save_backtest_result(self, strategy_name, symbol, start_date, end_date, params, result) -> str:
    """保存回测结果，返回ID"""

def get_backtest_history(self, symbol=None, strategy_name=None, limit=20) -> list[dict]:
    """查询历史回测记录"""

def save_trade_signal(self, symbol, strategy_name, signal_type, score, price, regime="") -> None:
    """保存交易信号记录（用于后验分析）"""

def get_factor_cache(self, symbol, factor_name, start_date="", end_date="") -> pd.DataFrame:
    """获取因子缓存"""

def set_factor_cache(self, symbol, factor_name, dates, values) -> None:
    """批量写入因子缓存"""

def get_performance_stats(self) -> dict:
    """返回系统运行统计：总回测次数、平均夏普、最佳策略等"""

【升级2】连接池优化
将当前 threading.local() 方案升级：
- 新增 _connection_pool: list[sqlite3.Connection] = []（最大5个连接）
- 实现 _acquire_conn() 和 _release_conn() 上下文管理器
- 读操作：从池中取可用连接，并发读不阻塞
- 写操作：序列化（保持WAL模式）
- 连接健康检查：execute("SELECT 1")，失败则重建

【升级3】数据压缩存储
对历史K线数据实现列式压缩：
- 存储时将 float 精度降至4位小数（价格）和0位（成交量）
- 对重复的 symbol/market/kline_type 前缀不重复存储（已是主键）
- 新增 compress_old_data() 方法：将90天以前的数据按周聚合存储
```

---

## 三、API层升级（api/routes.py + api/backtest_routes.py）

### 3.1 🔴 新增专业级API接口

```
目标文件：api/routes.py（新增路由，不修改现有路由）

【新增接口组1】技术分析深度分析
@router.get("/stock/analysis/{symbol}")
async def get_deep_analysis(request, symbol, period="1y"):
    """
    返回综合技术分析报告：
    {
        "trend": {
            "direction": "up/down/sideways",
            "strength": 0-100,
            "duration_days": int,
            "key_levels": {"support": [], "resistance": []}
        },
        "momentum": {
            "rsi_signal": "overbought/oversold/neutral",
            "macd_signal": "bullish/bearish/neutral",
            "kdj_signal": "...",
            "composite_momentum": -1 to 1
        },
        "volume": {
            "trend": "accumulation/distribution/neutral",
            "obv_divergence": bool,
            "volume_ratio_5d": float
        },
        "patterns": [...],  # K线形态
        "ichimoku": {...},
        "fibonacci_levels": [0.236, 0.382, 0.5, 0.618, 0.786的价格位],
        "composite_score": -100 to 100,
        "signal": "strong_buy/buy/neutral/sell/strong_sell",
        "signal_confidence": 0-100
    }
    """

@router.get("/stock/prediction/{symbol}")
async def get_price_prediction(request, symbol, horizons="1d,1w,1m"):
    """多时间框架价格预测，整合 core/prediction.py"""

@router.get("/stock/signals/{symbol}")
async def get_strategy_signals(request, symbol, period="3m"):
    """
    返回所有策略对该股票的信号历史：
    {
        "strategy_name": [...{date, signal, price, score}]
    }
    """

@router.get("/stock/correlation/{symbol}")
async def get_correlation_analysis(request, symbol, benchmark="sh000300", period="1y"):
    """
    返回与基准的相关性分析：
    - 滚动相关性曲线
    - Beta/Alpha分解
    - 相对强弱 (RS)
    - 相关性稳定性得分
    """

@router.get("/market/heatmap")
async def get_market_heatmap(request, market="A"):
    """
    返回行业/板块热力图数据：
    各行业当日涨跌幅，成交额占比，领涨/领跌股
    用 akshare.stock_board_industry_name_em() 获取
    """

@router.get("/market/northbound/detail")
async def get_northbound_detail(request):
    """北向资金详情：历史净买入、今日持仓变动、前十大买入股票"""

@router.get("/market/limit_up")
async def get_limit_up_pool(request):
    """今日涨停板池，含原因、炸板情况、连板数"""

@router.get("/market/dragon_tiger")
async def get_dragon_tiger(request, date=None):
    """龙虎榜数据"""

@router.get("/factor/analysis/{symbol}")
async def get_factor_analysis(request, symbol, period="1y"):
    """
    多因子分析：
    - 计算所有因子的当前值和历史分位数
    - 因子IC值（过去60日）
    - 因子综合评分
    - 各因子信号方向
    """

【新增接口组2】回测增强
@router.post("/backtest/advanced")
async def run_advanced_backtest(
    request,
    symbol: str = Query(...),
    strategy_name: str = Query("adaptive"),
    start_date: str = Query("2022-01-01"),
    end_date: str = Query("2024-12-31"),
    initial_capital: float = Query(1000000),
    enable_short: bool = Query(False),
    leverage: float = Query(1.0),
    monte_carlo: bool = Query(False),
    n_simulations: int = Query(500),
):
    """
    高级回测，返回：
    - 标准回测结果
    - 若 monte_carlo=True，额外返回蒙特卡洛分析
    - 参数敏感性摘要
    - 交易统计明细
    - MAE/MFE分析
    """

@router.post("/backtest/optimize")
async def optimize_strategy(
    request,
    symbol: str = Query(...),
    strategy_name: str = Query("ma_cross"),
    start_date: str = Query("2023-01-01"),
    end_date: str = Query("2024-12-31"),
    metric: str = Query("sharpe_ratio"),
    max_combinations: int = Query(100),
):
    """
    策略参数优化，返回Top10参数组合及其指标对比
    使用 core/backtest.py 中的 grid_search_params()
    """

@router.get("/backtest/history")
async def get_backtest_history(request, symbol=None, limit=20):
    """历史回测记录查询"""

【新增接口组3】组合分析
@router.get("/portfolio/risk_analysis")
async def get_portfolio_risk(request):
    """
    持仓风险分析：
    - 组合VaR(95%)和CVaR(95%)
    - 最大单一持仓集中度
    - 行业分布
    - 与沪深300相关性
    - Stress Test：若市场暴跌10%，组合预期损失
    """

@router.get("/portfolio/attribution")
async def get_return_attribution(request, period="1m"):
    """
    收益归因分析：
    - 各持仓对总收益的贡献
    - 选股收益 vs 择时收益
    - 对比benchmark超额收益
    """
```

### 3.2 🟠 WebSocket实时推送优化

```
目标文件：api/routes.py

在 push_realtime_data() 中重构推送逻辑：

【优化1】差分推送
- 维护 _last_push_state: dict[str, dict]，存储上次推送的完整数据
- 每次只推送变化的字段（价格变化、成交量变化）
- 压缩ratio = 变化字段数/总字段数，若<0.1不推送
- 减少带宽消耗约60%

【优化2】优先级推送
- 持仓股票：每3秒推送一次
- 自选股：每5秒推送一次
- 指数数据：每5秒推送一次
- 普通订阅：每10秒推送一次

【优化3】推送消息格式优化
新消息格式：
{
    "type": "quote_update",  // quote_update | index_update | signal | alert
    "ts": 1234567890.123,   // 时间戳
    "data": {
        "quotes": {...},    // 只包含变化的字段
        "indices": {...},
    },
    "seq": 12345            // 序列号，用于客户端检测丢包
}

【优化4】新增消息类型
- type="signal"：策略信号实时推送
  当策略产生新信号时，主动推送给订阅了该股票的客户端
  data: {symbol, strategy, signal_type, score, price}
  
- type="alert"：价格预警
  用户可设置 {symbol, price_above/below, pct_change_above}
  触发时推送 type="alert"
  API: POST /watchlist/alert/add?symbol=&alert_type=price_above&value=100
  
- type="market_event"：重要市场事件
  涨停/跌停/成交量异常放大(>3x均量)/北向资金大额买入
```

---

## 四、前端全面重构（frontend/src）

### 4.1 🔴 Dashboard.vue 专业金融终端界面

```
目标文件：frontend/src/views/Dashboard.vue
完全重写，参考彭博终端/Wind资讯的专业布局

新布局（使用 CSS Grid）：
┌─────────────────────────────────────────────────────────┐
│ 顶部状态栏：实时时间 | 市场状态 | 北向资金 | 温度计      │
├──────────┬──────────┬──────────┬───────────────────────┤
│ 上证指数  │ 深证成指 │ 创业板   │                       │
│ 大图表   │ 迷你图   │ 迷你图   │   自选股快速面板       │
├──────────┴──────────┴──────────┤   (实时价格+涨跌幅)   │
│ 港股恒指 │ 恒生科技 │ 道琼斯   │                       │
│ 纳斯达克 │ 标普500  │ ....     │                       │
├───────────────────────────────┬┴───────────────────────┤
│ 市场热力图（行业板块）         │ 今日信号               │
│ 颜色深浅表示涨跌幅             │ 策略产生的买卖信号       │
│ 面积表示成交额                 │ 时间+标的+策略+得分     │
├───────────────────────────────┼────────────────────────┤
│ 龙虎榜/涨停板/异动股          │ 账户实时盈亏           │
└───────────────────────────────┴────────────────────────┘

具体实现要求：

1. 市场指数卡片（IndexCard 组件）：
   - 用 echarts 迷你折线图展示当日分时走势
   - 数字变化时有动画（上涨红色上移，下跌绿色下移）
   - 卡片边框颜色随涨跌动态变化（渐变辉光效果）
   - 悬停时展示：52周高低、PE、成交量

2. 市场热力图（HeatmapPanel 组件）：
   - 使用 echarts treemap 类型
   - 行业分类：银行/券商/科技/医药/消费/能源/地产/周期
   - 颜色：涨幅>3%深红 | 1-3%浅红 | 0~1%淡红 | 0~-1%淡绿 | -1~-3%浅绿 | <-3%深绿
   - 面积：按各行业总成交额加权
   - 点击行业块 → 展开显示该行业TOP5股票

3. 实时信号流（SignalFeed 组件）：
   - 垂直滚动列表，新信号从顶部插入
   - 每条信号：时间 | 股票代码+名称 | 策略名 | 信号类型 | 得分
   - 买入信号左边红色竖条，卖出信号绿色竖条
   - 点击信号 → 跳转股票详情

4. 北向资金仪表盘（NorthboundGauge 组件）：
   - 圆弧仪表盘，今日净流入/净流出
   - 流入为正(红色)，流出为负(绿色)
   - 下方小字：沪股通 + 深股通 分开显示

5. 整体动效要求：
   - 数字更新使用 countUp.js 风格的滚动效果（手写，不引入库）
   - 卡片加载使用 stagger 动画（已有 CSS class）
   - 背景添加极细的网格线（1px rgba(255,255,255,0.02)）
   - 夜间金融数据流背景（可选）：用 canvas 绘制竖向流动的数字流
```

### 4.2 🔴 StockDetail.vue 完整K线图和分析页

```
目标文件：frontend/src/views/StockDetail.vue
完全重写为专业股票详情页

布局：
┌─────────────────────────────────────────────────────┐
│ 股票头部：代码 名称 市场 | 价格 涨跌 涨跌幅 | 操作按钮 │
├─────────────────────────────────────────────────────┤
│ 价格指标行：开/高/低/昨收/量/额/换手 振幅/5日均量比  │
├──────────────────────────────────┬──────────────────┤
│                                  │ 深度面板          │
│  主图：K线 + 成交量               │ (侧边可折叠)      │
│  支持周期切换：日/周/月/年        │ - 基本面数据      │
│  支持复权切换：不复权/前复权      │ - PE/PB/ROE      │
│  叠加均线：5/10/20/60/120        │ - 资金流向        │
│  叠加布林带、VWAP               │ - 北向持仓        │
│                                  │ - 机构评级        │
│  副图1（可切换）：MACD/KDJ/RSI   │                  │
│  副图2（可切换）：成交量/OBV/CMF  │ - AI分析摘要     │
├──────────────────────────────────┤                  │
│ 信号标注区：买卖信号箭头叠加在K线上 │                  │
├──────────────────────────────────┴──────────────────┤
│ Tabs: [行情] [技术指标] [财务] [回测] [相关股票]       │
└─────────────────────────────────────────────────────┘

具体技术要求：

1. K线图（使用 echarts）：
   使用 echarts candlestick 类型，实现以下功能：
   
   a) 初始化配置：
   const chartOption = {
     animation: false,  // 禁用动画提升性能
     backgroundColor: 'transparent',
     grid: [{top:30, bottom:120}, {top:'65%', bottom:50}],
     xAxis: [{type:'category', scale:true, boundaryGap:false,
              splitLine:{show:false}},
              {gridIndex:1, type:'category', scale:true}],
     yAxis: [{scale:true, splitNumber:4,
              axisLabel:{formatter: v => v.toFixed(2)}},
              {gridIndex:1, scale:true, splitNumber:2}],
     dataZoom: [{type:'inside', xAxisIndex:[0,1], start:70, end:100},
                {show:true, xAxisIndex:[0,1], type:'slider', height:20, bottom:0}],
     tooltip: {trigger:'axis', axisPointer:{type:'cross'},
               formatter: customTooltipFormatter},
     series: [
       {name:'K线', type:'candlestick', itemStyle:{
         color:'#f43f5e', color0:'#34d399',
         borderColor:'#f43f5e', borderColor0:'#34d399'}},
       {name:'MA5', type:'line', smooth:true, lineStyle:{width:1}},
       {name:'MA20', type:'line', smooth:true, lineStyle:{width:1}},
       {name:'成交量', type:'bar', xAxisIndex:1, yAxisIndex:1,
        itemStyle:{color: params => params.data[5]>=0?'#f43f5e80':'#34d39980'}},
       {name:'信号', type:'scatter', symbol:'arrow', symbolSize:14}
     ]
   }
   
   b) 买卖信号叠加：
   在 series 中添加 scatter 系列，buy用红色上箭头，sell用绿色下箭头
   markPoint 展示策略名称 tooltip
   
   c) 自定义 tooltip：
   显示：日期 | OHLC | 成交量 | 成交额 | 涨跌幅
   信号处额外显示：策略名 | 信号强度 | 持仓建议
   
   d) 技术指标叠加：
   支持动态添加/删除：BOLL带（3条线）、VWAP、ICHIMOKU云
   各指标有独立的颜色和透明度配置

2. 技术指标Tab（IndicatorPanel 组件）：
   分为5个可折叠区块：
   - 趋势类：MA/EMA/MACD信号/SuperTrend方向
   - 震荡类：RSI(6/12/24) 三线图 | KDJ三线图
   - 成交量：OBV趋势 | CMF资金流 | 量比
   - 波动率：ATR | 布林带宽度 | 历史波动率
   - 综合评分：雷达图展示6个维度得分（趋势/动量/成交量/波动/支撑阻力/形态）

3. 回测Tab（QuickBacktest 组件）：
   内嵌轻量版回测面板：
   - 选择策略（下拉）
   - 时间范围（快捷：1月/3月/6月/1年/3年/全部）
   - 一键运行，结果在同页面展示（不跳转）
   - 显示：收益曲线 | 关键指标卡片 | 交易记录列表

4. 交易面板优化：
   - 显示当前持仓（如有）
   - 价格输入框：实时获取买一/卖一价填充
   - 金额预估：自动计算所需资金、手续费
   - T+1提示：若今日已买入，卖出按钮置灰并提示
   - 止损/止盈设置（可选，默认折叠）
```

### 4.3 🔴 Strategy.vue 专业回测工作台

```
目标文件：frontend/src/views/Strategy.vue
完全重写为专业回测工作台

布局：三栏式
左栏（300px）：参数配置
中栏（弹性）：结果展示
右栏（280px，可折叠）：历史记录

左栏配置面板：
1. 策略选择：
   - 分组显示：【趋势策略】【均值回归】【多因子】【自适应】
   - 选中策略显示简要说明和适用市场
   
2. 回测标的：
   - 股票代码输入（带搜索联想）
   - 快捷预设：沪深300成分股随机 | 我的自选股 | 指数

3. 时间范围：
   - 快捷按钮：1年/2年/3年/5年/最大
   - 自定义日期范围选择器

4. 高级参数（折叠面板）：
   - 初始资金（滑块：10万-1000万）
   - 手续费率（默认0.02%，可调）
   - 是否启用蒙特卡洛（开关+模拟次数）
   - 是否启用参数优化（开关）

5. 运行按钮 + 进度条（模拟运行时间）

中栏结果展示（Tabs）：
Tab1 [概览]：
  - 顶部4个大指标卡：年化收益 | 最大回撤 | 夏普比率 | 胜率
  - 第二行4个小指标：总收益 | 盈亏比 | 交易次数 | 平均持仓天数
  - 收益曲线（策略 vs 基准双线）+ 回撤曲线（下方叠加）
  - 年度/月度收益热力图（日历热力图）

Tab2 [交易明细]：
  - 表格：日期 | 方向 | 价格 | 股数 | 金额 | 手续费 | 盈亏 | 策略原因
  - 支持按盈亏排序、导出CSV
  - 每行悬停显示：持仓期间K线缩略图

Tab3 [风险分析]：
  - 收益分布直方图（正态分布拟合）
  - 回撤分析：最大回撤区间高亮在收益曲线上
  - 月度收益热力图
  - 滚动夏普比率图（60日滚动窗口）
  - VaR/CVaR可视化

Tab4 [蒙特卡洛]（仅启用时显示）：
  - 1000条模拟路径（半透明浅色）+ 实际路径（高亮）
  - 置信区间带（5th~95th）
  - 最终净值分布柱状图

Tab5 [参数优化]（仅启用时显示）：
  - 2D热力图：X轴/Y轴分别是两个最重要参数
  - 颜色表示夏普比率
  - 最优参数标星，一键应用

右栏历史记录：
  - 按时间倒序列出历史回测
  - 每条：策略名+股票+日期范围+夏普 | 一键重新运行
  - 支持对比选中的两条记录
```

### 4.4 🟠 新增实时行情页面（Market.vue 重写）

```
目标文件：frontend/src/views/Market.vue
完全重写为专业行情页

布局：左侧过滤器 + 主列表 + 右侧迷你图

功能要求：
1. 多市场Tab + 搜索过滤
2. 支持列排序（点击表头）：按代码/名称/价格/涨跌幅/成交量/成交额排序
3. 表格列可选择显示/隐藏
4. 实时更新：WebSocket数据驱动，变化的格子闪烁一下
5. 自选股标记（★图标）
6. 行情表格虚拟滚动（@tanstack/virtual 或手写）：支持>5000只股票不卡顿

板块/行业Tab：
- 行业涨跌幅排名（水平条形图）
- 点击行业 → 过滤显示该行业股票

量价异动Tab：
- 成交量放大>3倍
- 涨停/跌停
- 突破20日高低点
- 实时更新（60秒刷新）
```

### 4.5 🟠 全局组件库建设

```
新建文件：frontend/src/components/

【BaseChart.vue】基础ECharts封装组件：
props: {option: Object, height: String, loading: Boolean}
- 自动resize（ResizeObserver）
- 主题统一：复用 CSS 变量（bg/text/border颜色）
- loading骨架屏（不依赖ECharts loading）
- 销毁时正确dispose

【PriceTag.vue】价格+涨跌幅展示：
props: {price, change, changePct, size: 'sm|md|lg'}
- 红绿颜色自动判断
- 数字变化动画
- 支持加载骨架

【SparkLine.vue】迷你趋势图（纯SVG，无需ECharts）：
props: {data: number[], color, height}
- 极简SVG折线
- 根据涨跌自动选红/绿

【SignalBadge.vue】信号标签：
props: {signal: 'strong_buy|buy|neutral|sell|strong_sell', score}
- 对应颜色和文字
- 强烈信号有脉冲动画

【MetricCard.vue】指标卡片：
props: {label, value, unit, change, tooltip, loading}
- 统一样式
- 支持tooltip

【DataTable.vue】数据表格：
props: {columns, data, sortable, loading, rowClick}
- 支持排序
- 虚拟滚动
- 列宽可调

【LoadingOverlay.vue】加载覆盖层：
- 半透明遮罩
- 中间旋转图标（纯CSS）
- 支持文字提示

【ToastNotification.vue】消息提示：
- 全局单例（通过 provide/inject）
- success/warning/error/info 四种类型
- 自动消失（3秒），支持手动关闭
- 右上角堆叠显示

使用方式：
// main.ts 中注册全局组件
import { createApp } from 'vue'
import App from './App.vue'
import { registerGlobalComponents } from './components'
const app = createApp(App)
registerGlobalComponents(app)
```

### 4.6 🟠 状态管理升级（Pinia）

```
新建文件：frontend/src/stores/

在 package.json 中添加依赖：pinia@^2.1.0

【market.store.ts】市场数据Store：
import { defineStore } from 'pinia'
export const useMarketStore = defineStore('market', {
  state: () => ({
    overview: null,
    status: {},
    lastUpdate: 0,
    isLoading: false,
  }),
  getters: {
    cnIndices: (state) => state.overview?.cn_indices ?? {},
    temperature: (state) => state.overview?.temperature ?? 50,
    isMarketOpen: (state) => Object.values(state.status).some(s => s.is_open),
  },
  actions: {
    async fetchOverview() { ... },
    startAutoRefresh(intervalMs = 5000) { ... },
    stopAutoRefresh() { ... },
  }
})

【watchlist.store.ts】自选股Store：
state: { symbols, quotes, loading }
actions: fetch, add, remove, reorder（支持拖拽排序）

【portfolio.store.ts】持仓Store：
state: { account, positions, orders, history }
actions: fetchAccount, executeBuy, executeSell, refreshPrices

【websocket.store.ts】WebSocket管理Store：
state: { connected, subscriptions, lastMessage }
actions: connect, disconnect, subscribe, unsubscribe
- 自动重连（指数退避：1s→2s→4s→8s，最大30s）
- 心跳检测（每30秒发ping，10秒无pong则重连）
- 消息队列：断线期间缓存，重连后批量处理

【backtest.store.ts】回测Store：
state: { results, history, running, progress }
actions: runBacktest, cancelBacktest, loadHistory, compare
```

---

## 五、性能优化专项

### 5.1 🔴 后端性能优化

```
【优化1】异步化改造审计
目标文件：所有 core/*.py

执行以下审计和改造：
1. 找出所有 time.sleep() → 替换为 await asyncio.sleep()（仅在async函数中）
2. 找出所有同步 requests.get() → 替换为 await async_http_get()
3. 找出所有 pd.read_csv() 等IO操作 → 用 asyncio.to_thread() 包装
4. 检查 BacktestEngine.run() 是否在异步请求路径中被同步调用
   → 如果是，用 await asyncio.to_thread(engine.run, strategy, df) 改造

【优化2】计算热路径优化
目标文件：core/indicators.py, core/adaptive_strategy.py

1. 在 TechnicalIndicators.compute_all() 中加入 LRU 缓存：
   - 缓存键：(symbol, period, last_date, len(df))
   - 缓存大小：500条，TTL=30秒
   - 已有实现，检查是否正确命中

2. 在 classify_market_regime() 中优化：
   - 预计算全部日期的 ADX/ATR（已做），但避免重复计算
   - 用 np.vectorize 或直接向量化替换 Python 循环
   - 目标：1000条数据 < 50ms

3. 在 AdaptiveStrategyEngine._precompute_scores() 中：
   - 增加进度追踪（每处理100个bar记录一次）
   - 使用 concurrent.futures.ThreadPoolExecutor 并发计算不同策略的分数
   - 注意：pandas/numpy 在多线程下不完全线程安全，加 .copy() 保护

【优化3】API响应缓存
目标文件：api/routes.py

为高频只读接口添加内存缓存（用 _realtime_cache）：

from functools import wraps
import time

def cache_response(ttl_seconds: int):
    """API响应缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            # 生成缓存key
            cache_key = f"api_{func.__name__}_{args}_{sorted(kwargs.items())}"
            cached = _realtime_cache.get(cache_key)
            if cached:
                return cached
            result = await func(request, *args, **kwargs)
            _realtime_cache.set(cache_key, result, ttl=ttl_seconds)
            return result
        return wrapper
    return decorator

应用到以下路由：
- /market/overview: TTL=5秒
- /market/status: TTL=60秒
- /stock/fundamentals/{symbol}: TTL=3600秒
- /search: TTL=300秒

【优化4】数据库查询优化
目标文件：core/database.py

1. 在 load_kline_rows() 中增加 LIMIT 参数：
   - 短期分析（<1年）：LIMIT 300
   - 中期分析（1-3年）：LIMIT 800
   - 长期/全量：不加LIMIT

2. 添加复合索引：
   CREATE INDEX IF NOT EXISTS idx_kline_composite 
   ON kline(symbol, market, kline_type, adjust, date DESC);
   
   CREATE INDEX IF NOT EXISTS idx_config_key ON config(key);

3. 启用 WAL 模式的检查点配置：
   conn.execute("PRAGMA wal_autocheckpoint=1000")

【优化5】进程级别优化
目标文件：main.py

1. 启动时预热 CPU：
   import gc
   gc.set_threshold(700, 10, 10)  # 优化GC频率

2. 为 uvicorn 配置更优参数：
   uvicorn.run(
       app, host="0.0.0.0", port=PORT,
       log_level="warning", workers=1,
       loop="uvloop", http="httptools",
       limit_concurrency=200,
       timeout_keep_alive=30,
       # 关键：禁用 access_log 节省IO
       access_log=False,
   )
```

### 5.2 🟠 前端性能优化

```
目标文件：frontend/src/

【优化1】路由懒加载
在 router/index.ts 中：
const Dashboard = () => import('../views/Dashboard.vue')
const Strategy = () => import('../views/Strategy.vue')
// 所有路由组件改为动态import

【优化2】ECharts按需引入
新建 frontend/src/lib/echarts.ts：
import * as echarts from 'echarts/core'
import { CandlestickChart, LineChart, BarChart, ScatterChart, HeatmapChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, DataZoomComponent, 
         LegendComponent, MarkPointComponent, MarkLineComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
echarts.use([CandlestickChart, LineChart, BarChart, ScatterChart, HeatmapChart,
             GridComponent, TooltipComponent, DataZoomComponent,
             LegendComponent, MarkPointComponent, MarkLineComponent, CanvasRenderer])
export default echarts

【优化3】虚拟列表
对市场行情页的大量股票列表，实现简单虚拟滚动：
// VirtualList.vue 组件
// 只渲染可视区域 + 上下缓冲区各5条
// 监听 scroll 事件更新可视范围
// 容器高度固定，子项高度固定（44px）

【优化4】WebWorker计算卸载
将以下计算移入 WebWorker（frontend/src/workers/）：
- indicator.worker.ts：计算本地技术指标（MA/MACD等）
- 使用 Comlink 简化通信（或手写 postMessage）

【优化5】图片和资源优化
在 vite.config.ts 中：
export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: '../static',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['vue', 'vue-router', 'pinia'],
          'echarts': ['echarts'],
          'utils': ['axios'],
        }
      }
    },
    minify: 'terser',
    terserOptions: { compress: { drop_console: true } },
  },
  server: {
    port: 5173,
    proxy: { '/api': { target: 'http://localhost:8080', changeOrigin: true } }
  }
})
```

---

## 六、系统健壮性

### 6.1 🔴 错误处理和容错机制

```
【升级1】全局异常处理中间件
目标文件：main.py

from fastapi import Request
from fastapi.responses import JSONResponse
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "服务器内部错误，请稍后重试", "error_type": type(exc).__name__}
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"success": False, "error": str(exc)})

【升级2】断路器模式
目标文件：core/data_fetcher.py

class CircuitBreaker:
    """
    防止级联失败的断路器
    状态：CLOSED（正常）| OPEN（断开）| HALF_OPEN（试探）
    """
    def __init__(self, failure_threshold=5, timeout=60, half_open_calls=2):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.state = "CLOSED"
        self.last_failure_time = 0
        self.half_open_calls = 0
        self.half_open_max = half_open_calls
    
    async def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                self.half_open_calls = 0
            else:
                raise Exception(f"Circuit breaker OPEN for {func.__name__}")
        
        try:
            result = await func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.half_open_calls += 1
                if self.half_open_calls >= self.half_open_max:
                    self.state = "CLOSED"
                    self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(f"Circuit breaker OPENED for {func.__name__}")
            raise

为每个数据源维护独立断路器：
self._circuit_breakers = {
    "tencent": CircuitBreaker(failure_threshold=5, timeout=30),
    "eastmoney": CircuitBreaker(failure_threshold=5, timeout=30),
    "akshare": CircuitBreaker(failure_threshold=3, timeout=120),
}

【升级3】交易安全保护
目标文件：core/simulated_trading.py

在 execute_buy() 和 execute_sell() 中增加：
1. 幂等性检查：维护 _order_ids: set[str]，防止重复下单
2. 并发锁：self._trade_lock = threading.Lock()，防止并发修改持仓
3. 余额一致性检查：交易后验证 cash >= 0，否则回滚
4. 审计日志：每笔交易记录到 audit_log 文件（不仅是数据库）

【升级4】数据验证层
目标文件：core/data_fetcher.py

新增 validate_realtime_data(data: dict, symbol: str) -> bool：
- 价格必须 > 0
- 涨跌幅必须在 -20% ~ +20% 之间（A股）
- 成交量必须 >= 0
- timestamp 必须是今天
- 若验证失败，返回 False 并记录警告

新增 validate_kline_data(df: pd.DataFrame, symbol: str) -> bool：
- 至少有10行数据
- date列存在且格式正确
- 价格列无负值
- 日期单调递增

【升级5】健康检查端点
目标文件：main.py 或 api/routes.py

@app.get("/health")
async def health_check(request: Request):
    """详细健康状态检查"""
    checks = {}
    
    # 数据库连接
    try:
        db = get_db()
        db.fetchone("SELECT 1")
        checks["database"] = {"status": "ok"}
    except Exception as e:
        checks["database"] = {"status": "error", "message": str(e)}
    
    # 数据源连接
    try:
        session = await get_aiohttp_session()
        checks["network"] = {"status": "ok"}
    except Exception as e:
        checks["network"] = {"status": "error"}
    
    # 内存使用
    import psutil
    process = psutil.Process()
    mem = process.memory_info()
    checks["memory"] = {
        "rss_mb": round(mem.rss / 1024**2, 1),
        "status": "ok" if mem.rss < 512*1024*1024 else "warning"
    }
    
    # 缓存状态
    checks["cache"] = {
        "realtime_entries": len(_realtime_cache),
        "history_entries": len(_history_cache),
    }
    
    uptime = time.time() - request.app.state.start_time
    all_ok = all(v.get("status") == "ok" for v in checks.values())
    
    return {
        "status": "healthy" if all_ok else "degraded",
        "uptime_seconds": round(uptime),
        "checks": checks,
        "version": "3.0.0",
    }
```

### 6.2 🟡 监控和可观测性

```
目标文件：core/logger.py + 新建 core/metrics.py

新建 core/metrics.py：
import time
import threading
from collections import defaultdict, deque

class MetricsCollector:
    """轻量级指标收集器"""
    
    def __init__(self):
        self._counters: dict[str, int] = defaultdict(int)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._lock = threading.Lock()
    
    def increment(self, name: str, value: int = 1, tags: dict = None) -> None:
        with self._lock:
            key = self._make_key(name, tags)
            self._counters[key] += value
    
    def gauge(self, name: str, value: float, tags: dict = None) -> None:
        with self._lock:
            key = self._make_key(name, tags)
            self._gauges[key] = value
    
    def histogram(self, name: str, value: float, tags: dict = None) -> None:
        with self._lock:
            key = self._make_key(name, tags)
            self._histograms[key].append(value)
    
    def timer(self, name: str, tags: dict = None):
        """上下文管理器：自动记录耗时"""
        return _TimerContext(self, name, tags)
    
    def get_summary(self) -> dict:
        with self._lock:
            result = {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {}
            }
            for k, v in self._histograms.items():
                if v:
                    arr = sorted(v)
                    n = len(arr)
                    result["histograms"][k] = {
                        "count": n,
                        "mean": sum(arr)/n,
                        "p50": arr[n//2],
                        "p95": arr[int(n*0.95)],
                        "p99": arr[int(n*0.99)],
                    }
            return result
    
    def _make_key(self, name: str, tags: dict = None) -> str:
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}{{{tag_str}}}"

_metrics = MetricsCollector()

def get_metrics() -> MetricsCollector:
    return _metrics

在以下关键位置添加指标收集：
1. data_fetcher.py: 数据源请求次数、延迟、成功率
   _metrics.increment("data_fetch_total", tags={"source": source_name, "status": "success"})
   _metrics.histogram("data_fetch_latency_ms", latency*1000, tags={"source": source_name})

2. backtest.py: 回测次数、耗时、结果分布
   _metrics.increment("backtest_total", tags={"strategy": name})
   _metrics.histogram("backtest_duration_ms", duration*1000)

3. routes.py: API请求次数、延迟
   # 用中间件统一记录

新增 API 接口：
@app.get("/metrics")
async def get_metrics_endpoint():
    return _metrics.get_summary()
```

---

## 七、用户体验专项

### 7.1 🟠 交互体验优化

```
【优化1】全局快捷键
目标文件：frontend/src/App.vue 或新建 useKeyboardShortcuts.ts

实现以下快捷键（composable）：
- / 或 Ctrl+K：聚焦搜索框
- Esc：关闭任何打开的弹窗/下拉
- 1-6数字键：切换导航（需先按住Cmd/Ctrl）
- R：刷新当前页面数据（不刷新浏览器）
- B：在股票详情页，快速打开买入面板

【优化2】主题系统
目标文件：frontend/src/App.vue + frontend/src/styles/

实现暗色（默认）和亮色主题切换：
// themes.ts
export const darkTheme = {
  '--bg-primary': '#06060a',
  '--bg-secondary': '#0e0e14',
  // ... 所有变量
}

export const lightTheme = {
  '--bg-primary': '#f8f9fa',
  '--bg-secondary': '#ffffff',
  '--text-primary': '#1a1a2e',
  // ... 
}

// 保存到 localStorage
// 在 <html> 元素上切换 data-theme 属性
// CSS变量跟随改变

【优化3】数据加载骨架屏
对所有异步加载数据的组件，添加骨架屏：
- 卡片骨架：灰色块 + shimmer动画（已有.skeleton CSS class）
- 表格骨架：5行×N列的灰色条
- 图表骨架：纯色矩形 + "加载中" 文字

使用 v-if="!loading" / v-else 切换

【优化4】空状态设计
每个列表/图表区域都要有精心设计的空状态：
- 持仓为空：图标 + "开始你的第一笔交易" + 引导按钮
- 自选股为空：图标 + "添加感兴趣的股票" + 快捷添加
- 回测未运行：图标 + 步骤引导（1.选策略 2.选股票 3.运行）
- 搜索无结果：图标 + "未找到" + 建议（检查代码/尝试中文名）

【优化5】移动端响应式支持
在现有 CSS 中添加断点（@media max-width: 768px）：
- Sidebar 在移动端变为底部Tab Bar
- 表格在移动端变为卡片列表
- K线图高度自适应
- 交易面板变为全屏抽屉
```

### 7.2 🟡 智能功能

```
【功能1】AI辅助分析摘要
目标文件：新建 api/ai_routes.py（可选，用本地规则代替真实AI）

@router.get("/stock/ai_summary/{symbol}")
async def get_ai_summary(request, symbol, period="1y"):
    """
    基于规则的智能分析摘要（不调用外部AI API，纯本地规则引擎）：
    
    1. 收集技术指标数据
    2. 基于规则生成自然语言描述：
       - "过去20日，{symbol}呈现[上升/下降/震荡]趋势，
          累计涨幅{pct:.1f}%，[高于/低于]同期沪深300指数{alpha:.1f}个百分点"
       - "当前RSI={rsi:.0f}，处于[超买/超卖/中性]区域"
       - "MACD于{date}出现[金叉/死叉]信号，此后价格[上涨/下跌]{follow_pct:.1f}%"
       - "成交量近5日较前5日[放大/萎缩]{vol_ratio:.1f}倍，[量价]配合[正常/背离]"
    3. 综合评分和操作建议（买入/持有/减仓/观望）
    4. 风险提示：波动率处于历史{percentile:.0f}%分位
    """

【功能2】策略信号推送通知
目标文件：frontend/src/stores/websocket.store.ts + frontend/src/App.vue

当 WebSocket 收到 type="signal" 消息时：
- 使用 Web Notifications API（需用户授权）推送系统通知
- 同时在页面右上角显示 ToastNotification
- 通知内容："{策略名} 在 {股票名称} 产生{买入/卖出}信号 | 当前价格: {price}"

【功能3】价格预警
前端新增 AlertManager 组件（在 Watchlist 页面和 StockDetail 页面）：
- 设置涨跌幅预警（如：涨超5%通知）
- 设置绝对价格预警（如：跌破100元通知）
- 本地 localStorage 保存预警设置
- WebSocket 接收行情后本地检测（不依赖后端推送）

【功能4】自动化报告生成
@router.get("/report/weekly")
async def get_weekly_report(request):
    """
    生成本周量化报告（纯文本+结构化数据）：
    - 本周持仓盈亏汇总
    - 触发的策略信号统计
    - 自选股涨跌排名
    - 市场回顾（指数表现）
    - 下周关注标的（基于策略扫描）
    """
```

---

## 八、执行计划和优先级

### Phase 1（核心功能，先做这些）
```
执行顺序：
1. [P1] 策略层：添加5个最重要的新策略（Ichimoku/VWAP/OrderFlow/RegimeSwitching/Fractal）
2. [P1] 数据层：添加东方财富数据源 + 数据质量检查
3. [P1] 回测层：完善绩效指标（Omega/Tail Ratio/MAE/MFE/Expectancy）
4. [P1] API层：添加 /stock/analysis/{symbol} 和 /market/heatmap 接口
5. [P1] 前端：重写 Dashboard.vue（热力图+信号流+专业布局）
6. [P1] 前端：重写 StockDetail.vue（完整K线图+技术分析Tab）
7. [P1] 前端：重写 Strategy.vue（专业回测工作台）
8. [P1] 健壮性：全局异常处理 + 断路器 + 健康检查端点
```

### Phase 2（进阶功能）
```
9.  [P2] 策略层：剩余5个策略（Wyckoff/Elliott/Copula/Quantile/Microstructure）
10. [P2] 策略层：自适应引擎强化学习改造
11. [P2] 前端：Market.vue 重写（虚拟滚动+实时更新）
12. [P2] 前端：Pinia状态管理 + WebSocket Store
13. [P2] 性能：后端异步化审计 + API缓存装饰器
14. [P2] 性能：前端代码分割 + ECharts按需引入
15. [P2] 数据库：新增数据表 + 连接池优化
```

### Phase 3（体验打磨）
```
16. [P3] 全局组件库（BaseChart/PriceTag/MetricCard等）
17. [P3] 主题系统（暗色/亮色切换）
18. [P3] 快捷键系统
19. [P3] AI分析摘要（规则引擎）
20. [P3] 监控指标收集（MetricsCollector）
21. [P3] 蒙特卡洛分析 + 参数优化可视化
22. [P3] 移动端响应式
```

---

## 九、代码质量守则

### 每次提交前自检清单
```
□ 所有新函数：边界检查（None/空/NaN）
□ 所有金融计算：除零保护
□ 所有异步函数：try/except + 日志
□ 所有数据库操作：参数化查询（防注入）
□ 所有新API：返回统一格式 {success, data, error}
□ 前端新组件：loading/error/empty 三态处理
□ 前端API调用：try/catch + 用户提示
□ 性能敏感代码：加计时日志 logger.debug(f"xxx took {t:.0f}ms")
□ 新增依赖：更新 requirements.txt 或 package.json
□ 不破坏现有API接口签名
```

### 文件修改原则
```
1. 修改现有文件：先 read → 理解 → 最小化修改
2. 新增功能：优先新增函数/类，不改动已有代码
3. 重构：只在被要求时进行，附带完整测试逻辑说明
4. 前端组件：尽量复用现有 CSS 变量，不内联颜色值
5. 配置值：抽取到文件顶部常量，不散落在代码中间
```

---

## 十、参考实现样例（供Claude Code理解风格）

### 后端策略示例（严格遵循此风格）
```python
class IchimokuCloudStrategy(BaseStrategy):
    """一目均衡表策略 - 识别趋势确认信号"""
    
    def __init__(self, tenkan_period: int = 9, kijun_period: int = 26, senkou_b_period: int = 52):
        super().__init__()
        self._tenkan = tenkan_period
        self._kijun = kijun_period
        self._senkou_b = senkou_b_period
    
    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        n = self._senkou_b + 2
        if len(df) < n:
            return TradeSignal(SignalType.HOLD)
        
        h = df["high"].astype(float)
        l = df["low"].astype(float)
        c = df["close"].astype(float)
        
        def mid_line(high, low, p):
            return (high.rolling(p).max() + low.rolling(p).min()) / 2
        
        tenkan = mid_line(h, l, self._tenkan)
        kijun = mid_line(h, l, self._kijun)
        senkou_a = ((tenkan + kijun) / 2).shift(self._kijun)
        senkou_b = mid_line(h, l, self._senkou_b).shift(self._kijun)
        
        last_c = c.iloc[-1]
        cloud_top = max(senkou_a.iloc[-1] or 0, senkou_b.iloc[-1] or 0)
        cloud_bot = min(senkou_a.iloc[-1] or 0, senkou_b.iloc[-1] or 0)
        
        # 转换线上穿基准线（金叉）
        tk_cross_up = (tenkan.iloc[-1] > kijun.iloc[-1] and 
                       tenkan.iloc[-2] <= kijun.iloc[-2])
        
        price_above_cloud = last_c > cloud_top
        price_below_cloud = last_c < cloud_bot
        
        if tk_cross_up and price_above_cloud:
            return TradeSignal(SignalType.BUY, 0.85, "一目均衡金叉+价格在云层上方")
        if tk_cross_up:
            return TradeSignal(SignalType.BUY, 0.55, "一目均衡金叉")
        if price_below_cloud and tenkan.iloc[-1] < kijun.iloc[-1]:
            return TradeSignal(SignalType.SELL, 0.75, "一目均衡空头排列")
        if tenkan.iloc[-1] > kijun.iloc[-1] and price_above_cloud:
            return TradeSignal(SignalType.BUY, 0.35, "一目均衡多头持续")
        
        return TradeSignal(SignalType.HOLD)
    
    @staticmethod
    def get_param_space() -> dict:
        return {
            "tenkan_period": {"min": 7, "max": 15, "step": 1},
            "kijun_period": {"min": 20, "max": 32, "step": 2},
        }
```

### 前端组件示例（严格遵循此风格）
```vue
<!-- MetricCard.vue - 复用性强的指标卡片 -->
<template>
  <div class="metric-card" :class="{ loading }">
    <div v-if="loading" class="skeleton" style="height:60px;border-radius:8px"/>
    <template v-else>
      <div class="metric-label">
        {{ label }}
        <span v-if="tooltip" class="tooltip-icon" :title="tooltip">?</span>
      </div>
      <div class="metric-value" :class="valueClass">
        {{ formattedValue }}
        <span v-if="unit" class="metric-unit">{{ unit }}</span>
      </div>
      <div v-if="change !== undefined" class="metric-change" :class="changeClass">
        {{ change >= 0 ? '+' : '' }}{{ change.toFixed(2) }}%
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = withDefaults(defineProps<{
  label: string
  value: number | string
  unit?: string
  change?: number
  positive?: 'up' | 'down' | 'neutral'  // 哪个方向是"好"
  tooltip?: string
  loading?: boolean
  format?: 'number' | 'percent' | 'currency' | 'raw'
}>(), { positive: 'up', format: 'raw' })

const formattedValue = computed(() => {
  if (typeof props.value !== 'number') return props.value
  switch (props.format) {
    case 'number': return props.value.toLocaleString('zh-CN', {maximumFractionDigits: 2})
    case 'percent': return `${props.value.toFixed(2)}%`
    case 'currency': return `¥${props.value.toLocaleString('zh-CN', {minimumFractionDigits: 2})}`
    default: return String(props.value)
  }
})

const valueClass = computed(() => {
  if (typeof props.value !== 'number' || props.positive === 'neutral') return ''
  if (props.positive === 'up') return props.value >= 0 ? 'text-up' : 'text-down'
  return props.value >= 0 ? 'text-down' : 'text-up'
})

const changeClass = computed(() => {
  if (props.change === undefined) return ''
  return props.change >= 0 ? 'text-up' : 'text-down'
})
</script>
```

---

## 附录：关键依赖说明

```
后端新增依赖（如需要）：
- psutil>=5.9.0              # 内存/CPU监控
- scipy>=1.11.0              # 已有，用于统计计算
- numpy>=1.24.0              # 已有

前端新增依赖（如需要）：
- pinia@^2.1.0               # 状态管理（替代 provide/inject 散装方案）

特别说明：
1. 不引入 hmmlearn（纯numpy手写HMM）
2. 不引入 TA-Lib（现有纯numpy实现已足够，避免C依赖）
3. 不引入 zipline/backtrader（自研回测引擎更灵活）
4. 前端不引入 element-plus/antd（保持轻量，自定义组件）
5. 前端不引入 tailwind（保持现有 CSS 变量体系）
```

---

*提示词版本：v3.0 | 适用：Claude Code | 项目：QuantCore 量化交易系统*
*设计理念：机构级专业性 × 轻量级实现 × 极致用户体验*
