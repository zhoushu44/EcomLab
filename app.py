import os
import json
import uuid
import io
import base64
from math import sqrt, log
from datetime import datetime

import pymysql
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_DIR = os.path.join(app.root_path, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MYSQL_HOST = "8.163.52.51"
MYSQL_PORT = 13306
MYSQL_USER = "root"
MYSQL_PASS = "LFajEj6Lw7tKfZ8z"
MYSQL_DB = "ecomlab"


def get_db():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASS,
        database=MYSQL_DB,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def init_db():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS experiments (
            id VARCHAR(36) PRIMARY KEY,
            title VARCHAR(200) NOT NULL DEFAULT '',
            method VARCHAR(20) NOT NULL DEFAULT 'mab',
            daily_data LONGTEXT NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    db.commit()
    cur.close()
    db.close()


init_db()

METRICS = {
    "visitors": {"label": "访客数", "type": "int", "required": True, "default": 0, "min": 0},
    "clicks": {"label": "点击数", "type": "int", "required": False, "default": 0, "min": 0},
    "orders": {"label": "订单数", "type": "int", "required": False, "default": 0, "min": 0},
    "revenue": {"label": "收入(元)", "type": "float", "required": False, "default": 0.0, "min": 0.0},
    "add_to_cart": {"label": "加购数", "type": "int", "required": False, "default": 0, "min": 0},
    "impressions": {"label": "曝光数", "type": "int", "required": False, "default": 0, "min": 0},
    "stay_seconds": {"label": "停留时长(秒)", "type": "float", "required": False, "default": 0.0, "min": 0.0},
}

OUTPUT_METRICS = {
    "ctr": {"label": "点击率", "format": "percent", "numerator": "clicks", "denominator": "visitors"},
    "cvr": {"label": "转化率", "format": "percent", "numerator": "orders", "denominator": "visitors"},
    "rpm": {"label": "千访客收入", "format": "currency", "numerator": "revenue", "denominator": "visitors", "multiplier": 1000},
    "aov": {"label": "客单价", "format": "currency", "numerator": "revenue", "denominator": "orders"},
    "cart_rate": {"label": "加购率", "format": "percent", "numerator": "add_to_cart", "denominator": "visitors"},
    "avg_stay_seconds": {"label": "平均停留时长", "format": "number", "numerator": "stay_seconds", "denominator": "visitors"},
}

METRICS_CONFIG_MAB = {
    "name": "MAB 多臂老虎机",
    "input_fields": ["visitors", "clicks"],
    "output_metrics": ["ctr"],
    "primary_metric": "ctr",
}

METRICS_CONFIG_PAPER = {
    "name": "Best of Three Worlds",
    "input_fields": ["visitors", "clicks"],
    "output_metrics": ["ctr"],
    "primary_metric": "ctr",
}

METRICS_CONFIG_PRESETS = {
    "mab": METRICS_CONFIG_MAB,
    "paper": METRICS_CONFIG_PAPER,
    "conversion": {
        "name": "转化率实验",
        "input_fields": ["visitors", "clicks", "orders", "revenue"],
        "output_metrics": ["ctr", "cvr", "rpm"],
        "primary_metric": "cvr",
    },
    "funnel": {
        "name": "漏斗实验",
        "input_fields": ["visitors", "impressions", "clicks", "add_to_cart", "orders", "revenue"],
        "output_metrics": ["ctr", "cart_rate", "cvr", "aov", "rpm"],
        "primary_metric": "rpm",
    },
}

METRICS_CONFIG_SUGGESTION_RULES = [
    {"keywords": ["收入", "roi", "利润", "gmv", "客单价"], "preset": "funnel", "reason": "目标关注商业收益，需要收入、订单和漏斗数据，主指标建议 RPM。"},
    {"keywords": ["围栏", "漏斗", "加购", "收藏"], "preset": "funnel", "reason": "目标包含围栏/漏斗指标，需要覆盖曝光、点击、加购、订单和收入。"},
    {"keywords": ["转化", "成交", "订单", "cvr"], "preset": "conversion", "reason": "目标进入成交链路，需要订单数和收入，主指标建议 CVR。"},
    {"keywords": ["点击", "主图", "素材", "ctr"], "preset": "mab", "reason": "目标集中在点击表现，用访客数和点击数计算 CTR 即可。"},
]
DEFAULT_DAILY_DATA = [
    {"date": "2024-01-01", "data": [
        {"name": "主图1", "image_type": "白底图", "visitors": 400, "clicks": 32},
        {"name": "主图2", "image_type": "场景图", "visitors": 390, "clicks": 38},
        {"name": "主图3", "image_type": "细节图", "visitors": 405, "clicks": 30},
    ]},
    {"date": "2024-01-02", "data": [
        {"name": "主图1", "image_type": "白底图", "visitors": 420, "clicks": 35},
        {"name": "主图2", "image_type": "场景图", "visitors": 410, "clicks": 39},
        {"name": "主图3", "image_type": "细节图", "visitors": 430, "clicks": 32},
    ]},
    {"date": "2024-01-03", "data": [
        {"name": "主图1", "image_type": "白底图", "visitors": 380, "clicks": 29},
        {"name": "主图2", "image_type": "场景图", "visitors": 380, "clicks": 33},
        {"name": "主图3", "image_type": "细节图", "visitors": 380, "clicks": 26},
    ]},
]


def save_uploaded_image(upload_file):
    if not upload_file or not getattr(upload_file, "filename", ""):
        return ""
    filename = secure_filename(upload_file.filename)
    _, ext = os.path.splitext(filename)
    saved_name = f"{uuid.uuid4().hex}{ext.lower() if ext else '.png'}"
    saved_path = os.path.join(UPLOAD_DIR, saved_name)
    upload_file.save(saved_path)
    return f"uploads/{saved_name}"


def safe_divide(a, b):
    return a / b if b else 0.0


def calculate_output_metric(totals, metric_key):
    formula = OUTPUT_METRICS.get(metric_key)
    if not formula:
        return 0.0
    numerator = totals.get(formula["numerator"], 0)
    denominator = totals.get(formula["denominator"], 0)
    value = safe_divide(numerator, denominator)
    return value * formula.get("multiplier", 1)


def calculate_output_metrics(totals, metrics_config=None):
    config = normalize_metrics_config(metrics_config)
    return {
        metric_key: calculate_output_metric(totals, metric_key)
        for metric_key in config["output_metrics"]
    }


def confidence_interval(rate, visitors, z=1.96):
    if visitors <= 0:
        return 0.0, 0.0
    margin = z * sqrt(max(rate * (1 - rate), 0) / visitors)
    return max(0.0, rate - margin), min(1.0, rate + margin)


def reliability_level(ci_low, ci_high):
    width = ci_high - ci_low
    if width < 0.05:
        return "高可靠"
    if width < 0.1:
        return "中可靠"
    return "低可靠"


def power_level(visitors):
    if visitors > 500:
        return "高识别力"
    if visitors > 200:
        return "中识别力"
    return "低识别力"


def stage_label(total_visitors_per_variant):
    if total_visitors_per_variant < 200:
        return "探索期"
    if total_visitors_per_variant < 500:
        return "平衡观察期"
    return "决策期"


def recommendation(reliability, power, ctr, average_ctr, comparison):
    if comparison == "显著领先" and reliability == "高可靠" and power == "高识别力":
        return "可逐步提升到核心流量，准备作为候选主图"
    if comparison == "显著落后" and reliability != "低可靠":
        return "建议持续降流量，保留少量探索即可"
    if reliability == "低可靠" or power == "低识别力":
        return "先保留探索流量，不要过早淘汰"
    if ctr >= average_ctr:
        return "建议增加流量 10%~20%"
    return "建议保持当前流量"


def sequential_margin(visitors, day_index, alpha=0.05):
    if visitors <= 0:
        return 1.0
    spent_alpha = max(alpha / max(day_index + 1, 1), 1e-6)
    margin = sqrt(log(2 / spent_alpha) / (2 * visitors))
    return min(1.0, margin)


def intervals_overlap(low_a, high_a, low_b, high_b):
    return max(low_a, low_b) <= min(high_a, high_b)


def comparison_label(row, best_row):
    if row["name"] == best_row["name"]:
        best_threshold = best_row.get("second_best_gain_high", best_row.get("second_best_ci_high", 0))
        return "显著领先" if row.get("gain_low", row["ci_low"]) > best_threshold else "暂时领先"
    if row.get("gain_high", row["ci_high"]) < best_row.get("gain_low", best_row["ci_low"]):
        return "显著落后"
    if intervals_overlap(row["ci_low"], row["ci_high"], best_row["ci_low"], best_row["ci_high"]):
        return "结果未拉开"
    return "接近领先"


def compute_summary(rows, average_ctr, total_visitors):
    if not rows:
        return {
            "phase": "探索期",
            "ab_conclusion": "暂无数据",
            "mab_conclusion": "暂无数据",
            "paper_hint": "请先录入主图测试数据。",
            "winner_ready": False,
            "overlap_count": 0,
        }

    visitors_per_variant = safe_divide(total_visitors, len(rows))
    phase = stage_label(visitors_per_variant)
    sorted_rows = sorted(rows, key=lambda row: row["mab_share"], reverse=True)
    best_row = sorted_rows[0]
    overlap_count = sum(
        1
        for row in rows
        if row["name"] != best_row["name"]
        and intervals_overlap(row["ci_low"], row["ci_high"], best_row["ci_low"], best_row["ci_high"])
    )
    winner_ready = best_row["reliability"] == "高可靠" and best_row["power"] == "高识别力" and overlap_count == 0

    if overlap_count > 0:
        ab_conclusion = "固定分流逻辑下，主图差异还未完全拉开，持续均分流量会继续消耗表现较弱主图的曝光。"
    else:
        ab_conclusion = "固定分流逻辑下已经能看出主图层级，但仍会让落后主图持续分走固定流量。"

    if winner_ready:
        mab_conclusion = f"MAB 已识别出更稳的优胜主图：{best_row['name']}，可以进入最终上线候选。"
    elif phase == "探索期":
        mab_conclusion = "当前更适合继续探索，MAB 应保持所有主图都有基础曝光，同时把更多流量倾向高潜力图片。"
    else:
        mab_conclusion = "当前更适合用 MAB 做动态分流，先放大领先主图，同时保留未完全证伪的备选图。"

    if len(rows) >= 3 and overlap_count > 0:
        paper_hint = "这更符合论文强调的电商常见场景：多变体、细微差异、区间重叠明显，此时 MAB 通常比固定均分更省流量。"
    elif winner_ready:
        paper_hint = "这更接近论文里适合下结论的状态：优胜图区间更稳、识别力更高，可从实验转向上线。"
    else:
        paper_hint = "论文强调要同时看置信区间和检验功效，而不是只看当前点击率高低。"

    return {
        "phase": phase,
        "ab_conclusion": ab_conclusion,
        "mab_conclusion": mab_conclusion,
        "paper_hint": paper_hint,
        "winner_ready": winner_ready,
        "overlap_count": overlap_count,
        "best_name": best_row["name"],
        "best_share": best_row["mab_share"],
        "average_ctr": average_ctr,
    }


def build_variant_snapshot(cumulative_totals, active_names, total_visitors_so_far, baseline_rate, day_index):
    snapshots = []
    for name in active_names:
        item = cumulative_totals[name]
        visitors = item["total_visitors"]
        clicks = item["total_clicks"]
        ctr = safe_divide(clicks, visitors)
        ci_low, ci_high = confidence_interval(ctr, visitors)
        reliability = reliability_level(ci_low, ci_high)
        power = power_level(visitors)
        exploration_bonus = sqrt((2 * log(max(total_visitors_so_far, 2))) / max(visitors, 1)) if visitors > 0 else 1.0
        gain_rate = ctr - baseline_rate
        gain_low = ci_low - baseline_rate
        gain_high = ci_high - baseline_rate
        gain_margin = sequential_margin(visitors, day_index)
        gain_floor = gain_rate - gain_margin
        gain_ceiling = gain_rate + gain_margin
        snapshots.append({
            "name": name,
            "image_type": item["image_type"],
            "image_path": item.get("image_path", ""),
            "visitors": visitors,
            "clicks": clicks,
            "ctr": ctr,
            "ci_low": ci_low,
            "ci_high": ci_high,
            "ci_width": ci_high - ci_low,
            "reliability": reliability,
            "power": power,
            "exploration_bonus": exploration_bonus,
            "gain_rate": gain_rate,
            "gain_low": gain_floor if gain_floor < gain_low else gain_low,
            "gain_high": gain_ceiling if gain_ceiling > gain_high else gain_high,
            "gain_width": max(gain_ceiling, gain_high) - min(gain_floor, gain_low),
            "cumulative_gain": clicks - (baseline_rate * visitors),
            "mab_score": gain_rate + exploration_bonus,
        })
    return snapshots


def adaptive_allocation(snapshots, day_index):
    if not snapshots:
        return []
    if len(snapshots) == 1:
        return [1.0]
    if len(snapshots) >= 3 or day_index < 2:
        return [1 / len(snapshots)] * len(snapshots)

    ordered = sorted(snapshots, key=lambda row: (row["gain_high"], row["mab_score"]), reverse=True)
    best_row = ordered[0]
    second_row = ordered[1]
    if best_row["gain_low"] > second_row["gain_high"]:
        return [1.0 if row["name"] == best_row["name"] else 0.0 for row in snapshots]

    shares = []
    for row in snapshots:
        if row["name"] == best_row["name"]:
            shares.append(0.6)
        else:
            shares.append(0.4)
    return shares


def compute_results(daily_data, metrics_config=None):
    metrics_config = normalize_metrics_config(metrics_config)
    input_fields = metrics_config["input_fields"]
    variant_totals = {}

    for day in daily_data:
        for item in day["data"]:
            name = item["name"]
            if name not in variant_totals:
                variant_totals[name] = {
                    "name": name,
                    "image_type": item["image_type"],
                    "image_path": item.get("image_path", ""),
                    "total_visitors": 0,
                    "total_clicks": 0,
                    "totals": {field_key: 0 for field_key in input_fields},
                    "daily": [],
                }
            if item.get("image_path") and not variant_totals[name].get("image_path"):
                variant_totals[name]["image_path"] = item["image_path"]
            variant_totals[name]["total_visitors"] += item.get("visitors", 0)
            variant_totals[name]["total_clicks"] += item.get("clicks", 0)
            for field_key in input_fields:
                variant_totals[name]["totals"][field_key] += item.get(field_key, 0)
            daily_row = {
                "date": day["date"],
                "visitors": item.get("visitors", 0),
                "clicks": item.get("clicks", 0),
                "ctr": safe_divide(item.get("clicks", 0), item.get("visitors", 0)),
            }
            daily_row.update({field_key: item.get(field_key, 0) for field_key in input_fields})
            variant_totals[name]["daily"].append(daily_row)

    active_names = list(variant_totals.keys())
    cumulative_totals = {
        name: {
            "name": data["name"],
            "image_type": data["image_type"],
            "image_path": data.get("image_path", ""),
            "total_visitors": 0,
            "total_clicks": 0,
        }
        for name, data in variant_totals.items()
    }

    experiment_trace = []
    elimination_events = []
    termination_day = None
    winner_name = None
    terminated = False
    daily_impressions = 10000

    for day_index, day in enumerate(daily_data):
        active_before = active_names.copy()
        if not active_before:
            break

        before_visitors = sum(cumulative_totals[name]["total_visitors"] for name in active_before)
        before_clicks = sum(cumulative_totals[name]["total_clicks"] for name in active_before)
        baseline_rate_before = safe_divide(before_clicks, before_visitors)
        before_snapshots = build_variant_snapshot(
            cumulative_totals,
            active_before,
            max(before_visitors, 1),
            baseline_rate_before,
            day_index,
        )

        allocation_shares = adaptive_allocation(before_snapshots, day_index)
        allocation_mode = "均分探索"
        if len(active_before) == 2 and day_index >= 2:
            allocation_mode = "倾斜分流"
        elif len(active_before) == 1:
            allocation_mode = "全流量上线"

        allocation_items = []
        for snapshot, share in zip(before_snapshots, allocation_shares):
            allocation_items.append({
                "name": snapshot["name"],
                "share": share,
                "exposure": int(daily_impressions * share),
            })

        for item in day["data"]:
            name = item["name"]
            if name not in cumulative_totals:
                continue
            cumulative_totals[name]["total_visitors"] += item["visitors"]
            cumulative_totals[name]["total_clicks"] += item["clicks"]

        after_visitors = sum(cumulative_totals[name]["total_visitors"] for name in active_before)
        after_clicks = sum(cumulative_totals[name]["total_clicks"] for name in active_before)
        baseline_rate_after = safe_divide(after_clicks, after_visitors)
        after_snapshots = build_variant_snapshot(
            cumulative_totals,
            active_before,
            max(after_visitors, 1),
            baseline_rate_after,
            day_index,
        )

        eliminated_names = []
        elimination_reason_map = {}
        leader_name = None
        if len(active_before) > 1 and day_index >= 2:
            leader_snapshot = max(after_snapshots, key=lambda row: (row["gain_low"], row["ci_low"], row["mab_score"]))
            leader_name = leader_snapshot["name"]
            leader_gain_low = leader_snapshot["gain_low"]
            for row in after_snapshots:
                if row["name"] != leader_name and row["gain_high"] < leader_gain_low:
                    eliminated_names.append(row["name"])
                    elimination_reason_map[row["name"]] = f"累计收益上界 < {leader_name} 的累计收益下界"

        if eliminated_names:
            for name in eliminated_names:
                if name in active_names:
                    active_names.remove(name)
                elimination_events.append({
                    "day": day["date"],
                    "name": name,
                    "reason": elimination_reason_map[name],
                })
            if len(active_names) == 1:
                terminated = True
                winner_name = active_names[0]
                termination_day = day["date"]

        active_after_text = "、".join(active_names) if active_names else "无"
        eliminated_text = "无"
        if eliminated_names:
            eliminated_text = "；".join(
                f"{name}（{elimination_reason_map[name]}）" for name in eliminated_names
            )

        allocation_text = "；".join(
            f"{item['name']} {item['share'] * 100:.0f}%（{item['exposure']}）" for item in allocation_items
        )

        decision_text = "继续观察"
        if terminated and winner_name:
            decision_text = f"实验终止，全流量上线 {winner_name}"
        elif eliminated_names:
            decision_text = f"消除 {eliminated_text}，下一轮收缩到剩余主图"
        elif len(active_before) == 2 and day_index >= 2:
            decision_text = "两臂阶段进入 60/40 倾斜分流"
        elif len(active_before) >= 3:
            decision_text = "保持均分探索，等待区间进一步分离"

        experiment_trace.append({
            "day_label": f"第 {day_index + 1} 天",
            "date": day["date"],
            "active_before_text": "、".join(active_before),
            "active_after_text": active_after_text,
            "allocation_text": allocation_text,
            "allocation_mode": allocation_mode,
            "baseline_text": f"当前基准累计收益率 {baseline_rate_before * 100:.2f}%",
            "eliminated_text": eliminated_text,
            "decision_text": decision_text,
            "termination_text": f"实验终止，全流量上线 {winner_name}" if terminated else "继续观察",
            "leader_text": leader_name or "—",
        })

        if terminated:
            break

    variants = []
    for v in variant_totals.values():
        daily_data_v = v["daily"]
        max_daily_ctr = max(d["ctr"] for d in daily_data_v) if daily_data_v else 1.0
        for d in daily_data_v:
            d["max_ctr"] = max_daily_ctr
            d["bar_height"] = (d["ctr"] / max_daily_ctr) * 100 if max_daily_ctr > 0 else 0
            d["is_highest"] = d["ctr"] == max_daily_ctr
        variant_metrics = calculate_output_metrics(v.get("totals", {}), metrics_config)
        variants.append({
            "name": v["name"],
            "image_type": v["image_type"],
            "image_path": v.get("image_path", ""),
            "visitors": v["total_visitors"],
            "clicks": v["total_clicks"],
            "totals": v.get("totals", {}),
            "metrics": variant_metrics,
            "daily": v["daily"],
        })

    total_visitors = sum(v["visitors"] for v in variants)
    total_variants = len(variants) if variants else 1
    average_ctr = safe_divide(sum(v["clicks"] for v in variants), total_visitors)
    ab_share = 1 / total_variants if total_variants else 0
    scored_rows = []

    for item in variants:
        visitors = item["visitors"]
        clicks = min(item["clicks"], visitors) if visitors >= 0 else 0
        ctr = safe_divide(clicks, visitors)
        ci_low, ci_high = confidence_interval(ctr, visitors)
        reliability = reliability_level(ci_low, ci_high)
        power = power_level(visitors)
        exploration_bonus = sqrt((2 * log(max(total_visitors, 2))) / max(visitors, 1)) if visitors > 0 else 1.0
        gain_rate = ctr - average_ctr
        gain_margin = sequential_margin(visitors, max(len(daily_data) - 1, 0))
        gain_low = gain_rate - gain_margin
        gain_high = gain_rate + gain_margin
        mab_score = gain_rate + exploration_bonus

        scored_rows.append(
            {
                "name": item["name"],
                "image_type": item["image_type"],
                "image_path": item.get("image_path", ""),
                "visitors": visitors,
                "clicks": clicks,
                "ctr": ctr,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "ci_width": ci_high - ci_low,
                "reliability": reliability,
                "power": power,
                "ab_share": ab_share,
                "exploration_bonus": exploration_bonus,
                "gain_rate": gain_rate,
                "gain_low": gain_low,
                "gain_high": gain_high,
                "gain_width": gain_high - gain_low,
                "mab_score": mab_score,
                "metrics": item.get("metrics", {}),
                "totals": item.get("totals", {}),
                "daily": item.get("daily", []),
            }
        )

    mab_shares = adaptive_allocation(scored_rows, max(len(daily_data) - 1, 0))
    for row, share in zip(scored_rows, mab_shares):
        row["mab_share"] = share
        row["allocation_note"] = "全流量上线" if share >= 1 else "倾斜分流" if len(scored_rows) == 2 else "均分探索"

    sorted_by_share = sorted(scored_rows, key=lambda row: row["mab_share"], reverse=True)
    best_variant = sorted_by_share[0] if sorted_by_share else None
    second_best_ci_high = sorted_by_share[1]["ci_high"] if len(sorted_by_share) > 1 else 0
    second_best_gain_high = sorted_by_share[1]["gain_high"] if len(sorted_by_share) > 1 else 0
    if best_variant:
        best_variant["second_best_ci_high"] = second_best_ci_high
        best_variant["second_best_gain_high"] = second_best_gain_high

    for row in scored_rows:
        row["comparison"] = comparison_label(row, best_variant) if best_variant else "暂无判断"
        row["recommendation"] = recommendation(row["reliability"], row["power"], row["ctr"], average_ctr, row["comparison"])

    summary = compute_summary(scored_rows, average_ctr, total_visitors)
    winner_snapshot = winner_name or (best_variant["name"] if best_variant else None)
    summary.update({
        "termination_day": termination_day,
        "winner_name": winner_snapshot,
        "terminated": terminated,
        "termination_text": f"实验终止，全流量上线 {winner_snapshot}" if terminated and winner_snapshot else "实验尚未终止，继续观察流量分配、累计收益与消除结果。",
        "elimination_count": len(elimination_events),
        "active_names": active_names,
        "eliminated_names": [event["name"] for event in elimination_events],
    })

    return {
        "rows": scored_rows,
        "average_ctr": average_ctr,
        "best_variant": best_variant,
        "total_visitors": total_visitors,
        "total_clicks": sum(v["clicks"] for v in variants),
        "summary": summary,
        "days_count": len(daily_data),
        "experiment_trace": experiment_trace,
        "elimination_events": elimination_events,
        "metrics_config": metrics_config,
        "metrics_meta": METRICS,
        "output_metrics": OUTPUT_METRICS,
    }


def parse_metric_value(raw_value, metric_key):
    meta = METRICS[metric_key]
    default_value = meta["default"]
    try:
        if meta["type"] == "float":
            value = float(raw_value)
        else:
            value = int(raw_value)
    except (ValueError, TypeError):
        value = default_value
    return max(value, meta["min"])


def normalize_metrics_config(metrics_config=None):
    config = metrics_config or METRICS_CONFIG_MAB
    input_fields = [field for field in config.get("input_fields", []) if field in METRICS]
    if "visitors" not in input_fields:
        input_fields.insert(0, "visitors")
    if "clicks" not in input_fields:
        input_fields.append("clicks")
    return {
        **config,
        "input_fields": input_fields,
        "output_metrics": [metric for metric in config.get("output_metrics", ["ctr"]) if metric in OUTPUT_METRICS],
        "primary_metric": config.get("primary_metric", "ctr"),
    }


def suggest_metrics_config(experiment_goal):
    goal_text = (experiment_goal or "").lower()
    matched_rule = None
    for rule in METRICS_CONFIG_SUGGESTION_RULES:
        if any(keyword.lower() in goal_text for keyword in rule["keywords"]):
            matched_rule = rule
            break
    if not matched_rule:
        matched_rule = METRICS_CONFIG_SUGGESTION_RULES[0]
    preset_key = matched_rule["preset"]
    config = normalize_metrics_config(METRICS_CONFIG_PRESETS[preset_key])
    return {
        "preset": preset_key,
        "reason": matched_rule["reason"],
        "metrics_config": config,
        "input_fields_detail": [METRICS[field] for field in config["input_fields"]],
        "output_metrics_detail": [OUTPUT_METRICS[metric] for metric in config["output_metrics"]],
        "need_user_confirm": True,
    }


def parse_daily_data(form_data, file_data, metrics_config=None):
    config = normalize_metrics_config(metrics_config)
    dates = form_data.getlist("date[]")
    daily_data = []

    if not dates:
        return DEFAULT_DAILY_DATA

    unique_dates = sorted(set(dates))

    for date in unique_dates:
        if not date.strip():
            continue

        prefix = f"{date.replace('-', '')}_"
        names = form_data.getlist(f"{prefix}name[]")
        image_types = form_data.getlist(f"{prefix}image_type[]")
        image_paths = form_data.getlist(f"{prefix}image_path[]")
        image_files = file_data.getlist(f"{prefix}image_file[]")
        metric_lists = {
            field_key: form_data.getlist(f"{prefix}{field_key}[]")
            for field_key in config["input_fields"]
        }

        day_data = []
        for idx in range(len(names)):
            name = (names[idx] or f"主图{idx + 1}").strip()
            image_type = (image_types[idx] or "未分类").strip()
            image_path = image_paths[idx].strip() if idx < len(image_paths) else ""
            if idx < len(image_files):
                uploaded_path = save_uploaded_image(image_files[idx])
                if uploaded_path:
                    image_path = uploaded_path

            item_data = {
                "name": name,
                "image_type": image_type,
                "image_path": image_path,
            }
            for field_key, values in metric_lists.items():
                raw_value = values[idx] if idx < len(values) else METRICS[field_key]["default"]
                item_data[field_key] = parse_metric_value(raw_value, field_key)

            item_data["visitors"] = int(item_data.get("visitors", 0))
            item_data["clicks"] = int(min(item_data.get("clicks", 0), item_data["visitors"]))
            for field_key in config["input_fields"]:
                item_data.setdefault(field_key, METRICS[field_key]["default"])

            day_data.append(item_data)

        if day_data:
            daily_data.append({"date": date, "data": day_data})

    return daily_data if daily_data else DEFAULT_DAILY_DATA


@app.route("/", methods=["GET", "POST"])
def index():
    daily_data = DEFAULT_DAILY_DATA
    experiment_id = request.args.get("id", "")
    experiment_title = ""
    if experiment_id:
        loaded = load_experiment(experiment_id)
        if loaded:
            daily_data = loaded["daily_data"]
            experiment_title = loaded["title"]

    if request.method == "POST":
        daily_data = parse_daily_data(request.form, request.files, METRICS_CONFIG_MAB)
        experiment_id = request.form.get("experiment_id", "") or uuid.uuid4().hex
        experiment_title = request.form.get("experiment_title", "") or "MAB 实验"
        save_experiment(experiment_id, experiment_title, "mab", daily_data)

    results = compute_results(daily_data, METRICS_CONFIG_MAB)
    experiments = list_experiments("mab")
    return render_template(
        "index.html",
        daily_data=daily_data,
        results=results,
        experiment_id=experiment_id,
        experiment_title=experiment_title,
        experiments=experiments,
        metrics_config=METRICS_CONFIG_MAB,
        metrics_meta=METRICS,
        output_metrics=OUTPUT_METRICS,
    )


@app.route("/paper", methods=["GET", "POST"])
def paper():
    daily_data = DEFAULT_DAILY_DATA
    experiment_id = request.args.get("id", "")
    experiment_title = ""
    if experiment_id:
        loaded = load_experiment(experiment_id)
        if loaded:
            daily_data = loaded["daily_data"]
            experiment_title = loaded["title"]

    if request.method == "POST":
        daily_data = parse_daily_data(request.form, request.files, METRICS_CONFIG_PAPER)
        experiment_id = request.form.get("experiment_id", "") or uuid.uuid4().hex
        experiment_title = request.form.get("experiment_title", "") or "BOTW 实验"
        save_experiment(experiment_id, experiment_title, "paper", daily_data)

    results = compute_results(daily_data, METRICS_CONFIG_PAPER)
    experiments = list_experiments("paper")
    return render_template(
        "paper.html",
        daily_data=daily_data,
        results=results,
        experiment_id=experiment_id,
        experiment_title=experiment_title,
        experiments=experiments,
        metrics_config=METRICS_CONFIG_PAPER,
        metrics_meta=METRICS,
        output_metrics=OUTPUT_METRICS,
    )


@app.route("/compare", methods=["GET", "POST"])
def compare():
    daily_data = DEFAULT_DAILY_DATA
    if request.method == "POST":
        daily_data = parse_daily_data(request.form, request.files, METRICS_CONFIG_MAB)
    results = compute_results(daily_data, METRICS_CONFIG_MAB)

    mab_rows = []
    for row in results["rows"]:
        visitors = row["visitors"]
        clicks = row["clicks"]
        ctr = safe_divide(clicks, visitors)
        ci_low, ci_high = confidence_interval(ctr, visitors)
        mab_rows.append({
            "name": row["name"],
            "image_type": row["image_type"],
            "image_path": row.get("image_path", ""),
            "visitors": visitors,
            "clicks": clicks,
            "ctr": ctr,
            "ci_low": ci_low,
            "ci_high": ci_high,
            "reliability": reliability_level(ci_low, ci_high),
            "power": power_level(visitors),
        })

    return render_template(
        "compare.html",
        daily_data=daily_data,
        results=results,
        mab_rows=mab_rows,
        metrics_config=METRICS_CONFIG_MAB,
        metrics_meta=METRICS,
        output_metrics=OUTPUT_METRICS,
    )


@app.route("/api/save", methods=["POST"])
def api_save():
    data = request.get_json()
    if not data:
        return jsonify({"ok": False, "message": "请求数据为空"}), 400
    daily_data = data.get("daily_data")
    experiment_id = data.get("id", "")
    title = data.get("title", "未命名实验")
    method = data.get("method", "mab")
    if not daily_data:
        return jsonify({"ok": False, "message": "缺少 daily_data"}), 400
    experiment_id = save_experiment(experiment_id, title, method, daily_data)
    return jsonify({"ok": True, "id": experiment_id, "message": "保存成功"})


@app.route("/api/load/<experiment_id>", methods=["GET"])
def api_load(experiment_id):
    data = load_experiment(experiment_id)
    if data:
        return jsonify({"ok": True, "data": data})
    return jsonify({"ok": False, "message": "未找到该实验"}), 404


@app.route("/api/list", methods=["GET"])
def api_list():
    method = request.args.get("method", "")
    experiments = list_experiments(method)
    return jsonify({"ok": True, "experiments": experiments})


@app.route("/api/metrics/suggest", methods=["POST"])
def api_suggest_metrics_config():
    data = request.get_json() or {}
    experiment_goal = data.get("experiment_goal") or data.get("goal") or ""
    suggestion = suggest_metrics_config(experiment_goal)
    return jsonify({"ok": True, **suggestion})


@app.route("/api/delete/<experiment_id>", methods=["DELETE"])
def api_delete(experiment_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM experiments WHERE id = %s", (experiment_id,))
    db.commit()
    cur.close()
    db.close()
    return jsonify({"ok": True, "message": "已删除"})


@app.route("/export/pdf", methods=["POST"])
def export_pdf():
    daily_data = parse_daily_data(request.form, request.files, METRICS_CONFIG_MAB)
    results = compute_results(daily_data, METRICS_CONFIG_MAB)
    html = render_template("export.html", daily_data=daily_data, results=results)
    return html


@app.route("/api/export/data", methods=["POST"])
def api_export_data():
    data = request.get_json()
    daily_data = data.get("daily_data") if data else None
    if not daily_data:
        daily_data = DEFAULT_DAILY_DATA
    results = compute_results(daily_data, METRICS_CONFIG_MAB)
    return jsonify({
        "ok": True,
        "daily_data": serialize_daily_data(daily_data),
        "results_summary": results["summary"],
        "rows": [
            {
                "name": row["name"],
                "image_type": row["image_type"],
                "visitors": row["visitors"],
                "clicks": row["clicks"],
                "ctr": round(row["ctr"] * 100, 2),
                "reliability": row["reliability"],
                "power": row["power"],
                "comparison": row["comparison"],
            }
            for row in results["rows"]
        ],
    })


def save_experiment(experiment_id, title, method, daily_data):
    db = get_db()
    cur = db.cursor()
    if not experiment_id:
        experiment_id = uuid.uuid4().hex
    cur.execute(
        "SELECT id FROM experiments WHERE id = %s", (experiment_id,)
    )
    exists = cur.fetchone()
    json_data = json.dumps(daily_data, ensure_ascii=False, default=str)
    if exists:
        cur.execute(
            "UPDATE experiments SET title=%s, method=%s, daily_data=%s WHERE id=%s",
            (title, method, json_data, experiment_id),
        )
    else:
        cur.execute(
            "INSERT INTO experiments (id, title, method, daily_data) VALUES (%s, %s, %s, %s)",
            (experiment_id, title, method, json_data),
        )
    db.commit()
    cur.close()
    db.close()
    return experiment_id


def load_experiment(experiment_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM experiments WHERE id = %s", (experiment_id,))
    row = cur.fetchone()
    cur.close()
    db.close()
    if row:
        return {
            "id": row["id"],
            "title": row["title"],
            "method": row["method"],
            "daily_data": json.loads(row["daily_data"]),
            "created_at": row["created_at"].strftime("%Y-%m-%d %H:%M"),
            "updated_at": row["updated_at"].strftime("%Y-%m-%d %H:%M"),
        }
    return None


def list_experiments(method=""):
    db = get_db()
    cur = db.cursor()
    if method:
        cur.execute("SELECT id, title, method, created_at, updated_at FROM experiments WHERE method=%s ORDER BY updated_at DESC LIMIT 50", (method,))
    else:
        cur.execute("SELECT id, title, method, created_at, updated_at FROM experiments ORDER BY updated_at DESC LIMIT 50")
    rows = cur.fetchall()
    cur.close()
    db.close()
    return [
        {
            "id": row["id"],
            "title": row["title"],
            "method": row["method"],
            "created_at": row["created_at"].strftime("%Y-%m-%d %H:%M"),
            "updated_at": row["updated_at"].strftime("%Y-%m-%d %H:%M"),
        }
        for row in rows
    ]


def serialize_daily_data(daily_data):
    return [
        {
            "date": day["date"],
            "variants": [
                {"name": item["name"], "image_type": item["image_type"], "visitors": item["visitors"], "clicks": item["clicks"]}
                for item in day["data"]
            ],
        }
        for day in daily_data
    ]



if __name__ == "__main__":
    app.run(debug=True)
