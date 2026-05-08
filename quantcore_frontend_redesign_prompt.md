# QuantCore 前端系统完整重构提示词

## 一、使命与设计哲学

你是一位顶级创意技术总监，同时精通前端工程与视觉艺术设计。你的任务是对一套量化交易系统的前端进行**彻底重构**，使其成为一件兼具工业美学与数据艺术气息的产品。

**核心设计宣言：**
> 这不是一个"好看的仪表盘"，而是一台**精密运转的数据机器**。它应当让人联想到 NASA 任务控制室、CERN 粒子加速器监控终端、路透社交易大厅——一种冷静的、压迫性的、令人敬畏的专业感。同时，它又不失艺术家对构图、节奏、对比度的敏锐直觉。

**设计风格定义：**「工业数据主义」（Industrial Data-ism）

- **瑞士网格系统**：所有元素严格对齐 8px 基准网格，布局像《苏黎世财经报》的版式设计
- **暴力排版美学**：大量使用等宽字体（monospace）作为主要内容字体，而非辅助字体
- **克制的色彩爆破**：整体极度克制（近黑、石墨、金属灰），但关键数据点用高饱和度冲击色（荧光黄、信号红、终端绿）
- **密度即美学**：信息密度是设计语言的一部分，拒绝无意义留白，每一个像素都在工作
- **机械感微交互**：悬停状态像机械卡位，动画曲线追求精密而非流畅

---

## 二、视觉设计系统（Design Tokens）

### 2.1 色彩系统

```css
:root {
  /* === 主背景色阶：建筑级深色 === */
  --bg-void: #050507;           /* 最深背景，接近纯黑 */
  --bg-base: #080810;           /* 页面基础背景 */
  --bg-plate: #0d0d1a;          /* 面板背景，略带深蓝 */
  --bg-surface: #111120;        /* 卡片表面 */
  --bg-raised: #161628;         /* 浮起层 */
  --bg-overlay: #1c1c32;        /* 弹出层 */

  /* === 网格/边框：极细但存在感强 === */
  --grid-line: rgba(255, 255, 255, 0.04);   /* 背景网格线 */
  --border-hair: rgba(255, 255, 255, 0.06); /* 发丝细线 */
  --border-dim: rgba(255, 255, 255, 0.10);  /* 低调边框 */
  --border-mid: rgba(255, 255, 255, 0.18);  /* 标准边框 */
  --border-hi: rgba(255, 255, 255, 0.28);   /* 高亮边框 */

  /* === 文字色阶：五级灰度系统 === */
  --text-primary: #f0f0f8;      /* 主文字，冷白 */
  --text-secondary: #9898b0;    /* 次要文字，蓝灰 */
  --text-tertiary: #555568;     /* 辅助文字 */
  --text-muted: #333345;        /* 极弱文字 */
  --text-inverse: #050507;      /* 反色文字 */

  /* === 信号色：冲击性，稀少使用 === */
  --signal-rise: #ff3b3b;       /* 涨（中国习惯：红涨） */
  --signal-fall: #00e676;       /* 跌（绿跌） */
  --signal-warn: #ffd600;       /* 警告/中性，荧光黄 */
  --signal-info: #2979ff;       /* 信息/蓝 */
  --signal-purple: #e040fb;     /* 特殊标注/紫 */
  --signal-teal: #1de9b6;       /* 辅助数据/青 */

  /* === 信号色低透明度变体（用于背景） === */
  --rise-bg: rgba(255, 59, 59, 0.08);
  --fall-bg: rgba(0, 230, 118, 0.08);
  --warn-bg: rgba(255, 214, 0, 0.08);
  --info-bg: rgba(41, 121, 255, 0.08);

  /* === 强调色：主题蓝，仅用于焦点/选中 === */
  --accent: #2979ff;
  --accent-muted: rgba(41, 121, 255, 0.12);

  /* === 字体 === */
  --font-mono: 'JetBrains Mono', 'SF Mono', 'Fira Code', Consolas, monospace;
  --font-sans: -apple-system, 'Helvetica Neue', 'Noto Sans SC', 'PingFang SC', sans-serif;

  /* === 间距单位：严格8px基础 === */
  --u1: 4px; --u2: 8px; --u3: 12px; --u4: 16px;
  --u5: 20px; --u6: 24px; --u8: 32px; --u10: 40px;
  --u12: 48px; --u16: 64px;

  /* === 圆角：克制使用 === */
  --r-none: 0px;
  --r-xs: 2px;   /* 最细微 */
  --r-sm: 4px;   /* 标签、徽章 */
  --r-md: 6px;   /* 卡片 */
  --r-lg: 8px;   /* 模态框 */

  /* === 布局尺寸 === */
  --sidebar-w: 52px;
  --sidebar-expanded: 200px;
  --topbar-h: 48px;

  /* === 动画曲线：机械感 === */
  --ease-mechanical: cubic-bezier(0.0, 0.0, 0.2, 1);  /* 快入慢出 */
  --ease-snap: cubic-bezier(0.4, 0, 0.6, 1);           /* 弹性感 */
  --dur-instant: 60ms;
  --dur-fast: 120ms;
  --dur-normal: 200ms;
  --dur-slow: 350ms;
}

/* 亮色主题（可选，但要与暗色同样精良） */
[data-theme="light"] {
  --bg-void: #f4f4f0;
  --bg-base: #f0f0ec;
  --bg-plate: #ebebE7;
  --bg-surface: #ffffff;
  --bg-raised: #fafaf8;
  --bg-overlay: #ffffff;
  --grid-line: rgba(0, 0, 0, 0.04);
  --border-hair: rgba(0, 0, 0, 0.06);
  --border-dim: rgba(0, 0, 0, 0.10);
  --border-mid: rgba(0, 0, 0, 0.16);
  --border-hi: rgba(0, 0, 0, 0.24);
  --text-primary: #0d0d1a;
  --text-secondary: #555568;
  --text-tertiary: #9898b0;
  --text-muted: #c0c0d0;
}
```

