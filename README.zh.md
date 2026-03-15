<h1 align="center">MaoQuant Skills</h1>

<p align="center">
<strong>A 股一切交易思路，一句话验证</strong>
</p>

<p align="center">
<a href="./README.md">English</a> | 简体中文
</p>

---

你有一个交易想法，MaoQuant 帮你生成完整的回测报告、收益曲线，验证策略可被程序化执行。

## 快速开始

```bash
npx skills add huajuancat/mao-quant
```

然后告诉你的 AI 助手：

```
/backtest ema-crossover SH600000
```

搞定。完整报告，含图表、指标、交易记录。

## 你能做什么

| 你这样问                                            | AI 帮你做                         |
| -------------------------------------------------- | --------------------------------- |
| "茅台用均线策略能赚钱吗？"                            | 自动回测，出收益曲线和完整报告      |
| "宁德时代适合做短线吗？用 KDJ 试试"                    | KDJ 策略回测，标注每笔交易         |
| "MACD 金叉买入到底靠不靠谱？拿平安银行验证一下"         | MACD 策略回测，含胜率、盈亏比      |
| "帮我选一下市盈率低于 15、成交量大的股票"               | 全市场扫描，输出符合条件的股票列表  |
| "布林带做反弹，回撤能控制在多少？"                      | 布林带策略回测，重点展示最大回撤    |

像跟懂量化的朋友聊天一样说就行，MaoQuant 搞定其余的。

## 内置策略

| 策略 | 逻辑 | 适合行情 |
|------|------|----------|
| **均线交叉 (EMA)** | 快慢均线金叉/死叉 | 趋势行情 |
| **RSI** | 超买超卖反转 | 震荡行情 |
| **MACD** | DIF 与 DEA 交叉 | 中长线趋势 |
| **KDJ** | 随机指标极值 | 短线波动 |
| **布林带 (BOLL)** | 价格触及上下轨 | 均值回归 |

## 数据源

双数据引擎，按需选择：

| 引擎 | 覆盖范围 | 配置 |
|------|----------|------|
| **花卷猫数据** | A 股，日线 | 零配置，开箱即用 |
| **通达信 (TDX)** | 全 A 股，日线/1分钟/5分钟 | 需安装通达信客户端并下载数据 |

内置数据即装即用，无需 API Key。

## A 股交易规则（自动内置）

无需配置，MaoQuant 自动执行：

- **T+1**：当日买入，次日才能卖出
- **涨跌停**：主板 +/-10%，创业板/科创板 +/-20%，北交所 +/-30%
- **整手交易**：最小买入 100 股
- **印花税**：卖出千分之一 (0.1%)
- **佣金**：万 2.5（双向），最低 5 元

## 架构

MaoQuant 遵循 [AI Skill Manifest](SPEC.md) 规范。Skill 系统完全自描述：

```
skills/
  SKILL.md              # 根 manifest：capabilities, contracts, environment
  backtest/SKILL.md     # 回测 skill（用户可调用）
  scan/SKILL.md         # 选股 skill（用户可调用）
  data/SKILL.md         # 数据引擎参考
  catquant-expert/      # 知识库 + 6 个规则文件
catquant/               # Python 引擎（回测、指标、图表、数据）
```

关键设计：

- **BarSeries 容器**：`get_history()` 返回 `BarSeries`，`repr` 只显示摘要 -- 原始 K 线数据永远不会泄漏到 AI 上下文
- **环境自检**：`python -m catquant.selftest` 10 秒验证整个环境
- **约束即架构**：T+1、涨跌停、费用、手数由引擎强制执行，不靠提示词

## 环境配置

```bash
pip install -r requirements.txt
cp .env.sample .env     # 按需编辑 FaceCat_URL 和 TDX_DIR
python -m catquant.selftest
```

## 支持的客户端

OpenClaw, Claude Code, Cursor, Windsurf, Copilot, Cline, OpenCode, Trae 等 40+ AI 编程客户端。

## 我们的团队

由[花卷猫量化研究团队](https://jjmfc.com)打造。成员来自：大智慧（龙软）、东方财富、东吴证券、广发证券、东海证券、山西证券、湘财证券、华泰证券、恒泰期货、德意志银行。

## 完整服务

我们提供：

- **数据与分析能力** -- A 股实时与历史数据，独有市场分析能力
- **定制策略开发** -- 为你打造私人策略回测方案

联系我们：**https://www.jjmfc.com**

---

*Built by [花卷猫量化研究团队](https://jjmfc.com)*
