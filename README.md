# EcomLab

电商实验系统 — 支持多种自适应实验方法的计算与可视化。

当前已实现方法：MAB 多臂老虎机、Best of Three Worlds 自适应实验。

---

## 项目结构

```
EcomLab/
├── app.py                     # Flask 后端（所有逻辑在此文件）
├── DEV_SPEC.md                # 开发规范（新增实验方法必须遵守）
├── EXPERIMENT_SPECIFICATION.md
├── README.md                  # 本文件
├── templates/
│   ├── index.html             # MAB 多臂老虎机页
│   ├── paper.html             # Best of Three Worlds 页
│   ├── compare.html           # 左右对比页
│   └── export.html            # 打印报告模板
└── static/uploads/            # 上传的测试图片（运行时自动创建）
```

---

## 技术栈

| 层 | 技术 |
|----|------|
| 后端   | Python 3.10 + Flask |
| 前端   | Jinja2 模板，CSS/JS 内联，无构建工具 |
| 数据库 | MySQL 8.0（8.163.52.51:13306，root/LFajEj6Lw7tKfZ8z，库 ecomlab） |
| 驱动   | pymysql |
| 图片   | werkzeug secure_filename + static/uploads/ |

---

## 快速启动

```bash
cd EcomLab
pip install flask pymysql
python app.py
# 访问 http://127.0.0.1:5000
```

---

# ⚠️ AI 助手必读：如何新增一个实验方法

请先通读 **DEV_SPEC.md**（开发规范）再动手。以下是精简版流程。

---

## 第一层：新增方法的 7 步流程

### 1. 确定 method 字符串
如 `epsilon-greedy`，全部小写+短横线。这个字符串贯穿路由、数据库、模板。

### 2. 添加路由（app.py）
复制 `paper()` 函数，改这 5 处：
```python
@app.route("/epsilon-greedy", methods=["GET", "POST"])
def epsilon_greedy():
    # 改 1：路由路径
    # 改 2：experiment_title 默认值 → "EG 实验"
    # 改 3：save_experiment(..., "epsilon-greedy", ...)
    # 改 4：list_experiments("epsilon-greedy")
    # 改 5：render_template("epsilon-greedy.html", ..., metrics_config=METRICS_CONFIG_EG)
```

### 3. 创建模板（templates/）
复制 `paper.html` → `epsilon-greedy.html`，逐区域改：
- Hero 标题、介绍、badge 标签
- 输入表格列 → 根据该方法需要的指标动态渲染
- 结果表格列 → 根据该方法输出的指标动态渲染
- 小白解读区块
- 操作建议区块
- `saveExperiment('epsilon-greedy')` 调用

### 4. 注册导航
在所有模板的 `<details class="page-switcher">` 中加链接。要改的文件：`index.html`、`paper.html`、`compare.html`。

### 5. 如需方法特有的算法逻辑
在 `app.py` 中新增独立算法函数（命名 `compute_xxx`），在路由中调用，不要改已有的 `compute_results()`。

### 6. 验证
```bash
python -c "from app import app; c=app.test_client(); print(c.get('/epsilon-greedy').status_code)"
# 预期输出 200
```

### 7. 提交前检查 DEV_SPEC.md 末尾的自查清单

---

## 第二层：多指标系统 — 每个实验自己选指标

当前系统只支持两个输入字段：`visitors`（访客数）和 `clicks`（点击数），输出指标只有一个 CTR。新增的实验方法很可能需要更多指标。以下是实现方案。

### 核心理念

**不是在现有页面上硬塞所有指标列，而是每个实验方法声明自己需要哪些输入字段和输出指标。** 前端根据声明渲染输入表格，后端根据声明计算对应指标。

### 第一步：在 app.py 中定义指标注册表

在 `app.py` 顶部新增常量字典，声明所有可用指标：

```python
# 所有可用指标的注册表 — key 同时用作数据库字段名、表单名、显示名
METRICS = {
    "visitors":    {"label": "访客数",     "type": "int", "required": True,  "default": 0,   "min": 0},
    "clicks":      {"label": "点击数",     "type": "int", "required": False, "default": 0,   "min": 0},
    "orders":      {"label": "订单数",     "type": "int", "required": False, "default": 0,   "min": 0},
    "revenue":     {"label": "收入(元)",   "type": "float", "required": False, "default": 0.0, "min": 0.0},
    "add_to_cart": {"label": "加购数",     "type": "int", "required": False, "default": 0,   "min": 0},
    "impressions": {"label": "曝光数",     "type": "int", "required": False, "default": 0,   "min": 0},
    "stay_seconds":{"label": "停留时长(秒)","type": "float", "required": False, "default": 0.0, "min": 0.0},
}
```

### 第二步：每个实验方法声明自己的配置文件