### 2.2 全局背景纹理系统

全页面背景必须叠加一个极细的点阵网格，使用 CSS 实现：

```css
body::before {
  content: '';
  position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background-image:
    radial-gradient(circle, rgba(255,255,255,0.03) 1px, transparent 1px);
  background-size: 24px 24px;
}
```

侧边栏和顶栏使用毛玻璃效果但加入扫描线质感：

```css
.sidebar, .topbar {
  backdrop-filter: blur(24px) brightness(0.7);
  background: rgba(8, 8, 16, 0.85);
  /* 扫描线 */
  background-image: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(255,255,255,0.012) 2px,
    rgba(255,255,255,0.012) 4px
  );
}
```

### 2.3 字体排版规则

```
数据显示（价格/涨跌/百分比）：JetBrains Mono，必须用此字体
页面大标题：--font-sans，weight 700，letter-spacing -0.04em
卡片标题：--font-sans，weight 600
表格数字列：--font-mono，tabular-nums，weight 500
标签/徽章：--font-mono，uppercase，letter-spacing 0.08em

字号层级：
  --fs-xs:   10px   /* 表格辅助，状态点 */
  --fs-sm:   12px   /* 表格主要内容 */
  --fs-base: 13px   /* 基础正文 */
  --fs-md:   15px   /* 卡片正文 */
  --fs-lg:   18px   /* 小标题 */
  --fs-xl:   24px   /* 数据大字 */
  --fs-2xl:  32px   /* 页面副标题 */
  --fs-3xl:  48px   /* 页面主标题 */
  --fs-hero: 72px   /* 核心指数数字 */
```

---

## 三、组件设计规范

### 3.1 侧边栏（Sidebar）

**设计语言**：工业控制台风格，图标与文字等宽对齐

- 宽度：收缩 52px / 展开 200px，通过鼠标悬停触发，过渡 var(--dur-normal)
- 左侧有 2px 宽的 `--border-dim` 分隔线
- 导航图标：18×18px SVG，无填充，stroke-width=1.5，颜色 `--text-tertiary`
- 激活状态：左侧 2px `--accent` 色竖线 + 背景 `--accent-muted` + 图标变 `--accent`
- 品牌区域：顶部 48px 区域，显示「QC」字样（等宽字体，加粗），展开时显示全称
- 底部显示实时时钟：`HH:MM:SS`，等宽字体，`--text-muted` 色
- **特殊设计**：每个导航项悬停时，右侧出现一条细如发丝的水平线延伸到内容区边缘（纯视觉效果，用 `::after` 伪元素实现）

### 3.2 顶栏（Topbar）

**布局**：左（市场状态） | 中（搜索入口） | 右（指数跑马灯）

- 高度固定 48px，底部 1px `--border-hair` 线
- **市场状态指示器**：`A股 ● 09:30` 格式，●为脉动动画点，开盘时为 `--signal-rise`，休市为 `--text-muted`
- **搜索框**：宽度 320px，背景 `--bg-raised`，左侧放大镜 SVG，右侧显示 `⌘K` 快捷键提示（等宽字体显示）
- **指数跑马灯**：右侧无限水平滚动动画（CSS animation），显示 `上证 ▲0.82%  深证 ▼1.23%  创业 ...`，涨跌用信号色，无需箭头图标，用 ▲▼ 字符

### 3.3 卡片系统

**三种卡片变体：**

