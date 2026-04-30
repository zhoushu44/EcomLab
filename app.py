from math import sqrt, log
from flask import Flask, render_template, request

app = Flask(__name__)

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


def safe_divide(a, b):
    return a / b if b else 0.0


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


def normalize_shares(scores, min_share=0.05):
    if not scores:
        return []
    clipped_scores = [max(score, 0.0001) for score in scores]
    total = sum(clipped_scores)
    base = [score / total for score in clipped_scores]
    if len(scores) * min_share >= 1:
        return base
    adjusted = [min_share + share * (1 - len(scores) * min_share) for share in base]
    adjusted_total = sum(adjusted)
    return [share / adjusted_total for share in adjusted]


def intervals_overlap(low_a, high_a, low_b, high_b):
    return max(low_a, low_b) <= min(high_a, high_b)


def comparison_label(row, best_row):
    if row["name"] == best_row["name"]:
        return "显著领先" if row["ci_low"] > best_row.get("second_best_ci_high", 0) else "暂时领先"
    if row["ci_high"] < best_row["ci_low"]:
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
        ab_conclusion = "A/B 下主图差异还未完全拉开，固定均分流量会继续消耗表现较弱主图的曝光。"
    else:
        ab_conclusion = "A/B 已能看出主图层级，但仍会让落后主图持续分走固定流量。"

    if winner_ready:
        mab_conclusion = f"MAB 已识别出更稳的优胜主图：{best_row['name']}，可以进入最终上线候选。"
    elif phase == "探索期":
        mab_conclusion = "当前更适合继续探索，MAB 应保持所有主图都有基础曝光，同时把更多流量倾向高潜力图片。"
    else:
        mab_conclusion = "当前更适合用 MAB 做动态分流，先放大领先主图，同时保留未完全证伪的备选图。"

    if len(rows) >= 3 and overlap_count > 0:
        paper_hint = "这更符合论文强调的电商常见场景：多变体、细微差异、区间重叠明显，此时 MAB 通常比 A/B 更省流量。"
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


def compute_results(daily_data):
    variant_totals = {}
    
    for day in daily_data:
        for item in day["data"]:
            name = item["name"]
            if name not in variant_totals:
                variant_totals[name] = {
                    "name": name,
                    "image_type": item["image_type"],
                    "total_visitors": 0,
                    "total_clicks": 0,
                    "daily": [],
                }
            variant_totals[name]["total_visitors"] += item["visitors"]
            variant_totals[name]["total_clicks"] += item["clicks"]
            variant_totals[name]["daily"].append({
                "date": day["date"],
                "visitors": item["visitors"],
                "clicks": item["clicks"],
                "ctr": safe_divide(item["clicks"], item["visitors"]),
            })

    variants = []
    for v in variant_totals.values():
        daily_data_v = v["daily"]
        max_daily_ctr = max(d["ctr"] for d in daily_data_v) if daily_data_v else 1.0
        for d in daily_data_v:
            d["max_ctr"] = max_daily_ctr
            d["bar_height"] = (d["ctr"] / max_daily_ctr) * 100 if max_daily_ctr > 0 else 0
            d["is_highest"] = (d["ctr"] == max_daily_ctr)
        variants.append({
            "name": v["name"],
            "image_type": v["image_type"],
            "visitors": v["total_visitors"],
            "clicks": v["total_clicks"],
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
        mab_score = ctr + exploration_bonus

        scored_rows.append(
            {
                "name": item["name"],
                "image_type": item["image_type"],
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
                "mab_score": mab_score,
                "daily": item.get("daily", []),
            }
        )

    mab_shares = normalize_shares([row["mab_score"] for row in scored_rows])
    for row, share in zip(scored_rows, mab_shares):
        row["mab_share"] = share

    sorted_by_share = sorted(scored_rows, key=lambda row: row["mab_share"], reverse=True)
    best_variant = sorted_by_share[0] if sorted_by_share else None
    second_best_ci_high = sorted_by_share[1]["ci_high"] if len(sorted_by_share) > 1 else 0
    if best_variant:
        best_variant["second_best_ci_high"] = second_best_ci_high

    for row in scored_rows:
        row["comparison"] = comparison_label(row, best_variant) if best_variant else "暂无判断"
        row["recommendation"] = recommendation(row["reliability"], row["power"], row["ctr"], average_ctr, row["comparison"])

    summary = compute_summary(scored_rows, average_ctr, total_visitors)
    return {
        "rows": scored_rows,
        "average_ctr": average_ctr,
        "best_variant": best_variant,
        "total_visitors": total_visitors,
        "total_clicks": sum(v["clicks"] for v in variants),
        "summary": summary,
        "days_count": len(daily_data),
    }


def parse_daily_data(form_data):
    dates = form_data.getlist("date[]")
    daily_data = []
    
    if not dates:
        return DEFAULT_DAILY_DATA

    unique_dates = sorted(set(dates))
    variant_names = set()
    
    for date in unique_dates:
        if not date.strip():
            continue
        
        prefix = f"{date.replace('-', '')}_"
        names = form_data.getlist(f"{prefix}name[]")
        image_types = form_data.getlist(f"{prefix}image_type[]")
        visitors_list = form_data.getlist(f"{prefix}visitors[]")
        clicks_list = form_data.getlist(f"{prefix}clicks[]")
        
        day_data = []
        for idx in range(len(names)):
            name = (names[idx] or f"主图{idx + 1}").strip()
            variant_names.add(name)
            image_type = (image_types[idx] or "未分类").strip()
            try:
                visitors = max(int(visitors_list[idx]), 0)
            except (ValueError, TypeError, IndexError):
                visitors = 0
            try:
                clicks = max(int(clicks_list[idx]), 0)
            except (ValueError, TypeError, IndexError):
                clicks = 0
            clicks = min(clicks, visitors)
            
            day_data.append({
                "name": name,
                "image_type": image_type,
                "visitors": visitors,
                "clicks": clicks,
            })
        
        if day_data:
            daily_data.append({"date": date, "data": day_data})

    return daily_data if daily_data else DEFAULT_DAILY_DATA


@app.route("/", methods=["GET", "POST"])
def index():
    daily_data = DEFAULT_DAILY_DATA
    if request.method == "POST":
        daily_data = parse_daily_data(request.form)
    
    results = compute_results(daily_data)
    return render_template("index.html", daily_data=daily_data, results=results)


if __name__ == "__main__":
    app.run(debug=True)
