(function () {
  var Q = window.QwenPaw;
  if (!Q || !Q.host || !Q.host.React || !Q.registerRoutes) return;
  var React = Q.host.React;
  var antd = Q.host.antd;
  var h = React.createElement;
  var CORE = "/zhiyun-data-core";
  var APP = "/zhiyun-data-studio";

  function json(path, options) {
    options = options || {};
    var headers = options.headers || {};
    if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
    return Q.host.fetch(path, {
      method: options.method || "GET",
      headers: headers,
      body: options.body instanceof FormData ? options.body : options.body ? JSON.stringify(options.body) : undefined
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (payload) {
        if (!response.ok) throw new Error(payload.detail || ("HTTP " + response.status));
        return payload;
      });
    });
  }

  var LABELS = {
    order_no: "订单编号", customer_name: "客户名称", product_name: "产品名称",
    quantity: "数量", order_date: "下单日期", promised_date: "承诺交期",
    status: "订单状态", progress: "完成进度", last_logistics_update: "物流更新时间",
    production_delay_days: "生产延误天数"
  };

  function riskColor(level) { return level === "red" ? "red" : level === "yellow" ? "orange" : "green"; }
  function riskText(level) { return level === "red" ? "高风险" : level === "yellow" ? "需关注" : "正常"; }

  function DataStudio() {
    var tabState = React.useState("dashboard");
    var tab = tabState[0], setTab = tabState[1];
    var recordsState = React.useState([]);
    var records = recordsState[0], setRecords = recordsState[1];
    var schemaState = React.useState({ fields: [] });
    var schema = schemaState[0], setSchema = schemaState[1];
    var batchesState = React.useState([]);
    var batches = batchesState[0], setBatches = batchesState[1];
    var risksState = React.useState({ summary: { total: 0, red: 0, yellow: 0, green: 0, risk_rate: 0, average_progress: 0, overdue: 0, data_quality_issues: 0 }, status_distribution: {}, results: [] });
    var risks = risksState[0], setRisks = risksState[1];
    var trendsState = React.useState({ summary: { periods: 0, valid_orders: 0, invalid_date_records: 0, direction: "平稳", order_count_slope: 0, anomaly_periods: [] }, series: [] });
    var trends = trendsState[0], setTrends = trendsState[1];
    var briefState = React.useState({ summary: {}, insights: [], top_risks: [], missing_domains: [], disclaimer: "" });
    var brief = briefState[0], setBrief = briefState[1];
    var entityState = React.useState([]);
    var entities = entityState[0], setEntities = entityState[1];
    var fusionEntityState = React.useState("");
    var fusionEntity = fusionEntityState[0], setFusionEntity = fusionEntityState[1];
    var fusionSchemaState = React.useState(null);
    var fusionSchema = fusionSchemaState[0], setFusionSchema = fusionSchemaState[1];
    var fusionMappingState = React.useState({});
    var fusionMapping = fusionMappingState[0], setFusionMapping = fusionMappingState[1];
    var fusionState = React.useState(null);
    var fusion = fusionState[0], setFusion = fusionState[1];
    var loadingState = React.useState(true);
    var loading = loadingState[0], setLoading = loadingState[1];
    var errorState = React.useState("");
    var error = errorState[0], setError = errorState[1];
    var importState = React.useState(null);
    var importData = importState[0], setImportData = importState[1];
    var mappingState = React.useState({});
    var mapping = mappingState[0], setMapping = mappingState[1];
    var previewState = React.useState(null);
    var preview = previewState[0], setPreview = previewState[1];
    var fieldModalState = React.useState(false);
    var fieldModal = fieldModalState[0], setFieldModal = fieldModalState[1];
    var fieldForm = antd.Form.useForm()[0];
    var message = antd.App.useApp().message;
    var queryState = React.useState("");
    var query = queryState[0], setQuery = queryState[1];
    var levelState = React.useState("all");
    var level = levelState[0], setLevel = levelState[1];
    var customerState = React.useState("all");
    var customer = customerState[0], setCustomer = customerState[1];
    var statusState = React.useState("all");
    var status = statusState[0], setStatus = statusState[1];
    var sourceState = React.useState("all");
    var source = sourceState[0], setSource = sourceState[1];
    var selectedState = React.useState(null);
    var selected = selectedState[0], setSelected = selectedState[1];
    var artifactState = React.useState(null);
    var artifact = artifactState[0], setArtifact = artifactState[1];
    var reviewerState = React.useState("");
    var reviewer = reviewerState[0], setReviewer = reviewerState[1];

    function recordRefs(rows) {
      return (rows || []).filter(function (row) { return row.record_id && (row.source_type === "real" || row.source_type === "simulated"); })
        .map(function (row) { return { record_id: row.record_id, source_type: row.source_type }; });
    }
    function saveArtifact(kind, name, content, refs) {
      if (!refs.length) { message.warning("没有可追溯的 Data Core 记录，不能保存工件"); return; }
      setLoading(true);
      json(APP + "/artifacts", { method: "POST", body: { kind: kind, name: name, content: content, source_refs: refs } })
        .then(function (data) { setArtifact(data); message.success("已保存为待审阅工件"); })
        .catch(function (err) { message.error(err.message); }).finally(function () { setLoading(false); });
    }
    function reviewArtifact(action) {
      if (!reviewer.trim()) { message.warning("请输入审阅人"); return; }
      json(APP + "/artifacts/" + artifact.id + "/reviews", { method: "POST", body: { action: action, reviewer: reviewer } })
        .then(function (data) { setArtifact(data); message.success(action === "accept" ? "工件已接受" : "已撤销接受"); })
        .catch(function (err) { message.error(err.message); });
    }

    function refresh() {
      setLoading(true); setError("");
      return json(CORE + "/orders").then(function (orderPayload) {
        return json(APP + "/orders/normalize", { method: "POST", body: { payload: orderPayload } });
      }).then(function (normalized) {
        var orderRows = normalized.orders || [];
        setRecords(orderRows);
        return Promise.all([
          json(CORE + "/schemas/orders").then(setSchema),
          json(CORE + "/batches?entity=orders").then(function (value) { setBatches(value.batches || []); }),
          json(APP + "/risk/analyze", { method: "POST", body: { orders: orderRows } }),
          json(APP + "/trends/analyze", { method: "POST", body: { orders: orderRows } }),
          json(APP + "/brief/daily", { method: "POST", body: { orders: orderRows } })
        ]);
      }).then(function (analysis) {
        setRisks(analysis[2]); setTrends(analysis[3]); setBrief(analysis[4]);
      }).catch(function (err) {
        setRecords([]); setError(err.message);
      }).finally(function () { setLoading(false); });
    }

    React.useEffect(function () {
      refresh();
      json(CORE + "/entities").then(function (data) { setEntities(data.entities || []); });
    }, []);

    React.useEffect(function () {
      if (!fusionEntity) { setFusionSchema(null); return; }
      json(CORE + "/schemas/" + encodeURIComponent(fusionEntity)).then(function (data) {
        setFusionSchema(data);
        var names = (data.fields || []).map(function (field) { return field.name; });
        var standard = {};
        ["department", "output", "labor_hours", "employee_count", "cost", "loss"].forEach(function (name) { if (names.indexOf(name) >= 0) standard[name] = name; });
        setFusionMapping(standard); setFusion(null);
      }).catch(function (err) { message.error(err.message); });
    }, [fusionEntity]);

    function generate() {
      json(CORE + "/simulate/orders", { method: "POST", body: { count: 50, seed: Date.now() % 100000 } })
        .then(function () { message.success("已生成50条模拟订单"); return refresh(); })
        .catch(function (err) { message.error(err.message); });
    }

    function rollback(batchId) {
      json(CORE + "/batches/" + encodeURIComponent(batchId) + "/rollback", { method: "POST" })
        .then(function () { message.success("批次已撤销"); return refresh(); })
        .catch(function (err) { message.error(err.message); });
    }

    function upload(file) {
      var form = new FormData(); form.append("file", file);
      json(APP + "/parse", { method: "POST", body: form }).then(function (data) {
        var fields = schema.fields.filter(function (field) { return field.active; });
        var next = {};
        data.headers.forEach(function (header) {
          var exact = fields.find(function (field) { return field.name === header || field.label === header || LABELS[field.name] === header; });
          if (exact) next[header] = exact.name;
        });
        setImportData(data); setMapping(next); setPreview(null); setTab("import");
      }).catch(function (err) { message.error(err.message); });
      return false;
    }

    function runPreview() {
      json(CORE + "/imports/orders/preview", { method: "POST", body: { rows: importData.rows, mapping: mapping, source_name: importData.filename } })
        .then(setPreview).catch(function (err) { message.error(err.message); });
    }

    function commitImport() {
      json(CORE + "/imports/orders/commit", { method: "POST", body: { rows: importData.rows, mapping: mapping, source_name: importData.filename } })
        .then(function (result) { message.success("已导入" + result.row_count + "条数据"); setImportData(null); setPreview(null); setTab("data"); return refresh(); })
        .catch(function (err) { message.error(err.message); });
    }

    function addField() {
      fieldForm.validateFields().then(function (values) {
        return json(CORE + "/schemas/orders/fields", { method: "POST", body: values });
      }).then(function (next) { setSchema(next); setFieldModal(false); fieldForm.resetFields(); message.success("字段已添加"); })
        .catch(function (err) { if (err instanceof Error) message.error(err.message); });
    }

    function disableField(field) {
      json(CORE + "/schemas/orders/fields/" + field.name, { method: "PATCH", body: { active: false } })
        .then(function (next) { setSchema(next); message.success("字段已停用"); }).catch(function (err) { message.error(err.message); });
    }

    var riskByOrder = {};
    risks.results.forEach(function (item) { riskByOrder[item.order_no] = item; });
    var columns = [
      ["订单号", "order_no", 130], ["客户", "customer_name", 140], ["产品", "product_name", 140],
      ["数量", "quantity", 80], ["交期", "promised_date", 110], ["状态", "status", 100],
      ["进度", "progress", 130], ["来源", "source_type", 100]
    ].map(function (field) { return { title: field[0], dataIndex: field[1], key: field[1], ellipsis: true, width: field[2],
      render: field[1] === "progress" ? function (value) { return value == null ? "字段缺失" : h(antd.Progress, { percent: Math.max(0, Math.min(100, Number(value) || 0)), size: "small" }); }
        : field[1] === "source_type" ? function (value) { return value ? h(antd.Tag, { color: value === "real" ? "blue" : "purple" }, value === "real" ? "真实数据" : "模拟数据") : h(antd.Tag, { color: "warning" }, "来源缺失"); }
        : function (value) { return value == null || value === "" ? h("span", { style: { color: "#b54708" } }, "字段缺失") : String(value); }
    }; });
    columns.push({ title: "风险", key: "risk", fixed: "right", width: 100, render: function (_, row) {
      var risk = riskByOrder[row.order_no] || { level: "green", reasons: [] };
      return h(antd.Tooltip, { title: risk.reasons.join("；") }, h(antd.Tag, { color: riskColor(risk.level) }, riskText(risk.level)));
    }});

    var visibleRecords = records.filter(function (row) {
      var risk = riskByOrder[row.order_no] || { level: "green" };
      var needle = query.trim().toLowerCase();
      var matchesText = !needle || [row.order_no, row.customer_name, row.product_name].some(function (value) { return String(value || "").toLowerCase().indexOf(needle) >= 0; });
      return matchesText && (level === "all" || risk.level === level) &&
        (customer === "all" || row.customer_name === customer) &&
        (status === "all" || row.status === status) &&
        (source === "all" || row.source_type === source);
    });

    function selectForAgent(row) {
      json(APP + "/agent/context", { method: "POST", body: { order: row } }).then(function (context) {
        setSelected(context);
        if (Q.setAgentContext) Q.setAgentContext(context);
        else window.dispatchEvent(new CustomEvent("qwenpaw:agent-context", { detail: context }));
        message.success("已将 " + context.label + " 加入 Agent 上下文");
      }).catch(function (err) { message.error(err.message); });
    }

    function exportCsv() {
      if (!visibleRecords.length) { message.warning("当前没有可导出的订单"); return; }
      var fields = schema.fields.filter(function (field) { return field.active; });
      var quote = function (value) {
        var text = String(value == null ? "" : value);
        if (/^[=+\-@]/.test(text)) text = "'" + text;
        return '"' + text.replace(/"/g, '""') + '"';
      };
      var lines = [fields.map(function (field) { return quote(field.label); }).concat([quote("风险等级"), quote("风险分数"), quote("判断依据")]).join(",")];
      visibleRecords.forEach(function (row) {
        var risk = riskByOrder[row.order_no] || { level: "green", score: 0, reasons: [] };
        lines.push(fields.map(function (field) { return quote(row[field.name]); }).concat([quote(riskText(risk.level)), quote(risk.score), quote((risk.reasons || []).join("；"))]).join(","));
      });
      var blob = new Blob(["\ufeff" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
      var link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = "订单风险清单.csv"; link.click();
      window.setTimeout(function () { URL.revokeObjectURL(link.href); }, 1000);
    }

    var summaryCards = [
      ["订单总数", risks.summary.total, "#1677ff"], ["高风险", risks.summary.red, "#ef4444"],
      ["需关注", risks.summary.yellow, "#f59e0b"], ["风险率", (risks.summary.risk_rate || 0) + "%", "#7c3aed"]
    ];

    function dashboard() { return h(React.Fragment, null,
      h("div", { style: { display: "grid", gridTemplateColumns: "repeat(4,minmax(140px,1fr))", gap: 14 } }, summaryCards.map(function (item) {
        return h(antd.Card, { key: item[0], size: "small" }, h("div", { style: { color: "#667085" } }, item[0]), h("div", { style: { fontSize: 30, fontWeight: 700, color: item[2] } }, item[1]));
      })),
      h(antd.Card, { title: "交付风险订单", style: { marginTop: 16 }, extra: h(antd.Space, null,
        h(antd.Tag, { color: "red" }, "逾期 " + (risks.summary.overdue || 0)),
        h(antd.Tag, { color: "blue" }, "平均进度 " + (risks.summary.average_progress || 0) + "%"),
        risks.summary.data_quality_issues ? h(antd.Tag, { color: "orange" }, "数据问题 " + risks.summary.data_quality_issues) : null,
        h(antd.Button, { onClick: function () { saveArtifact("delivery_risk", "订单交付风险清单", risks, recordRefs(records)); } }, "保存为待审阅工件")
      ) },
        h(antd.Table, { rowKey: function (row, index) { return row.__record_id || row.order_no || index; }, size: "small", pagination: { pageSize: 8 }, dataSource: records.filter(function (row) { return (riskByOrder[row.order_no] || {}).level !== "green"; }), columns: columns.concat([
          { title: "分数", width: 70, render: function (_, row) { return (riskByOrder[row.order_no] || {}).score || 0; } },
          { title: "判断依据", width: 260, ellipsis: true, render: function (_, row) { return ((riskByOrder[row.order_no] || {}).reasons || []).join("；"); } }
        ]), scroll: { x: 1400 } }))
    ); }

    function dataTable() { return h(antd.Card, { title: "实时客户订单进度（" + visibleRecords.length + "/" + records.length + "）", extra: h("div", { style: { display: "flex", gap: 8, flexWrap: "wrap" } },
      h(antd.Input.Search, { allowClear: true, value: query, placeholder: "订单号/客户/产品", style: { width: 220 }, onChange: function (event) { setQuery(event.target.value); } }),
      h(antd.Select, { value: customer, style: { width: 140 }, onChange: setCustomer, options: [{ value: "all", label: "全部客户" }].concat(Array.from(new Set(records.map(function (row) { return row.customer_name; }).filter(Boolean))).map(function (value) { return { value: value, label: value }; })) }),
      h(antd.Select, { value: status, style: { width: 120 }, onChange: setStatus, options: [{ value: "all", label: "全部状态" }].concat(Array.from(new Set(records.map(function (row) { return row.status; }).filter(Boolean))).map(function (value) { return { value: value, label: value }; })) }),
      h(antd.Select, { value: source, style: { width: 120 }, onChange: setSource, options: [{ value: "all", label: "全部来源" }, { value: "real", label: "真实数据" }, { value: "simulated", label: "模拟数据" }] }),
      h(antd.Select, { value: level, style: { width: 110 }, onChange: setLevel, options: [{ value: "all", label: "全部风险" }, { value: "red", label: "高风险" }, { value: "yellow", label: "需关注" }, { value: "green", label: "正常" }] }),
      h(antd.Upload, { accept: ".xlsx,.csv", showUploadList: false, beforeUpload: upload }, h(antd.Button, null, "导入Excel/CSV")),
      h(antd.Button, { onClick: exportCsv }, "导出当前结果"),
      h(antd.Button, { type: "primary", onClick: generate }, "生成模拟订单")
    ) },
      selected ? h(antd.Alert, { type: "info", showIcon: true, closable: true, onClose: function () { setSelected(null); }, message: selected.label + " 已选中", description: "Data Core record_id: " + selected.record_id + " · source_type: " + selected.source_type, style: { marginBottom: 12 } }) : null,
      !loading && !error && records.length === 0 ? h(antd.Empty, { description: "Data Core 中暂无持久化订单" }) :
      !loading && visibleRecords.length === 0 ? h(antd.Empty, { description: "没有符合当前筛选条件的订单" }) :
      h(antd.Table, { rowKey: function (row, index) { return row.record_id || row.order_no || index; }, size: "small", pagination: { pageSize: 15 }, dataSource: visibleRecords, columns: columns.concat([{ title: "操作", fixed: "right", width: 120, render: function (_, row) { return h(antd.Button, { size: "small", onClick: function () { selectForAgent(row); } }, "交给 Agent"); } }]), scroll: { x: 1150 } })
    ); }

    function importPanel() {
      if (!importData) return h(antd.Empty, { description: "请在订单数据页面选择Excel或CSV文件" });
      var options = schema.fields.filter(function (field) { return field.active; }).map(function (field) { return { label: field.label + "（" + field.name + "）", value: field.name }; });
      return h(antd.Card, { title: "导入映射 · " + importData.filename },
        h(antd.Alert, { type: "info", showIcon: true, message: "共" + importData.row_count + "行，请确认源字段与数据库字段的对应关系。", style: { marginBottom: 14 } }),
        h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(260px,1fr))", gap: 10 } }, importData.headers.map(function (header) {
          return h("div", { key: header, style: { display: "flex", alignItems: "center", gap: 8 } }, h("span", { style: { width: 100 } }, header), h(antd.Select, { allowClear: true, value: mapping[header], options: options, style: { flex: 1 }, placeholder: "选择目标字段", onChange: function (value) { setMapping(Object.assign({}, mapping, (function () { var x = {}; x[header] = value; return x; })())); } }));
        })),
        h("div", { style: { marginTop: 16, display: "flex", gap: 8 } }, h(antd.Button, { onClick: runPreview }, "预览校验"), h(antd.Button, { type: "primary", disabled: !preview || preview.error_count > 0, onClick: commitImport }, "确认导入")),
        preview ? h(antd.Alert, { style: { marginTop: 14 }, type: preview.error_count ? "error" : "success", showIcon: true, message: preview.error_count ? ("发现" + preview.error_count + "行错误") : (preview.valid_count + "行数据校验通过"), description: preview.errors && preview.errors.length ? preview.errors.slice(0, 5).map(function (item) { return "第" + item.row + "行：" + item.errors.join("，"); }).join("；") : null }) : null
      );
    }

    function fieldsPanel() { return h(antd.Card, { title: "订单字段", extra: h(antd.Button, { type: "primary", onClick: function () { setFieldModal(true); } }, "新增字段") },
      h(antd.Table, { rowKey: "name", size: "small", pagination: false, dataSource: schema.fields, columns: [
        { title: "显示名称", dataIndex: "label" }, { title: "字段标识", dataIndex: "name" }, { title: "类型", dataIndex: "type" },
        { title: "状态", render: function (_, field) { return h(antd.Tag, { color: field.active ? "green" : "default" }, field.active ? "启用" : "停用"); } },
        { title: "来源", render: function (_, field) { return field.built_in ? "系统字段" : "自定义字段"; } },
        { title: "操作", render: function (_, field) { return !field.built_in && field.active ? h(antd.Button, { danger: true, size: "small", onClick: function () { disableField(field); } }, "停用") : null; } }
      ] })
    ); }

    function batchesPanel() { return h(antd.Card, { title: "数据批次" }, h(antd.Table, { rowKey: "batch_id", size: "small", dataSource: batches, columns: [
      { title: "批次", dataIndex: "batch_id", ellipsis: true }, { title: "来源", dataIndex: "source_name" },
      { title: "类型", render: function (_, row) { return h(antd.Tag, { color: row.source_type === "real" ? "blue" : "purple" }, row.source_type === "real" ? "真实数据" : "模拟数据"); } },
      { title: "数量", dataIndex: "row_count" }, { title: "状态", dataIndex: "status" },
      { title: "操作", render: function (_, row) { return row.status === "active" ? h(antd.Popconfirm, { title: "撤销后将删除该批次数据，确认继续？", onConfirm: function () { rollback(row.batch_id); } }, h(antd.Button, { danger: true, size: "small" }, "撤销")) : null; } }
    ] })); }

    function trendsPanel() {
      var summary = trends.summary || {};
      return h(React.Fragment, null,
        h(antd.Alert, { type: "info", showIcon: true, message: "趋势结论基于数据库内有有效下单日期的记录计算。", description: summary.method, style: { marginBottom: 14 } }),
        h("div", { style: { display: "grid", gridTemplateColumns: "repeat(4,minmax(140px,1fr))", gap: 14, marginBottom: 14 } },
          [["统计月份", summary.periods || 0], ["有效订单", summary.valid_orders || 0], ["订单量趋势", summary.direction || "平稳"], ["月均变化", summary.order_count_slope || 0]].map(function (item) {
            return h(antd.Card, { key: item[0], size: "small" }, h(antd.Statistic, { title: item[0], value: item[1] }));
          })
        ),
        summary.invalid_date_records ? h(antd.Alert, { type: "warning", showIcon: true, message: summary.invalid_date_records + " 条记录缺少有效下单日期，未进入趋势计算。", style: { marginBottom: 14 } }) : null,
        h(antd.Card, { title: "订单关键指标月度趋势", extra: h(antd.Space, null, (summary.anomaly_periods || []).length ? h(antd.Tag, { color: "orange" }, "异常月份 " + summary.anomaly_periods.join("、")) : h(antd.Tag, { color: "green" }, "未发现异常月份"), h(antd.Button, { onClick: function () { saveArtifact("kpi_trend", "订单关键指标趋势", trends, recordRefs(records)); } }, "保存为待审阅工件")) },
          h(antd.Table, { rowKey: "period", size: "small", pagination: false, dataSource: trends.series || [], columns: [
            { title: "月份", dataIndex: "period" }, { title: "订单量", dataIndex: "order_count" },
            { title: "平均进度", dataIndex: "average_progress", render: function (value) { return h(antd.Progress, { percent: value, size: "small" }); } },
            { title: "生产延误率", dataIndex: "delay_rate", render: function (value) { return value + "%"; } }
          ] })
        )
      );
    }

    function briefPanel() {
      var summary = brief.summary || {};
      var levelColor = { critical: "red", warning: "orange", info: "blue", normal: "green" };
      function copyBrief() {
        var lines = ["# 企业订单每日简报（" + (brief.brief_date || "") + "）", "", brief.disclaimer || ""];
        (brief.insights || []).forEach(function (item) { lines.push("- " + item.text); });
        lines.push("", "订单总数：" + (summary.total || 0), "高风险：" + (summary.red || 0), "逾期：" + (summary.overdue || 0), "平均进度：" + (summary.average_progress || 0) + "%");
        navigator.clipboard.writeText(lines.join("\n")).then(function () { message.success("简报已复制"); }).catch(function () { message.error("复制失败，请检查浏览器权限"); });
      }
      return h(React.Fragment, null,
        h(antd.Alert, { type: "warning", showIcon: true, message: brief.disclaimer || "当前仅覆盖订单域", style: { marginBottom: 14 } }),
        h("div", { style: { display: "grid", gridTemplateColumns: "repeat(4,minmax(140px,1fr))", gap: 14, marginBottom: 14 } },
          [["订单总数", summary.total || 0], ["高风险", summary.red || 0], ["逾期订单", summary.overdue || 0], ["平均进度", (summary.average_progress || 0) + "%"]].map(function (item) {
            return h(antd.Card, { key: item[0], size: "small" }, h(antd.Statistic, { title: item[0], value: item[1] }));
          })
        ),
        h(antd.Card, { title: "今日管理提示", extra: h(antd.Space, null, h(antd.Button, { onClick: copyBrief }, "复制简报"), h(antd.Button, { onClick: function () { saveArtifact("daily_brief", "企业订单每日简报", brief, recordRefs(records)); } }, "保存为待审阅工件")) },
          h(antd.List, { dataSource: brief.insights || [], renderItem: function (item) { return h(antd.List.Item, null, h(antd.Tag, { color: levelColor[item.level] || "default" }, item.level), item.text); } })
        ),
        h(antd.Card, { title: "优先处理订单", style: { marginTop: 14 } },
          h(antd.Table, { rowKey: function (row, index) { return row.order_no || index; }, size: "small", pagination: false, dataSource: brief.top_risks || [], columns: [
            { title: "订单号", dataIndex: "order_no" }, { title: "客户", dataIndex: "customer_name" },
            { title: "风险", dataIndex: "level", render: function (value) { return h(antd.Tag, { color: riskColor(value) }, riskText(value)); } },
            { title: "分数", dataIndex: "score" }, { title: "判断依据", dataIndex: "reasons", render: function (value) { return (value || []).join("；"); } }
          ] })
        )
      );
    }

    function fusionPanel() {
      var fields = fusionSchema ? fusionSchema.fields.filter(function (field) { return field.active; }) : [];
      var fieldOptions = fields.map(function (field) { return { value: field.name, label: field.label + " (" + field.name + ")" }; });
      var metrics = [
        ["department", "部门字段", true], ["output", "产量/产值字段", true], ["labor_hours", "工时字段", true],
        ["employee_count", "人数字段", false], ["cost", "成本字段", false], ["loss", "损耗字段", false]
      ];
      function runFusion() {
        if (!fusionMapping.department || !fusionMapping.output || !fusionMapping.labor_hours) { message.warning("请至少映射部门、产量/产值和工时字段"); return; }
        setLoading(true);
        json(CORE + "/records/" + encodeURIComponent(fusionEntity) + "?limit=1000").then(function (data) {
          return json(APP + "/fusion/analyze", { method: "POST", body: { records: (data.records || []).map(function (item) { return item.data; }), mapping: fusionMapping } })
            .then(function (result) { result.source_refs = recordRefs(data.records || []); return result; });
        }).then(setFusion).catch(function (err) { message.error(err.message); }).finally(function () { setLoading(false); });
      }
      return h(React.Fragment, null,
        h(antd.Alert, { type: "info", showIcon: true, message: "选择任意部门数据表并映射业务字段，系统按部门计算人效、单位成本和损耗率。", style: { marginBottom: 14 } }),
        h(antd.Card, { title: "指标模型配置", extra: h(antd.Space, null,
          entities.some(function (item) { return item.entity === "production"; }) ? h(antd.Button, { onClick: function () { setFusionEntity("production"); } }, "使用生产日报模板") : null,
          h(antd.Button, { type: "primary", disabled: !fusionEntity, onClick: runFusion }, "生成部门指标")
        ) },
          h(antd.Form, { layout: "vertical" },
            h(antd.Form.Item, { label: "数据表", required: true }, h(antd.Select, { value: fusionEntity || undefined, placeholder: "选择已导入数据的部门表", options: entities.map(function (item) { return { value: item.entity, label: item.label + "（" + item.record_count + "条）" }; }), onChange: setFusionEntity })),
            h("div", { style: { display: "grid", gridTemplateColumns: "repeat(3,minmax(200px,1fr))", gap: 12 } }, metrics.map(function (metric) {
              return h(antd.Form.Item, { key: metric[0], label: metric[1], required: metric[2] }, h(antd.Select, { allowClear: true, value: fusionMapping[metric[0]], options: fieldOptions, placeholder: "选择字段", onChange: function (value) { var next = Object.assign({}, fusionMapping); if (value) next[metric[0]] = value; else delete next[metric[0]]; setFusionMapping(next); setFusion(null); } }));
            }))
          )
        ),
        fusion ? h(React.Fragment, null,
          h("div", { style: { display: "grid", gridTemplateColumns: "repeat(4,minmax(140px,1fr))", gap: 14, margin: "14px 0" } },
            [["部门数", fusion.summary.departments], ["有效记录", fusion.summary.valid_records], ["总产量/产值", fusion.summary.total_output], ["总成本", fusion.summary.total_cost]].map(function (item) { return h(antd.Card, { key: item[0], size: "small" }, h(antd.Statistic, { title: item[0], value: item[1] })); })
          ),
          h(antd.Row, { gutter: [12, 12], style: { marginBottom: 14 } }, [
            ["人效最高", fusion.highlights && fusion.highlights.highest_productivity],
            ["单位成本最低", fusion.highlights && fusion.highlights.lowest_unit_cost],
            ["损耗率最低", fusion.highlights && fusion.highlights.lowest_loss_rate]
          ].map(function (item) { return h(antd.Col, { xs: 24, md: 8, key: item[0] }, h(antd.Card, { size: "small" }, h(antd.Statistic, { title: item[0], value: item[1] || "暂无" }))); })),
          h(antd.Card, { title: "部门效率对比", style: { marginBottom: 14 }, extra: h(antd.Button, { onClick: function () { saveArtifact("department_fusion", "跨部门融合指标", fusion, fusion.source_refs || []); } }, "保存为待审阅工件") }, (fusion.results || []).map(function (row) {
            var max = Math.max.apply(null, (fusion.results || []).map(function (item) { return item.output_per_hour || 0; })) || 1;
            return h("div", { key: row.department, style: { display: "grid", gridTemplateColumns: "120px 1fr 90px", gap: 10, alignItems: "center", marginBottom: 10 } },
              h("span", null, row.department), h(antd.Progress, { percent: Math.round(100 * (row.output_per_hour || 0) / max), showInfo: false }), h("strong", null, row.output_per_hour == null ? "-" : row.output_per_hour + "/工时")
            );
          })),
          h(antd.Card, { title: "部门人效—产值—损耗指标" }, h(antd.Table, { rowKey: "department", size: "small", pagination: false, dataSource: fusion.results || [], scroll: { x: 1100 }, columns: [
            { title: "部门", dataIndex: "department", fixed: "left" }, { title: "产量/产值", dataIndex: "output" }, { title: "工时", dataIndex: "labor_hours" },
            { title: "人数", dataIndex: "employee_count" }, { title: "每工时产出", dataIndex: "output_per_hour" }, { title: "人均产出", dataIndex: "output_per_employee" },
            { title: "总成本", dataIndex: "cost" }, { title: "单位成本", dataIndex: "cost_per_output" }, { title: "损耗", dataIndex: "loss" },
            { title: "损耗率", dataIndex: "loss_rate", render: function (value) { return value == null ? "-" : value + "%"; } }
          ] }))
        ) : null
      );
    }

    var content = tab === "dashboard" ? dashboard() : tab === "fusion" ? fusionPanel() : tab === "brief" ? briefPanel() : tab === "trends" ? trendsPanel() : tab === "data" ? dataTable() : tab === "import" ? importPanel() : tab === "fields" ? fieldsPanel() : batchesPanel();
    return h("div", { style: { padding: 22, height: "100%", overflow: "auto", background: "#f5f7fa" } },
      h("div", { style: { maxWidth: 1280, margin: "0 auto" } },
        h("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 } }, h("div", null, h("h2", { style: { margin: 0 } }, "Data Studio"), h("div", { style: { color: "#667085" } }, "企业数据与订单交付风险分析")), h(antd.Button, { onClick: refresh, loading: loading }, "刷新")),
        error ? h(antd.Alert, { type: "error", showIcon: true, message: "Data Core不可用", description: error, style: { marginBottom: 14 } }) : null,
        h(antd.Tabs, { activeKey: tab, onChange: setTab, items: [
          { key: "dashboard", label: "经营看板" }, { key: "fusion", label: "跨部门指标" }, { key: "brief", label: "每日简报" }, { key: "trends", label: "趋势分析" }, { key: "data", label: "订单数据" }, { key: "import", label: "数据导入" }, { key: "fields", label: "字段管理" }, { key: "batches", label: "数据批次" }
        ] }),
        h(antd.Spin, { spinning: loading }, content),
        artifact ? h(antd.Card, { title: "分析工件审阅", style: { marginTop: 16 }, extra: h(antd.Tag, { color: artifact.project_status === "accepted" ? "green" : "orange" }, artifact.project_status) },
          h(antd.Alert, { type: "info", showIcon: true, message: artifact.name, description: "Trace " + artifact.trace_id + " · " + artifact.source_refs.length + " 条 Data Core 来源" }),
          h(antd.Space, { style: { marginTop: 12 }, wrap: true },
            h(antd.Input, { value: reviewer, onChange: function (e) { setReviewer(e.target.value); }, placeholder: "审阅人", style: { width: 180 } }),
            h(antd.Button, { type: "primary", onClick: function () { reviewArtifact("accept"); } }, "接受工件"),
            h(antd.Button, { onClick: function () { reviewArtifact("revoke"); } }, "撤销接受"),
            h(antd.Button, { disabled: artifact.project_status !== "accepted", onClick: function () { window.open(APP + "/artifacts/" + artifact.id + "/export", "_blank"); } }, "导出工件")
          )
        ) : null,
        h(antd.Modal, { title: "新增订单字段", open: fieldModal, onOk: addField, onCancel: function () { setFieldModal(false); } },
          h(antd.Form, { form: fieldForm, layout: "vertical" },
            h(antd.Form.Item, { name: "label", label: "显示名称", rules: [{ required: true }] }, h(antd.Input, { placeholder: "例如：销售区域" })),
            h(antd.Form.Item, { name: "name", label: "字段标识", rules: [{ required: true, pattern: /^[a-z][a-z0-9_]{0,62}$/, message: "使用小写英文、数字和下划线" }] }, h(antd.Input, { placeholder: "例如：sales_region" })),
            h(antd.Form.Item, { name: "field_type", label: "字段类型", initialValue: "text" }, h(antd.Select, { options: ["text", "integer", "number", "boolean", "date", "datetime"].map(function (value) { return { label: value, value: value }; }) }))
          )
        )
      )
    );
  }

  Q.registerRoutes("zhiyun-data-studio", [{ path: "/apps/zhiyun-data-studio", component: DataStudio, label: "Data Studio", icon: "📊", priority: 90 }]);
})();