**A. 数据板块卡（Data Panel）**
```
边框：1px var(--border-hair) 线
背景：var(--bg-surface)
左上角有2px×20px的 --accent 色"定位锚点"装饰线
标题区：padding 12px 16px，底部 1px --border-hair
标题字体：--font-mono，uppercase，12px，--text-secondary，letter-spacing 0.1em
```

**B. 指标卡（Metric Card）**
```
无边框，背景 var(--bg-plate)
顶部8px高度的彩色条纹（根据数据涨跌切换颜色）
数字：--fs-xl，--font-mono，weight 600
标签：--fs-xs，uppercase，--text-tertiary
```

**C. 悬浮操作卡（Action Card）**
```
背景 var(--bg-overlay)
1px --border-mid 边框
悬停时 border-color 变为 --accent，过渡 120ms
内部有细密的45度斜纹背景（4px间距，opacity 0.03）
```

### 3.4 数据表格

**这是系统中最重要的组件，必须精心打磨：**

```
表头：--bg-void 背景，--font-mono，10px，uppercase，letter-spacing 0.1em，--text-tertiary
行高：36px（紧凑但不挤压）
奇偶行无差异，hover 时行背景变为 rgba(255,255,255,0.025)
分隔线：1px --border-hair，仅行间，无列间线
价格列：--font-mono，tabular-nums，右对齐
名称列：--font-sans，weight 500，--text-primary
代码列：--font-mono，--accent 色，11px
数字正数：--signal-fall（绿）
数字负数：--signal-rise（红）
表格右侧保留 52px 操作列（用于自选、详情等按钮）
行点击 cursor:pointer，点击后有 50ms 的背景色闪烁反馈
```

### 3.5 K线图样式

ECharts 主题覆盖要求：

```javascript
const CHART_THEME = {
  backgroundColor: 'transparent',
  // 阳线（涨）：中空红框，无填充
  // 阴线（跌）：实心绿色
  candlestick: {
    itemStyle: {
      color: 'transparent',          // 阳线空心
      color0: '#00e676',             // 阴线填充
      borderColor: '#ff3b3b',        // 阳线边框
      borderColor0: '#00e676',       // 阴线边框
      borderWidth: 1.5,
    }
  },
  // 坐标轴：极细，几乎不可见
  categoryAxis: {
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.03)', type: 'dashed' } },
    axisLabel: { color: '#555568', fontSize: 10, fontFamily: 'JetBrains Mono' },
  },
  // Tooltip：终端风格
  tooltip: {
    backgroundColor: '#0d0d1a',
    borderColor: 'rgba(255,255,255,0.15)',
    borderWidth: 1,
    textStyle: { color: '#f0f0f8', fontSize: 11, fontFamily: 'JetBrains Mono' },
    // 格式必须包含：日期 | O H L C | 涨跌幅 | 成交量
  }
}
```

均线颜色方案（细线，1px，low opacity）：
- MA5：`rgba(255, 214, 0, 0.7)`（金黄）
- MA10：`rgba(41, 121, 255, 0.7)`（蓝）
- MA20：`rgba(224, 64, 251, 0.7)`（紫）
- MA60：`rgba(97, 97, 97, 0.6)`（灰）

买卖信号标记：
- 买入：底部向上的等边三角形，`--signal-rise` 红色填充，无描边
- 卖出：顶部向下的等边三角形，`--signal-fall` 绿色填充

### 3.6 涨跌徽章（Signal Badge）

```
买入：2px × 10px 红色竖线 + "BUY" 文字，--font-mono，9px
卖出：2px × 10px 绿色竖线 + "SELL" 文字
持仓：2px × 10px 灰色竖线 + "HOLD"
背景仅一个极低透明度色块（opacity 0.08）
```

### 3.7 搜索弹窗

```
全屏暗色遮罩（rgba(0,0,0,0.7)，backdrop-filter blur 16px）
弹窗宽 600px，最大高度 520px，居中偏上（top: 20vh）
顶部输入行：52px 高度，左侧放大镜，右侧 ESC 按钮
输入框字体：--font-mono，16px，--text-primary
结果列表：每项 44px，代码（--accent，--font-mono）| 名称 | 市场标签
市场标签：2px × 8px 色块 + 文字（A股红、港股蓝、美股紫）
悬停：背景 rgba(255,255,255,0.04)，左侧 2px 亮线
空结果：居中显示「NO RESULTS」，--font-mono，--text-muted
```

### 3.8 加载/骨架屏

```
不使用传统骨架屏动画，改用：
左上角出现一个 2px 进度条，颜色 --accent，从 0% 扩展到 100%
加载完成后，进度条向右消失，内容淡入（fadeIn 200ms）

全屏加载态：
  - 全黑背景
  - 中心显示「QC」大字（--font-mono，120px，--text-muted）
  - 下方显示当前加载项名称（12px，--font-mono）
  - 底部细进度条
```

### 3.9 Toast 通知

