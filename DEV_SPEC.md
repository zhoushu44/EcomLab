# EcomLab 开发规范

## 适用场景

所有在 EcomLab 项目中**新增实验方法页**的开发工作，须遵循本规范。本规范确保多个实验方法的行为一致、代码可维护、前后端无遗漏。

---

## 1. 项目架构速览

```
EcomLab/
├── app.py                    # Flask 后端（唯一后端文件）
├── DEV_SPEC.md               # 本规范
├── EXPERIMENT_SPECIFICATION.md  # 实验功能规范（面向用户）
├── templates/
│   ├── index.html            # MAB 多臂老虎机
│   ├── paper.html            # Best of Three Worlds
│   ├── compare.html          # 左右对比
│   └── export.html           # 打印报告
└── static/uploads/           # 图片上传目录（运行时自建）
```

关键约束：

- **单文件后端**：不做 views/models/utils 拆分，所有逻辑在 `app.py` 内。
- **模板直出**：无前端构建，CSS/JS 内联在 `<style>` / `<script>` 中。
- **MySQL 单表**：`experiments` 表存所有实验，`method` 字段区分方法类型。

---

## 2. 数据库规范

### 2.1 表结构（已存在，禁止修改）

```sql
CREATE TABLE experiments (
    id          VARCHAR(36) PRIMARY KEY,        -- UUID
    title       VARCHAR(200) NOT NULL DEFAULT '',
    method      VARCHAR(20)  NOT NULL DEFAULT 'mab',
    daily_data  LONGTEXT     NOT NULL,          -- JSON
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 2.2 新增方法时的数据库操作

新增实验方法**不需要改表**。只需要在保存实验时指定新的 `method` 值（如 `'epsilon-greedy'`），加载/列表筛选时用对应 method 即可。

### 2.3 `daily_data` JSON 结构（已固定，新增方法也沿用）

```json
[
  {
    "date": "2024-01-01",
    "data": [
      {
        "name": "主图1",
        "image_type": "白底图",
        "image_path": "uploads/xxx.png",
        "visitors": 400,
        "clicks": 32
      }
    ]
  }
]
```

**允许给 `data[].item` 新增指标字段**，但必须来自 `app.py` 里的 `METRICS` 注册表，并且必须由该实验方法自己的 `metrics_config.input_fields` 声明。基础字段 `name`、`image_type`、`image_path` 保持不变。方法特有的中间计算结果在 `compute_results()` 返回的 dict 里扩展，不写入 daily_data。

---

## 3. 新增实验方法 — 标准步骤（7 步）

以新增一个假设的方法 `my-method` 为例：

### 3.1 步骤一：确定 method 常量

在 `app.py` 中为该方法定义 method 字符串（如 `'my-method'`），用于路由、数据库筛选、模板差异化。

### 3.2 步骤二：添加页面路由

在 `app.py` 中新增路由，必须以 `/paper` 的代码为模板复制，不能从零写：

```python
@app.route("/my-method", methods=["GET", "POST"])
def my_method():
    daily_data = DEFAULT_DAILY_DATA
    experiment_id = request.args.get("id", "")
    experiment_title = ""
    if experiment_id:
        loaded = load_experiment(experiment_id)
        if loaded:
            daily_data = loaded["daily_data"]
            experiment_title = loaded["title"]

    if request.method == "POST":
        daily_data = parse_daily_data(request.form, request.files)
        experiment_id = request.form.get("experiment_id", "") or uuid.uuid4().hex
        experiment_title = request.form.get("experiment_title", "") or "MY-METHOD 实验"
        save_experiment(experiment_id, experiment_title, "my-method", daily_data)

    results = compute_results(daily_data)
    experiments = list_experiments("my-method")
    return render_template(
        "my-method.html",
        daily_data=daily_data,
        results=results,
        experiment_id=experiment_id,
        experiment_title=experiment_title,
        experiments=experiments,
    )
```

路由必须满足的规则：

- 支持 `GET` 显示默认/已加载数据
- 支持 `POST` 接收表单 + 自动保存到 MySQL
- `?id=xxx` 加载已有实验
- 透传 `experiment_id`、`experiment_title`、`experiments` 到模板

### 3.3 步骤三：创建模板文件

以 `paper.html` 为模板复制，命名为 `my-method.html`。

复制后逐区域替换：

| 替换项 | 说明 |
|--------|------|
| 页面标题 `<title>` | 改为方法名称 |
| Hero 区块 `h1` 和 `p` | 方法介绍文案 |
| `.hero-badges` 里的 `.badge` | 方法特征标签 |
| 导航下拉菜单 | 新增本页面为 `active`，其他页面对应链接 |
| "计算累计结果"按钮旁 | 实验名占位符改为方法专属默认名 |
| 结果区列 | 根据方法特点增加/删除列 |
| "小白解读"区块 | 替换为该方法的通俗解释 |
| "操作建议"区块 | 替换为该方法的流程建议 |
| JS `saveExperiment('paper')` 调用 | 改为 `saveExperiment('my-method')` |
| 变量名"变体"/"主图" | 根据方法语境统一 |
| 加载实验的 URL | 改为 `'/my-method?id='` |

### 3.4 步骤四：注册导航链接

在**所有页面**的 `<details class="page-switcher">` 菜单中增加对 `/my-method` 的链接项：

```html
<div class="page-menu">
    <a class="page-option" href="/">MAB 多臂老虎机</a>
    <a class="page-option" href="/paper">Best of Three Worlds</a>
    <a class="page-option active" href="/my-method">MY-METHOD</a>
    <a class="page-option" href="/compare">左右对比</a>
