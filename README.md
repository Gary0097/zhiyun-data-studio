# Zhiyun Data Studio

Data Studio 是 AI-OS 的首个独立业务 PawApp，通过 `zhiyun-data-core` 使用 Workspace 统一数据库，不启动独立端口。

## 第一版功能

- 订单数据总览与红/黄/绿交付风险统计。
- 可解释风险评分，显示逾期、生产延误、物流停滞和低进度原因。
- Excel `.xlsx` 与 CSV 文件解析、字段映射、预览校验和确认导入。
- 用户自定义订单字段。
- 一键生成50条模拟订单。
- 真实数据与模拟数据来源标识。
- 批次列表与可恢复撤销。
- Data Core 不可用时显示明确错误，不回退到静态演示数据。

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
python -m unittest -v tests.test_risk_engine
node --check ui/index.js
```

文件解析测试需要与 QwenPaw 相同的 Python 环境，以获得 FastAPI 和 openpyxl 依赖。