```
位置：右下角（不是右上角），距边缘 24px
宽度：260px
背景：--bg-overlay，1px --border-mid
左侧 3px 色条（类型对应颜色）
字体：--font-mono，12px
无图标，用纯文字「OK」「ERR」「WARN」「INFO」前缀
自动消失动画：向下平移 + 透明度归零（200ms）
```

---

## 四、页面级设计规范

### 4.1 仪表盘（Dashboard）

**布局哲学**：像彭博终端首页，信息密集但有序

**页面结构：**

```
┌─ TOPBAR ─────────────────────────────────────────────┐
├─ HERO TICKER BAR（全宽，高64px）─────────────────────┤
│  六大指数：上证 深证 创业 科创 恒指 纳指                │
│  每个指数显示：名称 | 点位（--font-mono，--fs-xl）      │
│               涨跌点 | 涨跌幅（带颜色） | 日内迷你折线  │
├─ MAIN GRID（三列：2:1:1 比例）──────────────────────-┤
│                                                        │
│  左列（主区域）：                                      │
│  ┌─ 板块热力图（Data Panel, 高240px）────────────────┐ │
│  │  网格式色块，每格4×4px最小，颜色按涨跌深浅渐变      │ │
│  │  悬停显示工具提示：板块名 | 涨跌幅 | 成交量         │ │
│  └─────────────────────────────────────────────────┘ │
│  ┌─ 市场全景（Data Panel, 高180px）─────────────────┐ │
│  │  上涨/下跌/平盘只数 | 量比 | 北向净流入 | 成交额    │ │
│  │  水平条形图显示涨跌分布                            │ │
│  └─────────────────────────────────────────────────┘ │
│                                                        │
│  中列（信号区）：                                      │
│  ┌─ 策略信号（Data Panel，可滚动）──────────────────┐ │
│  │  LATEST SIGNALS 标题（--font-mono）               │ │
│  │  每条：时间戳 | 代码 | 策略名 | BUY/SELL 标记      │ │
│  └─────────────────────────────────────────────────┘ │
│  ┌─ 异动行情（Data Panel）──────────────────────────┐ │
│  │  列表：涨幅 | 代码 | 名称 | 原因标签              │ │
│  └─────────────────────────────────────────────────┘ │
│                                                        │
│  右列（账户+自选）：                                   │
│  ┌─ 账户快照（Data Panel）──────────────────────────┐ │
│  │  总资产（大字显示，--fs-hero 缩小版）              │ │
│  │  当日盈亏（带方向符号）| 持仓数 | 收益率            │ │
│  │  迷你持仓条形图（各仓位权重）                       │ │
│  └─────────────────────────────────────────────────┘ │
│  ┌─ 自选股（Data Panel，可滚动）────────────────────┐ │
│  │  紧凑型列表：代码 | 价格 | 涨跌幅                  │ │
│  └─────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────┘
```

**HERO TICKER BAR 特殊设计：**
```
高度 64px，背景 --bg-void（最深），顶底各1px --border-dim
六个指数等宽排列，用 1px 竖线分隔
每个指数右侧有一个高16px、宽60px 的迷你折线图（SVG）
折线颜色根据当日涨跌变色
整体没有标题，数字就是内容
```

**板块热力图改进设计：**
```
采用 TreeMap 布局（基于 ECharts treemap）替代等比网格
每个板块面积=成交额权重，颜色=涨跌幅
颜色映射：
  -7% → #004d2e（深绿）
  -3% → #00e676（亮绿）
   0% → #333345（灰）
  +3% → #ff3b3b（亮红）
  +7% → #4a0000（深红）
每个块内显示板块名（白色，11px）和涨跌幅（等宽，10px）
```

### 4.2 行情页（Market）

**顶部**：Tab 栏采用横向滚动，不换行

**表格区：**
- 全高度减去顶栏和 Tab 栏，内部滚动
- 首列（代码）固定，表格横向可滚动
- 在每行右侧，实时显示一个12px宽的迷你垂直价格柱（代表当日高低价区间，实时价格作为标记点）
- 搜索框集成在表格顶部工具栏右侧（不另起页面）
- 排序点击后，列标题旁出现 ▲ 或 ▼ 符号（等宽字体），同时整个列的文字颜色加亮

**板块视图特殊设计：**
```
放弃卡片布局，改为「密度矩阵」：
  - 每个板块占一行，高48px
  - 左：3px 涨跌色竖条 | 板块名 | 领涨股标签
  - 中：水平进度条（相对最大涨幅的百分比）
  - 右：涨跌幅数字（--font-mono，--fs-lg）
  - 悬停展开：显示该板块今日成交额、主力资金净流入、前三成分股
```

### 4.3 个股详情页（Stock Detail）