</div>
```

### 3.5 步骤五：确认计算逻辑

默认情况下，`compute_results(daily_data)` 返回的 result dict 已包含所有 MAB 和 BOTW 所需字段，新方法可直接使用。但如果新方法需要特殊指标：

- 在 `compute_results()` 函数内部（或独立新增小函数）加入差异化逻辑
- 在返回 dict 的 `summary` 或顶层扩展新 key
- 模板端用 `{% if %}` 条件渲染

**禁止**为单一方法新增路由级计算函数。计算逻辑入口始终是 `compute_results()`。

### 3.6 步骤六：数据库自动保存

POST 流程已经自动调用 `save_experiment()`。无需额外操作。确保 `list_experiments()` 调用时传入正确的 method 筛选。

### 3.7 步骤七：验证清单

- [ ] `/my-method` GET 返回 200
- [ ] `/my-method` POST 返回 200
- [ ] 数据提交后 experiment_id 出现在页面 HTML 中
- [ ] `/api/list?method=my-method` 返回该实验
- [ ] 所有页面的导航下拉菜单都有新方法入口
- [ ] 无 Jinja2 模板错误
- [ ] 无 Python 语法错误

---

## 4. 模板结构规范

### 4.1 页面必须包含的区块（从上到下）

```
1. CSS 变量定义  (.container / .card / .hero / .explain / .btn 等)
2. 页面切换器    (.page-switcher 下拉)
3. Hero 介绍     (h1 + p + .hero-badges)
4. 数据录入卡    (form > .actions + #daily-containers)
5. 实验总览      (.summary .metric × N)
6. 阶段判断      (.phase-box)
7. 决策推荐卡    (.decision-board)
8. 每日CTR趋势   (.trend-card)
9. 结果表        (thead 含 .tooltip-wrapper)
10. 消除轨迹     (仅 BOTW 类方法)
11. 终止条件     (仅 BOTW 类方法)
12. 操作建议     (.explain)
13. 小白解读     (方法论通俗版)
14. JS 脚本      (collectFormData / exportData / 增删行/日逻辑)
```

其中 4-9 为**强制区块**，10-13 为**可选区块**。

### 4.2 CSS 变量体系（强制使用）

```css
:root {
    --bg: #f3f6fb;
    --card: #ffffff;
    --primary: #2563eb;
    --primary-soft: #dbeafe;
    --primary-deep: #1d4ed8;
    --text: #1f2937;
    --muted: #6b7280;
    --border: #e5e7eb;
    --good: #16a34a;
    --warn: #d97706;
    --danger: #dc2626;
    --info: #0f766e;
}
```

**禁止**自定义新的颜色变量名（如 `--card-bg`、`--accent`），必须使用上表中已有变量。

### 4.3 共用 UI 类名

| 类名 | 用途 |
|------|------|
| `.container` | max-width:1280px 页面容器 |
| `.card` | 白色圆角卡片 |
| `.hero` / `.hero-badges` / `.badge` | 顶部介绍 |
| `.summary` / `.metric` | 四列指标网格 |
| `.phase-box` | 阶段提示条 |
| `.decision-board` / `.decision-card` / `.highlight` | 推荐卡片 |
| `.trend-card` / `.trend-header` / `.trend-bars` / `.trend-bar` | CTR趋势图 |
| `.tag` / `.tag-good` / `.tag-mid` / `.tag-danger` / `.tag-info` | 状态标签 |
| `.tooltip-wrapper` / `.tooltip-icon` / `.tooltip-content` / `.formula` | 指标提示 |
| `.explain` | 说明文字块 |
| `.bottom-grid` | 双列说明布局 |
| `.btn` / `.btn-primary` / `.btn-secondary` | 按钮 |
| `.actions` | 按钮组容器 |
| `.daily-section` / `.daily-header` / `.daily-table` | 每日数据录入 |
| `.paper-box` | 提示框 |

新增方法页不得自定义同义类名，必须复用以上。

### 4.4 响应式断点（统一）

```css
@media (max-width: 1024px) { /* 两列 → 单列 */ }
@media (max-width: 720px)  { /* 手机适配 */ }
```

---

## 5. JS 函数规范

### 5.1 必须存在的函数

每个方法页 `script` 中必须有（从 paper.html 复制）：

| 函数 | 用途 |
|------|------|
| `collectVariantRows()` | 从第一日表格读取变体列表 |
| `buildDayTR(name, type, path, isFirstDay, editable)` | 生成一行表格 HTML |
| `addVariantRow()` | 新增一行变体（同步到所有天） |
| `removeVariantRow(button)` | 删除一行变体（同步到所有天） |
| `addNewDay()` | 新增一日期块 |
| `removeDay(button)` | 删除一日期块 |
| `updateDayNumbers()` | 更新"第 N 天"文案 |
| `updateInputNames()` | 按日期前缀重命名输入框 name |
| `previewImage(input)` | FileReader 即时预览 |
| `collectFormData()` | 从表单收集 daily_data |
| `exportData()` | 导出 JSON Blob 下载 |
| `saveExperiment(method)` | 通过 `/api/save` 保存 |

### 5.2 禁止的行为

- 在 `document.addEventListener('change', ...)` 中重复绑定（index.html 和 paper.html 各绑了一次 date[] change，保持即可）
- 自定义不同的表单字段名映射——必须用 `YYYYMMDD_image_path[] / _name[] / _image_type[] / _visitors[] / _clicks[]`

---

## 6. 后端函数规范

### 6.1 共享计算引擎

所有方法共用一个 `compute_results(daily_data)`，返回 dict 结构：

```python
{
    "rows": [...],              # 每个变体的统计指标
    "average_ctr": float,
    "best_variant": {...},
    "total_visitors": int,
    "total_clicks": int,
    "summary": {                # compute_summary() 输出
        "phase": str,
        "winner_ready": bool,
        "overlap_count": int,
        "termination_text": str,
        "elimination_count": int,
        ...
    },
    "days_count": int,
    "experiment_trace": [...],  # 消除轨迹
    "elimination_events": [...],# 消除事件列表
}
```

### 6.2 新增方法专属计算的规则

如果需要方法特有的统计逻辑：

1. 在 `compute_results()` 返回 dict 中扩展新 key
2. 在 `compute_summary()` 中扩展 summary 字段
3. 模板端 `{% if %}` 条件渲染

例如当前 `compute_results()` 已为 BOTW 扩展：
- `experiment_trace`
- `elimination_events`
- `summary.terminated` / `summary.winner_name`

**禁止**为单一方法新建独立的 compute 函数。

### 6.3 数据库函数（已存在，只调不改）

- `get_db()` → 每次新建 pymysql 连接
- `init_db()` → 建表（模块导入时自动执行一次）
- `save_experiment(id, title, method, daily_data)` → UPSERT
- `load_experiment(id)` → 按 ID 加载
- `list_experiments(method="")` → 列表，最多 50 条

### 6.4 图片上传

- 统一调用 `save_uploaded_image(upload_file)` → 返回 `"uploads/{uuid}.{ext}"`
- 存储路径：`static/uploads/`
- 表单必须 `enctype="multipart/form-data"`

---

## 7. 命名规范

| 类别 | 规范 | 示例 |
|------|------|------|
| Python 函数 | snake_case | `compute_results` |
| Python 变量 | snake_case | `daily_data` |
| 路由路径 | kebab-case 或小写 | `/my-method` |
| 模板文件 | 小写 + .html | `my-method.html` |
| method 字段 | 小写 + 短横线 | `my-method` |
| CSS 类名 | kebab-case | `.daily-section` |
| JS 函数 | camelCase | `collectFormData` |
| 表单字段前缀 | YYYYMMDD_ | `20240101_` |
| 图片目录 | static/uploads/ | 固定 |

---

## 8. 代码风格

### 8.1 Python

- 无分号结尾
- 字符串用双引号（除非含双引号）
- 导入顺序：标准库 → 第三方库 → 本地

### 8.2 HTML/模板

- 缩进 4 空格
- Jinja2 `{% %}` 和 `{{ }}` 前后加空格（`{% if %}` 不是 `{%if%}`）
- 长属性换行时对齐

### 8.3 CSS

- 所有颜色用 `var(--xxx)`，不写死 `#xxxxxx`
- 禁止 `!important`

### 8.4 JavaScript

- 用 `const`/`let`，不用 `var`
- 模板字符串用反引号
- 箭头函数优先级低于 function 声明（function 声明有提升，更稳定）

---

## 9. 新增方法自查清单

- [ ] method 常量已确定，不与现有 mab/paper 重复
- [ ] `/my-method` GET/POST 路由已添加，代码从 `/paper` 复制修改
- [ ] 模板 `my-method.html` 已创建，从 `paper.html` 复制修改
- [ ] Hero 区块文案已替换
- [ ] `list_experiments("my-method")` 方法筛选已正确
- [ ] 所有页面导航下拉已新增本方法链接
- [ ] 实验名输入框 placeholder 已改
- [ ] `saveExperiment('my-method')` 调用已改（如有）
- [ ] 结果区列已调整，新增/删除列已同步表头和表体
- [ ] 小白解读区块已替换为方法相关内容
- [ ] 操作建议区块已替换
- [ ] `/my-method` GET 返回 200
- [ ] `/my-method` POST 返回 200 并自动保存到 DB
- [ ] `/api/list?method=my-method` 可查到实验
- [ ] 无 Jinja2 / Python 诊断错误
- [ ] Flask 服务正常启动

---

*最后更新：2026-05-01*