```python
# MAB 实验 — 只关注 CTR
METRICS_CONFIG_MAB = {
    "input_fields":  ["visitors", "clicks"],           # 输入表显示哪些列
    "output_metrics": ["ctr"],                          # 结果表显示哪些指标
    "primary_metric": "ctr",                            # 决策用的核心指标
}

# BOTW 实验 — 只关注 CTR（论文原文如此）
METRICS_CONFIG_PAPER = {
    "input_fields":  ["visitors", "clicks"],
    "output_metrics": ["ctr"],
    "primary_metric": "ctr",
}

# 示例：一个关注转化率的新实验
METRICS_CONFIG_CONVERSION = {
    "input_fields":  ["visitors", "clicks", "orders", "revenue"],
    "output_metrics": ["ctr", "cvr", "rpm"],
    "primary_metric": "cvr",
}

# 示例：一个关注全链路的新实验
METRICS_CONFIG_FUNNEL = {
    "input_fields":  ["visitors", "impressions", "clicks", "add_to_cart", "orders", "revenue"],
    "output_metrics": ["ctr", "cvr", "aov", "rpm"],
    "primary_metric": "rpm",
}
```

### 第三步：AI 先建议 metrics_config，用户确认后再定

新增实验时，不允许 AI 直接拍脑袋写死表格字段。必须先根据实验目标给出建议，然后等待用户确认。

AI 必须输出以下内容：

```python
METRICS_CONFIG_XXX = {
    "name": "实验名称",
    "input_fields": ["visitors", "clicks"],
    "output_metrics": ["ctr"],
    "primary_metric": "ctr",
}
```

同时说明：

- 为什么选择这些输入字段
- 为什么选择这些输出指标
- 为什么主指标是 `primary_metric`
- 是否需要围栏指标，例如加购率、订单数、收入、停留时长
- 用户确认前，不创建新页面、不改模板字段

项目已提供后端建议接口：

```bash
POST /api/metrics/suggest
Content-Type: application/json

{"experiment_goal": "测试新主图对转化率和收入的影响"}
```

返回内容包含：

- `preset`：建议使用的预设类型
- `reason`：推荐理由
- `metrics_config`：建议配置
- `need_user_confirm: true`：表示必须用户确认后才能作为最终配置

常见判断规则：

| 用户目标 | AI 建议 input_fields | AI 建议 primary_metric |
|----------|----------------------|-------------------------|
| 看主图/素材点击好不好 | visitors, clicks | ctr |
| 看下单转化 | visitors, clicks, orders, revenue | cvr |
| 看收入/GMV/ROI | visitors, impressions, clicks, add_to_cart, orders, revenue | rpm |
| 看围栏指标/漏斗 | visitors, impressions, clicks, add_to_cart, orders, revenue | rpm |

用户确认后，才把配置写入 `app.py`，并在路由里传入该配置。

### 第四步：parse_daily_data 改造为通用解析器

当前 `parse_daily_data` 硬编码了 `visitors` 和 `clicks`。改成一个循环，根据 `metrics_config["input_fields"]` 动态读取：

```python
def parse_daily_data(form_data, file_data, metrics_config=None):
    if metrics_config is None:
        metrics_config = METRICS_CONFIG_MAB  # 兜底

    dates = form_data.getlist("date[]")
    if not dates:
        return DEFAULT_DAILY_DATA

    unique_dates = sorted(set(dates))
    input_fields = metrics_config["input_fields"]

    for date in unique_dates:
        prefix = f"{date.replace('-', '')}_"
        names = form_data.getlist(f"{prefix}name[]")
        image_types = form_data.getlist(f"{prefix}image_type[]")
        image_paths = form_data.getlist(f"{prefix}image_path[]")
        image_files = file_data.getlist(f"{prefix}image_file[]")

        # ===== 关键改动：动态读取指标 =====
        field_data = {}
        for field_key in input_fields:
            meta = METRICS[field_key]
            raw = form_data.getlist(f"{prefix}{field_key}[]")
            parsed = []
            for v in raw:
                try:
                    val = float(v) if meta["type"] == "float" else int(v)
                    parsed.append(max(val, meta["min"]))
                except (ValueError, TypeError):
                    parsed.append(meta["default"])
            field_data[field_key] = parsed
        # =================================

        day_data = []
        for idx in range(len(names)):
            item = {
                "name": (names[idx] or f"主图{idx + 1}").strip(),
                "image_type": (image_types[idx] or "未分类").strip(),
                "image_path": image_paths[idx].strip() if idx < len(image_paths) else "",
            }
            for field_key in input_fields:
                item[field_key] = field_data[field_key][idx] if idx < len(field_data[field_key]) else METRICS[field_key]["default"]
            if item.get("clicks", 0) > item.get("visitors", 0):
                item["clicks"] = item["visitors"]
            if item.get("orders", 0) > item.get("clicks", 0):
                item["orders"] = item["clicks"]
            day_data.append(item)

        if day_data:
            daily_data.append({"date": date, "data": day_data})

    return daily_data if daily_data else DEFAULT_DAILY_DATA
```