**布局**：上栏（股票信息条）+ 主体（K线大图 + 右侧工具箱）+ 下方（多Tab信息区）

**股票信息条（粘性置顶，72px高）：**
```
左：股票名（--font-sans，20px，600）| 代码（--font-mono，--accent）| 市场标签
中：价格（--font-mono，--fs-hero，涨跌色）| 涨跌额 | 涨跌幅
右：开高低收量额换 （数字全部 --font-mono，11px，紧凑排列）
右最右：自选按钮（★/☆）| 买入按钮（纯色块按钮）
```

**K线图区域（占页面 55% 高度）：**
- 左上角浮动「周期选择」：1D 5D 3M 1Y 3Y 全部，--font-mono，10px
- 右上角浮动「指标选择」：MA MACD KDJ BOLL，多选徽章
- 信号标记必须精美：不使用 ECharts 默认 pin 形状，用自定义 SVG 渲染
- 图表右侧 Y 轴固定显示当前价格标签（高亮背景块）
- DataZoom 使用自定义滑块设计

**右侧工具箱（宽300px，与K线并排）：**
- 策略信号列表（最近15条，紧凑）
- 模拟交易表单（最小化，默认折叠，点击展开）
- 盘口深度（5档买卖盘，可视化条形）

**下方 Tab 区：**
Tab 设计：水平滑动下划线动画，无背景切换

---

### 4.4 策略回测页（Strategy Run）

**这是最具设计挑战性的页面：**

**左侧配置面板（宽280px，固定）：**
```
顶部：策略选择器
  - 不使用下拉菜单
  - 使用垂直滚动的策略列表，每项一行
  - 激活项：左侧 3px --accent 竖线 + 背景 --accent-muted
  - 策略名：--font-mono，12px
  - 右侧：难度标签（BASIC / PRO / EXPERT，用颜色区分）

中部：参数配置
  - 股票代码输入：--font-mono，高36px，全宽
  - 日期范围：两个日期框并列
  - 初始资金：数字输入，实时显示格式化后的大数字
  - 运行按钮：全宽，高48px，背景 --accent，等宽字体「RUN BACKTEST」

底部：历史记录（可折叠）
  - 每条：策略名 | 收益率（带颜色）| 时间戳
```

**右侧结果区：**

「等待运行」状态：
```
居中显示终端风格的 ASCII 艺术图案：

  ┌────────────────────────────────┐
  │  QUANTCORE BACKTEST ENGINE v2  │
  │  ─────────────────────────────  │
  │  SELECT STRATEGY AND RUN       │
  │  TO BEGIN ANALYSIS             │
  │                                │
  │  > _                           │
  └────────────────────────────────┘

字体 --font-mono，颜色 --text-muted
```

「运行中」状态：
```
模拟终端输出流：
[09:23:41] Loading price data for 600519...
[09:23:41] Computing indicators...
[09:23:42] Running strategy: DualMAStrategy
[09:23:42] Processing 1247 trading days...
[09:23:43] Generating signals... 84 trades found
[09:23:43] Computing performance metrics...
[09:23:43] Done.

每行依次出现（每100ms一行），用 setInterval 模拟
```

「结果展示」状态：

指标展示采用「电报风格」两列布局：
```
TOTAL RETURN        +127.34%
ANNUAL RETURN        +38.12%
SHARPE RATIO           2.14
MAX DRAWDOWN         -18.43%
WIN RATE             67.3%
PROFIT FACTOR          2.87
TOTAL TRADES           84
ALPHA                +21.3%
─────────────────────────────
VS BENCHMARK        +89.21%
```

净值曲线图：
- 深色背景，面积图（渐变从 --accent 到透明）
- X 轴只显示年份
- 回撤图叠加（用半透明红色面积）

交易明细表：紧凑，日期/方向/价格/盈亏，颜色区分买卖

### 4.5 资金流向页（Money Flow）

**设计亮点：主力资金流向的视觉化**

排名表格视觉增强：
```
每行最右侧加一个资金方向指示器：
  - 主力净流入时：向右的彩色条形（颜色深浅=流入量）
  - 主力净流出时：向左的灰色条形
条形宽度范围：0~120px，相对最大值缩放
条形在表格最右侧专用列中显示
```

板块资金面板：
```
改为带排序的水平条形图：
  - 每行：板块名（左对齐）| 流入条形（向右）/ 流出条形（向左）| 数字（等宽）
  - 流入条：--signal-fall（绿）
  - 流出条：--signal-rise（红）
  - 悬停展开：显示超大单/大单/中单/小单分解
  - 整体可排序，默认按净流入降序
```

### 4.6 筹码分布页（Chip Distribution）

**Canvas 绘图必须重新实现，精美度要求极高：**

