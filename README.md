# Zhiyun Data Studio

v0.8.0 通过 `GET /zhiyun-data-core/orders` 建立持久化订单实时看板闭环，并让选中订单以可溯源上下文进入 Agent。

Data Studio 是 AI-OS 的首个独立业务 PawApp，通过 `zhiyun-data-core` 使用 Workspace 统一数据库，不启动独立端口。

## 已实现功能（v0.8.0）

- 订单数据总览与红/黄/绿交付风险统计。
- 可解释风险评分，显示逾期、生产延误、物流停滞和低进度原因。
- Excel `.xlsx` 与 CSV 文件解析、字段映射、预览校验和确认导入。
- 用户自定义订单字段。
- 一键生成50条模拟订单。
- 真实数据与模拟数据来源标识。
- 批次列表与可恢复撤销。
- Data Core 不可用时显示明确错误，不回退到静态演示数据。
- Agent 可串联 `query_enterprise_orders` 与 `analyze_order_delivery_risk`，直接回答交付风险问题。
- 订单号、客户、产品关键词检索与红/黄/绿风险筛选。
- 当前筛选结果导出 CSV（包含风险等级、分数和判断依据）。
- 关键词、客户、状态、风险及真实/模拟数据来源组合筛选。
- 空数据、接口失败、Data Core 不可用及字段缺失的明确状态，不生成订单兜底。
- 选中订单可成为 Agent 上下文，查询结果保留 Data Core `record_id` 和 `source_type`。
- 风险率、平均进度、逾期数量和数据质量问题统计。
- 支持 ISO 日期时间与中英文已完成状态，异常进度自动限制在 0–100%。
- 按月统计订单量、平均进度与生产延误率，判断上升/下降/平稳趋势并识别异常月份。
- Agent 可调用 `analyze_order_kpi_trends` 直接回答订单关键指标趋势问题。
- 一页式订单每日管理简报，汇总高风险、逾期、临期、平均进度和数据质量问题，支持复制为 Markdown。
- Agent 可调用 `create_order_daily_brief` 生成简报；输出会明确标注尚未接入的生产、财务和售后数据域。
- 可从统一数据库选择任意部门数据表，自主映射部门、产量/产值、工时、人数、成本和损耗字段。
- 自动生成部门级每工时产出、人均产出、单位成本和损耗率，并注册 `analyze_cross_department_metrics` Agent Tool。
- 自动识别标准生产日报字段并完成映射，展示部门效率对比条形图，以及人效最高、单位成本最低、损耗率最低部门。

## AI 对话验收

先由 Data Core 查询统一数据库，再由 Data Studio 分析风险。可直接提问：

- `查询全部订单并分析交付风险，优先列出高风险订单。`
- `分析海川制造订单的交付风险，并说明每笔订单的判断依据。`
- `分析最近几个月订单量、平均进度和生产延误率的趋势。`

风险工具最多接收1000条订单，默认只返回红色和黄色风险项；结果包含风险分数、等级与可解释原因，不会把模型猜测写入数据库。

## 依赖

- QwenPaw 2.1.0
- AI-OS `zhiyun-data-core` 0.1.0+
- 安装插件时自动安装 `openpyxl` 和 `python-multipart`

## 安装

```bash
qwenpaw plugin install /path/to/zhiyun-data-studio --force
qwenpaw app
```

打开 `/apps/zhiyun-data-studio`。

## 验证

```bash
python -m unittest discover -s tests -v
node --check ui/index.js
```

产品需求、功能进度与代码目录见 `docs/PRD.md`、`docs/FEATURE_PROGRESS.md` 和 `docs/CATALOG.md`。

文件解析测试需要与 QwenPaw 相同的 Python 环境，以获得 FastAPI 和 openpyxl 依赖。