### 第四步：路由透传 metrics_config

```python
@app.route("/epsilon-greedy", methods=["GET", "POST"])
def epsilon_greedy():
    # ...
    if request.method == "POST":
        daily_data = parse_daily_data(request.form, request.files, METRICS_CONFIG_CONVERSION)
    # ...
    results = compute_results(daily_data, METRICS_CONFIG_CONVERSION)
    return render_template("epsilon-greedy.html", ..., metrics_config=METRICS_CONFIG_CONVERSION)
```

### 第五步：compute_results 支持多指标

在不改动现有逻辑的前提下，新增一个通用聚合函数：

```python
def compute_results(daily_data, metrics_config=None):
    if metrics_config is None:
        metrics_config = METRICS_CONFIG_MAB

    input_fields = metrics_config["input_fields"]
    output_metrics = metrics_config["output_metrics"]

    variant_totals = {}
    for day in daily_data:
        for item in day["data"]:
            name = item["name"]
            if name not in variant_totals:
                variant_totals[name] = {
                    "name": name,
                    "image_type": item["image_type"],
                    "image_path": item.get("image_path", ""),
                    "daily": [],
                }
                for f in input_fields:
                    variant_totals[name][f"total_{f}"] = 0

            for f in input_fields:
                variant_totals[name][f"total_{f}"] += item.get(f, 0)

            variant_totals[name]["daily"].append({
                "date": day["date"],
                **{f: item.get(f, 0) for f in input_fields},
            })

    # ... 后续逻辑中，把计算 CTR 的地方扩展为遍历 output_metrics 的循环

    return { "rows": ..., "metrics_config": metrics_config, ... }
```

### 第六步：模板端根据 metrics_config 渲染表格

输入表格表头：
```html
{% for field_key in metrics_config.input_fields %}
<th>{{ metrics_meta[field_key].label }}</th>
{% endfor %}
```

输入表格表体：
```html
{% for field_key in metrics_config.input_fields %}
<td><input type="number" min="0" name="{{ prefix }}{{ field_key }}[]" value="{{ item.get(field_key, 0) }}"></td>
{% endfor %}
```

结果表格同理，用 `metrics_config.output_metrics` 循环渲染。

### 第七步：模板中提供 metrics_meta

路由中把 `METRICS` 也传到模板：
```python
return render_template("xxx.html", ..., metrics_config=..., metrics_meta=METRICS)
```

---

## 数据模型

每个变体每行的字段取决于该实验的 `metrics_config.input_fields`。以下为全量字段：

```json
{
  "name": "主图1",
  "image_type": "白底图",
  "image_path": "uploads/xxx.png",
  "visitors": 400,
  "clicks": 32,
  "orders": 8,
  "revenue": 1280.50,
  "add_to_cart": 25,
  "impressions": 5000,
  "stay_seconds": 45.2
}
```

`visitors` 为必填字段，其余按需使用。没用的字段不填或填 0。

MySQL 表 `experiments` 用 `method` 列区分实验类型，`daily_data` 列存以上 JSON。**不要改 MySQL 表结构。**

---

## 指标计算公式速查

| 输出指标 | 输入字段 | 公式 |
|----------|----------|------|
| `ctr` | visitors, clicks | clicks / visitors |
| `cvr` | visitors, orders | orders / visitors |
| `rpm` | visitors, revenue | revenue / visitors × 1000 |
| `aov` | orders, revenue | revenue / orders |
| `add_to_cart_rate` | visitors, add_to_cart | add_to_cart / visitors |
| `avg_stay` | visitors, stay_seconds | stay_seconds / visitors |

所有指标都能用 `confidence_interval(rate, visitors)` 算出置信区间。

---

## 关键约束

- **不要拆 app.py** — 项目约定单文件后端
- **不要改 experiments 表结构** — 新字段只在 daily_data JSON 中扩展
- **CSS 统一变量** — `var(--primary)` 等，详见 DEV_SPEC.md §4.2
- **JS 函数统一** — collectFormData / exportData / previewImage 等，详见 DEV_SPEC.md §5
- **所有页面导航要一致** — 每加一个方法，三个已有页面都要加链接
- **metrics_config 驱动一切** — 输入表格、结果表格、算法计算全部由它控制

---

## 现有页面入口

| 路由 | 方法 | 指标 | 模板 |
|------|------|------|------|
| `/` | MAB 多臂老虎机 | CTR | index.html |
| `/paper` | Best of Three Worlds | CTR | paper.html |
| `/compare` | 左右对比 | CTR | compare.html |
| `/export/pdf` | 打印报告 | CTR | export.html |

---

*给 AI 助手：新增实验方法时，先读 DEV_SPEC.md 掌握全貌，再按本 README 的 7 步 + 7 步（多指标）操作。每个实验方法自己声明自己的 metrics_config，不要改动已有方法的指标配置。*