```
画布配色：
  - 背景：#080810（不使用CSS变量，直接硬编码暗色）
  - 筹码条（当前价上方，已盈利）：#ff3b3b，opacity 0.6
  - 筹码条（当前价下方，套牢盘）：#00e676，opacity 0.5
  - 当前价线：#ffd600（黄色），2px，虚线
  - 均成本线：#e040fb（紫色），1.5px，虚线
  - 支撑位标注：右侧小标签（背景色块+文字）
  - 阻力位标注：右侧小标签

筹码条的绘制方式：
  不使用矩形条，改用对称分布（从中轴向两侧展开）：
    - 左侧：散户持仓（稍窄）
    - 右侧：机构持仓（稍宽，颜色稍深）
  形成类似「蝴蝶型」或「钻石型」的筹码图

Y 轴：价格，精确到小数点后两位（--font-mono，10px）
悬停交互：鼠标移动时，在对应价格区域显示「持仓占比 XX%」工具提示
```

### 4.7 板块轮动页（Sector）

**板块强度列表的视觉设计：**

```
每行（高60px）由四个区域构成：
  1. 排名数字（--font-mono，18px，颜色按排名深浅变化：前3名用--signal-warn）
  2. 板块信息区：名称（--font-sans，15px）+ 涨跌幅 + 主力资金流向数字
  3. 动量热度条：水平渐变条（从蓝到红），标记当前值
  4. 领涨股快速链接（--accent，可点击跳转）

动量热度条颜色方案：
  负动量区：--signal-fall 渐变
  正动量区：--signal-rise 渐变
  零点用细白线标记

整体排列没有分割线，靠行高和对比色自然划分
```

---

## 五、技术实现要求

### 5.1 技术栈（不得更改）

```
框架：Vue 3.x（Composition API + <script setup>）
状态：Pinia
路由：Vue Router 4.x
图表：ECharts 5.x（tree-shaking 按需引入）
HTTP：Axios
构建：Vite 5.x
语言：TypeScript（strict 模式）
字体：JetBrains Mono（Google Fonts 引入）
```

### 5.2 目录结构（严格遵守）

```
frontend/src/
  api/index.ts            # 所有 API 调用（保持与原版完全一致的接口）
  assets/                 # 静态资源
  components/
    chart/
      BaseChart.vue       # ECharts 封装（支持 ResizeObserver）
      CandlestickChart.vue # K线图专用，包含MA/信号叠加
      MiniSparkline.vue   # 迷你折线（用于指数跑马灯和表格行）
      ChipCanvas.vue      # 筹码分布 Canvas 绘制
    layout/
      AppLayout.vue       # 主布局框架
      Sidebar.vue         # 侧边栏
      Topbar.vue          # 顶栏（含搜索）
      TickerBar.vue       # 指数跑马灯
    ui/
      DataPanel.vue       # 数据板块卡片（统一标题+内容槽）
      MetricBlock.vue     # 单指标数字块
      SignalBadge.vue     # BUY/SELL/HOLD 标记
      PriceTag.vue        # 价格+涨跌显示
      DataTable.vue       # 统一数据表格
      StatusDot.vue       # 脉动状态点
      ProgressBar.vue     # 资金流向条形
      Toast.vue           # 通知
      Loader.vue          # 终端风格加载
      SearchModal.vue     # 全局搜索弹窗
  lib/
    echarts.ts            # ECharts 按需注册 + 主题配置
    chartTheme.ts         # 图表主题对象
  router/index.ts         # 所有路由（保持与原版一致）
  stores/
    theme.ts              # 主题（dark/light）
    market.ts
    portfolio.ts
    watchlist.ts
    backtest.ts
    websocket.ts
  styles/
    base.css              # CSS 变量 + Reset + 全局样式
    typography.css        # 字体规则
    components.css        # 复用工具类
  types/index.ts          # 类型（保持与原版完全一致）
  utils/
    format.ts             # 数字/日期格式化（保持与原版一致）
  views/
    dashboard/DashboardPage.vue
    market/MarketPage.vue
    stock/StockDetailPage.vue
    strategy/
      StrategyIntroPage.vue
      StrategyRunPage.vue
    portfolio/PortfolioPage.vue
    watchlist/WatchlistPage.vue
    news/NewsPage.vue
    screener/ScreenerPage.vue
    moneyflow/MoneyFlowPage.vue
    chip/ChipPage.vue
    sector/SectorPage.vue
  App.vue                 # 根组件（含全局键盘导航）
  main.ts                 # 入口
  env.d.ts
```

### 5.3 API 接口（完全不得更改）

所有 API 调用的 URL、参数、返回类型必须与原版 `frontend/src/api/index.ts` 完全一致，代理配置不变（`/api` → `localhost:8080`）。

### 5.4 路由（完全不得更改）

所有路由路径和组件映射与原版 `frontend/src/router/index.ts` 完全一致。

