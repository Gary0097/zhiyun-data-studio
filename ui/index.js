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

    function refresh() {
      setLoading(true); setError("");
      return Promise.all([
        json(CORE + "/schemas/orders"),
        json(CORE + "/records/orders?limit=500"),
        json(CORE + "/batches?entity=orders")
      ]).then(function (values) {
        var orderRows = (values[1].records || []).map(function (item) {
          var row = Object.assign({}, item.data);
          row.__record_id = item.record_id; row.__batch_id = item.batch_id; row.__source_type = item.source_type;
          return row;
        });
        setSchema(values[0]); setRecords(orderRows); setBatches(values[2].batches || []);
        return json(APP + "/risk/analyze", { method: "POST", body: { orders: orderRows } });
      }).then(setRisks).catch(function (err) { setError(err.message); }).finally(function () { setLoading(false); });
    }

    React.useEffect(function () { refresh(); }, []);

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
    var columns = schema.fields.filter(function (field) { return field.active; }).slice(0, 10).map(function (field) {
      return { title: field.label, dataIndex: field.name, key: field.name, ellipsis: true, width: field.name === "customer_name" ? 140 : 110,
        render: field.name === "progress" ? function (value) { return h(antd.Progress, { percent: Number(value || 0), size: "small" }); } : undefined };
    });
    columns.push({ title: "风险", key: "risk", fixed: "right", width: 100, render: function (_, row) {
      var risk = riskByOrder[row.order_no] || { level: "green", reasons: [] };
      return h(antd.Tooltip, { title: risk.reasons.join("；") }, h(antd.Tag, { color: riskColor(risk.level) }, riskText(risk.level)));
    }});

    var visibleRecords = records.filter(function (row) {
      var risk = riskByOrder[row.order_no] || { level: "green" };
      var needle = query.trim().toLowerCase();
      var matchesText = !needle || [row.order_no, row.customer_name, row.product_name].some(function (value) { return String(value || "").toLowerCase().indexOf(needle) >= 0; });
      return matchesText && (level === "all" || risk.level === level);
    });

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
        risks.summary.data_quality_issues ? h(antd.Tag, { color: "orange" }, "数据问题 " + risks.summary.data_quality_issues) : null
      ) },
        h(antd.Table, { rowKey: function (row, index) { return row.__record_id || row.order_no || index; }, size: "small", pagination: { pageSize: 8 }, dataSource: records.filter(function (row) { return (riskByOrder[row.order_no] || {}).level !== "green"; }), columns: columns.concat([
          { title: "分数", width: 70, render: function (_, row) { return (riskByOrder[row.order_no] || {}).score || 0; } },
          { title: "判断依据", width: 260, ellipsis: true, render: function (_, row) { return ((riskByOrder[row.order_no] || {}).reasons || []).join("；"); } }
        ]), scroll: { x: 1400 } }))
    ); }

    function dataTable() { return h(antd.Card, { title: "订单数据（" + visibleRecords.length + "/" + records.length + "）", extra: h("div", { style: { display: "flex", gap: 8, flexWrap: "wrap" } },
      h(antd.Input.Search, { allowClear: true, value: query, placeholder: "订单号/客户/产品", style: { width: 220 }, onChange: function (event) { setQuery(event.target.value); } }),
      h(antd.Select, { value: level, style: { width: 110 }, onChange: setLevel, options: [{ value: "all", label: "全部风险" }, { value: "red", label: "高风险" }, { value: "yellow", label: "需关注" }, { value: "green", label: "正常" }] }),
      h(antd.Upload, { accept: ".xlsx,.csv", showUploadList: false, beforeUpload: upload }, h(antd.Button, null, "导入Excel/CSV")),
      h(antd.Button, { onClick: exportCsv }, "导出当前结果"),
      h(antd.Button, { type: "primary", onClick: generate }, "生成模拟订单")
    ) }, h(antd.Table, { rowKey: function (row, index) { return row.__record_id || row.order_no || index; }, size: "small", pagination: { pageSize: 15 }, dataSource: visibleRecords, columns: columns, scroll: { x: 1100 } })); }

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

    var content = tab === "dashboard" ? dashboard() : tab === "data" ? dataTable() : tab === "import" ? importPanel() : tab === "fields" ? fieldsPanel() : batchesPanel();
    return h("div", { style: { padding: 22, height: "100%", overflow: "auto", background: "#f5f7fa" } },
      h("div", { style: { maxWidth: 1280, margin: "0 auto" } },
        h("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 } }, h("div", null, h("h2", { style: { margin: 0 } }, "Data Studio"), h("div", { style: { color: "#667085" } }, "企业数据与订单交付风险分析")), h(antd.Button, { onClick: refresh, loading: loading }, "刷新")),
        error ? h(antd.Alert, { type: "error", showIcon: true, message: "Data Core不可用", description: error, style: { marginBottom: 14 } }) : null,
        h(antd.Tabs, { activeKey: tab, onChange: setTab, items: [
          { key: "dashboard", label: "经营看板" }, { key: "data", label: "订单数据" }, { key: "import", label: "数据导入" }, { key: "fields", label: "字段管理" }, { key: "batches", label: "数据批次" }
        ] }),
        h(antd.Spin, { spinning: loading }, content),
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
