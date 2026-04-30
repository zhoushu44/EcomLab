# E-commerce Experiment Testing System Specification

## Document Purpose
This specification defines the standard interface and functionality for e-commerce experiment testing systems, applicable to various testing methodologies including A/B Testing, Multi-Armed Bandit, and other statistical experiments.

---

## 1. Core Functional Requirements

### 1.1 Daily Data Input Module

| Feature | Description | Acceptance Criteria |
|---------|-------------|---------------------|
| **Multi-day Data Entry** | Support entering experimental data for multiple consecutive days | Users can add/remove date entries dynamically |
| **Add New Date** | Button to add a new date row | Clicking adds a new date entry with today's date |
| **Restore Default Sample** | Button to reset to demo data | Clicking restores predefined sample data |
| **Calculate Cumulative Results** | Button to trigger calculation | Aggregates all daily data and computes metrics |

### 1.2 Data Input Fields

| Field | Type | Validation | Description |
|-------|------|------------|-------------|
| `date` | Date | Required, valid date format | Date of the experiment day |
| `variant_name` | String | Required, max 50 chars | Name/ID of the tested variant |
| `variant_type` | String | Optional, max 30 chars | Category/classification of variant |
| `visitors` | Integer | Non-negative | Number of visitors exposed |
| `clicks` | Integer | Non-negative, ≤ visitors | Number of clicks recorded |

---

## 2. Output Metrics Specification

### 2.1 Experiment Overview Panel

| Metric | Display Name | Calculation |
|--------|-------------|-------------|
| Testing Days | `testing_days` | Count of unique dates |
| Total Visitors | `total_visitors` | Sum of all visitors |
| Total Clicks | `total_clicks` | Sum of all clicks |
| Overall CTR | `overall_ctr` | total_clicks / total_visitors |
| Current Phase | `current_phase` | Based on sample size |

### 2.2 Statistical Metrics

| Metric | Display Name | Formula |
|--------|-------------|---------|
| CI Lower Bound | `ci_lower` | CTR - 1.96 × √(CTR×(1-CTR)/visitors) |
| CI Upper Bound | `ci_upper` | CTR + 1.96 × √(CTR×(1-CTR)/visitors) |
| Interval Width | `interval_width` | ci_upper - ci_lower |
| Reliability Level | `reliability_level` | Based on interval_width |
| Statistical Power | `power_level` | Based on visitors |

### 2.3 Reliability Level Criteria

| Level | Condition | Color Code |
|-------|-----------|------------|
| High Reliability | interval_width < 5% | Green |
| Medium Reliability | 5% ≤ interval_width < 10% | Yellow |
| Low Reliability | interval_width ≥ 10% | Red |

### 2.4 Statistical Power Criteria

| Level | Condition | Color Code |
|-------|-----------|------------|
| High Power | visitors > 500 | Green |
| Medium Power | 200 < visitors ≤ 500 | Yellow |
| Low Power | visitors ≤ 200 | Red |

---

## 3. UI/UX Specification

### 3.1 Tooltip Explanations

All statistical metrics must include a question mark icon (?) that displays a tooltip on hover with:
- Plain language explanation of the metric
- Mathematical formula (if applicable)
- Interpretation guidance

**Tooltip Template:**
```
[Metric Name]
[Plain language explanation]

Formula: [mathematical formula]

Interpretation: [how to understand the value]
```

### 3.2 Trend Visualization

- **Daily CTR Trend Chart**: Bar chart showing CTR per day
- **Highlight**: Highest CTR day for each variant highlighted
- **X-axis**: Date labels (e.g., "01日", "02日")
- **Y-axis**: Relative CTR percentage

### 3.3 Result Table Columns

| Column | Description | Format |
|--------|-------------|--------|
| Variant ID | Unique identifier | String |
| Variant Type | Classification | String |
| Cumulative CTR | Aggregated CTR | Percentage (2 decimals) |
| CI Lower | Confidence interval lower bound | Percentage (2 decimals) |
| CI Upper | Confidence interval upper bound | Percentage (2 decimals) |
| Interval Width | Width of confidence interval | Percentage (2 decimals) |
| Reliability | Reliability assessment | Colored badge |
| Power | Statistical power | Colored badge |
| Comparison | Relative performance | Text label |
| Traffic Share | Recommended allocation | Percentage (2 decimals) |
| Recommendation | Action suggestion | Text |

---

## 4. Experimental Phase Definition

### 4.1 Phase Determination

| Phase | Condition | Recommended Action |
|-------|-----------|-------------------|
| Exploration | visitors_per_variant < 200 | Collect more data |
| Balanced Observation | 200 ≤ visitors_per_variant < 500 | Monitor closely |
| Decision | visitors_per_variant ≥ 500 | Ready for conclusion |

### 4.2 Decision Readiness Criteria

A variant is ready for full deployment when:
1. Reliability Level = High
2. Statistical Power = High
3. Confidence interval does not overlap with other variants

---

## 5. Paper-Based Best Practices

### 5.1 Daily Operation Workflow

1. **Data Entry**: Record visitor and click counts for each variant daily
2. **Trend Monitoring**: Review daily CTR trends for stability
3. **CI Tracking**: Monitor confidence interval narrowing
4. **Power Assessment**: Wait for sufficient statistical power
5. **Decision Making**: Apply decision readiness criteria
6. **Iteration**: Continue optimization based on results

### 5.2 Key Principles

- **Avoid Early Elimination**: Keep underperforming variants with minimal traffic
- **Dynamic Allocation**: Shift traffic to better-performing variants
- **Statistical Rigor**: Base decisions on confidence intervals and power
- **Continuous Learning**: Adapt based on accumulating evidence

---

## 6. Error Handling

| Error Scenario | Handling | User Feedback |
|----------------|----------|---------------|
| clicks > visitors | Auto-correct to visitors | Warning message displayed |
| Negative values | Auto-convert to 0 | Input validation prevents entry |
| Missing date | Use today's date | Auto-fill with current date |
| Empty form submission | Return error | Highlight required fields |

---

## 7. Technical Requirements

### 7.1 Frontend Stack
- HTML5 / CSS3 / JavaScript (ES6+)
- Responsive design for mobile/desktop
- Tooltip implementation with CSS hover

### 7.2 Backend Requirements
- RESTful API endpoints
- Input validation and sanitization
- Statistical calculation library
- Session management (optional)

### 7.3 Data Formats
- Date: ISO 8601 (YYYY-MM-DD)
- Numbers: Integer for counts, Float for percentages
- Output: JSON for API, HTML for web interface

---

## 8. Glossary

| Term | Definition |
|------|------------|
| CTR | Click-Through Rate: clicks / visitors |
| CI | Confidence Interval: range of plausible values |
| UCB | Upper Confidence Bound: MAB algorithm |
| Statistical Power | Probability of detecting a real effect |
| Reliability | Measure of result stability |

---

**Document Version**: 1.0  
**Last Updated**: May 2026  
**Reference**: Based on "Multi Armed Bandit vs. A/B Tests in E-commerce" research