### 5.5 类型定义（完全不得更改）

所有接口和类型定义与原版 `frontend/src/types/index.ts` 完全一致。

### 5.6 工具函数（完全不得更改）

`format.ts` 中所有导出函数的签名和行为与原版一致。

### 5.7 Vite 配置

与原版 `vite.config.ts` 保持一致，不改动代理配置和构建输出目录。

### 5.8 性能要求

```
图表组件：
  - 使用 ResizeObserver 自适应容器大小
  - option 变化时使用 setOption(opt, { notMerge: false }) 避免重渲染抖动
  - 组件销毁时 dispose() + disconnect()

数据表格：
  - 超过 200 行时启用虚拟滚动（手动实现或借助 CSS contain 优化）

状态管理：
  - Dashboard 使用 Promise.allSettled 并发加载所有模块数据
  - 轮询数据（市场状态、指数）使用 setInterval + onUnmounted 清理

代码分割：
  - 所有视图页面懒加载（dynamic import）
  - ECharts 按需引入（不全量导入）
```

---

## 六、页面功能完整性清单

以下所有功能必须完整实现，与原版行为一致：

### Dashboard
- [x] 六大指数实时显示（含迷你折线）
- [x] 板块热力图（TreeMap）
- [x] 策略信号列表（点击跳转个股）
- [x] 北向资金净流入
- [x] 异动行情列表
- [x] 账户快照（总资产/盈亏/收益率/持仓数）
- [x] 自选股快速列表
- [x] 功能入口卡片（6个模块链接）

### 行情页（Market）
- [x] 全市/沪市/深市/创业板/科创板切换
- [x] 股票列表（代码/名称/价/涨跌幅/量/额/换手）
- [x] 行内自选切换（★☆）
- [x] 板块行业视图（密度矩阵布局）
- [x] 量价异动视图

### 个股详情（Stock Detail）
- [x] 粘性股票信息条
- [x] 多周期 K 线图（3M/6M/1Y/3Y）
- [x] MA5/MA10/MA20/MA60 叠加
- [x] 成交量子图（K线图下方）
- [x] DataZoom 缩放
- [x] 策略买卖信号标记
- [x] 深度分析（趋势/动量/量能/信号）
- [x] AI 摘要
- [x] 策略信号列表（含策略名/置信度）
- [x] 基本面数据
- [x] 技术指标数值
- [x] 财务数据（PE/PB/ROE/EPS/营收同比/净利同比）
- [x] 相关股票
- [x] 盘口深度（5档，含可视化条形）
- [x] 模拟交易（买入/卖出）
- [x] 跳转回测功能链接

### 策略百科（Strategy Intro）
- [x] 策略列表（按类别筛选）
- [x] 策略卡片（名称/难度/描述）
- [x] 点击弹出详情弹窗（原理/适用场景/风险/参数说明）
- [x] 直接跳转回测

### 策略回测（Strategy Run）
- [x] 策略选择（垂直列表）
- [x] 参数配置（股票/日期/资金）
- [x] 终端日志风格的运行状态
- [x] 结果概览（所有指标）
- [x] 净值曲线图
- [x] 回撤图
- [x] 交易明细表
- [x] 风险指标（VaR/CVaR/波动率等）
- [x] 蒙特卡洛模拟（按需运行）
- [x] 参数敏感性分析（按需运行）
- [x] 智能策略推荐
- [x] 历史记录（本地存储）
- [x] 策略对比表格

### 投资组合（Portfolio）
- [x] 账户总览（四格关键指标）
- [x] 当前持仓表格（含盈亏百分比、权重）
- [x] 风险监控（集中度/日盈亏/限额/熔断/VaR）
- [x] 交易历史（时间/方向/价格/数量/金额）

### 自选股（Watchlist）
- [x] 股票列表（完整行情数据）
- [x] 添加/移除
- [x] 点击跳转个股
- [x] 价格预警列表（含触发状态）

### 资讯（News）
- [x] 新闻卡片（标题/来源/时间/情绪标签/相关股票）
- [x] 点击新闻打开原链接
- [x] 市场情绪页（恐惧贪婪指数/多维度情绪/资讯统计/热门标的）

### 选股（Screener）
- [x] 预设策略列表（按分类显示）
- [x] 选中预设后运行
- [x] 结果表格（含 PE 等指标）
- [x] 跳转个股

### 资金流向（Money Flow）
- [x] 资金排名表格（主力净流入/超大单/大单/中单/小单）
- [x] 表格行内资金条形指示器
- [x] 板块资金水平条形图
- [x] 悬停分解显示

### 筹码分布（Chip）
- [x] 股票搜索输入
- [x] 快速热门股票按钮
- [x] 六项指标卡（当前价/均成本/获利比例/集中度/支撑位/阻力位）
- [x] Canvas 筹码分布图（对称布局，含当前价/均成本参考线）
- [x] 筹码研判（状态标签/信号文字/三期集中度详情）

