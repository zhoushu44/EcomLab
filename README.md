# EcomLab - E-commerce Experiment Testing Platform

基于多臂老虎机算法的电商主图智能测试系统，助力商家科学优化点击率。

## 功能特点

- **📊 数据驱动决策** — 自动计算置信区间、检测功效等统计指标
- **⚡ 动态流量分配** — 智能调控流量，让优质主图获得更多曝光
- **📈 多日数据追踪** — 支持连续多天数据录入与趋势分析
- **💡 小白友好** — 鼠标悬停即可查看指标说明与计算公式

## 技术实现

- **后端**: Flask 2.x
- **算法**: UCB (Upper Confidence Bound) 多臂老虎机
- **统计**: 95% 二项式置信区间

## 安装运行

```bash
# 安装依赖
pip install flask

# 启动服务
python app.py

# 访问地址
http://127.0.0.1:5000
```

## 使用方法

1. 在每日数据表格中填写主图的访客数和点击数
2. 点击「添加新日期」添加更多天数数据
3. 点击「计算累计结果」获取分析报告
4. 查看实验总览、每日趋势和 MAB 动态分流建议

## 项目结构

```
├── app.py                    # Flask 后端应用
├── templates/
│   └── index.html            # 前端页面
├── EXPERIMENT_SPECIFICATION.md  # 实验测试规范文档
└── README.md                 # 项目说明文档
```

## 参考论文

基于论文《Multi Armed Bandit vs. A/B Tests in E-commerce》实现

---

**EcomLab** - 让数据驱动电商决策