### 板块轮动（Sector）
- [x] 板块强度排行榜（含动量热度条/资金流向/领涨股）
- [x] 点击查看板块成分股弹窗
- [x] 轮动信号列表
- [x] 当前快照（领涨/领跌板块）

### 全局功能
- [x] 全局键盘快捷键（⌘K 搜索，⌘D 主题切换，⌘1-5 页面切换）
- [x] 实时时钟（侧边栏底部）
- [x] 市场开盘状态（含脉动动画）
- [x] 深色/亮色主题切换（持久化）
- [x] 全局搜索弹窗（防抖搜索，键盘导航，ESC 关闭）
- [x] 路由切换动画（fade）

---

## 七、视觉细节要求（MUST-HAVE）

以下细节是区分「一般水准」和「艺术级」设计的关键，必须全部实现：

1. **数字跳动动画**：价格更新时，数字有 150ms 的高亮闪烁效果（不是滚动数字，只是颜色短暂加亮）

2. **表格行悬停效果**：不仅仅是背景色变化，同时让该行最左侧出现一条 2px 的竖线（颜色与涨跌色对应）

3. **导航激活线**：侧边栏激活项的左侧竖线有从上到下的"扫描"进入动画（200ms）

4. **背景点阵**：全页面的 CSS 点阵背景，视差滚动（用 CSS perspective 实现轻微的 3D 感）

5. **指数跑马灯**：无缝循环，过渡流畅，不跳动

6. **进度条风格加载**：任何数据加载都显示顶部细进度条，而非 spinner（spinner 只在嵌入内容区）

7. **K线十字线**：ECharts tooltip 的十字准线要细（0.5px），颜色 rgba(255,255,255,0.2)

8. **图表区域分割线**：K线图和成交量子图之间用 1px --border-hair 分隔，而不是默认间距

9. **状态点样式**：开盘状态的脉动动画必须是 CSS keyframe，不得使用 JS 实现

10. **字体降级**：JetBrains Mono 必须在 `<head>` 中预加载，设置 `font-display: swap`，降级字体为 SF Mono → Fira Code → Consolas → monospace

11. **滚动条样式**：所有滚动区域使用自定义细滚动条（6px 宽，圆角，颜色 rgba(255,255,255,0.12)）

12. **数字对齐**：所有等宽数字列必须设置 `font-variant-numeric: tabular-nums`，确保小数点对齐

---

## 八、交付物要求

1. 完整的 `frontend/` 目录，可通过 `npm install && npm run dev` 直接运行
2. 所有原有 API 接口正常工作（不修改后端）
3. 构建命令 `npm run build` 成功，产物输出到 `../static/`
4. TypeScript 编译无 error（warning 允许）
5. 深色/亮色两套主题均完整可用

---

## 九、设计禁忌清单（NEVER DO）

- ❌ 不使用 Element Plus / Ant Design Vue / Naive UI 等 UI 库
- ❌ 不使用 Tailwind CSS（但允许参考其间距概念）
- ❌ 不使用任何 CSS 框架
- ❌ 不使用渐变色作为主要背景（仅允许在图表面积填充中使用）
- ❌ 不使用圆形头像或任何人物/插画元素
- ❌ 不使用超过 4 个字体大小的混合（不含数据展示专用的大字）
- ❌ 不使用 box-shadow 作为装饰（仅允许在弹出层的阴影）
- ❌ 不使用 hover 时的 transform: scale() 超过 1.03
- ❌ 不使用 border-radius > 8px（除了全屏弹窗可用 12px）
- ❌ 不模仿 Ant Design 或 Material Design 的视觉语言
- ❌ 不使用任何 emoji 作为图标（全部使用 inline SVG）
- ❌ 不使用超过 3 种信号色同时出现在同一屏幕区域
- ❌ 不在表格中使用斑马纹（偶数行背景）
- ❌ 不使用圆点分页器
- ❌ 不使用任何 CSS 动画 duration 超过 400ms（加载动画除外）

---

## 十、最终检验标准

完成后，用以下问题自检：

1. 截图发给一个不懂金融的设计师看，他/她的第一感受是「这是一台精密仪器」而不是「这是个网页」吗？

2. 在没有任何数据的情况下，页面的骨架本身是否就已经美观？

3. 在数据更新的瞬间，眼睛能否立即定位到发生变化的区域？

4. 打印截图为黑白后，信息层级是否依然清晰可读？

5. 在 1440×900 分辨率下，不滚动的首屏能否传递出足够的信息量，让用户立刻理解市场全貌？

**如果以上五个问题的答案全部为「是」，则本次重构成功。**
