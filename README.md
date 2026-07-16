#  User Journey Funnel Analysis: FlowBoard SaaS

**A comprehensive, end-to-end funnel analysis of a SaaS project management tool, identifying bottlenecks, quantifying revenue impact, and delivering actionable growth recommendations.**

![Python](https://img.shields.io/badge/Python-3.9+-blue?style=flat-square&logo=python)
![Pandas](https://img.shields.io/badge/Pandas-2.0+-green?style=flat-square&logo=pandas)
![Plotly](https://img.shields.io/badge/Plotly-Interactive-orange?style=flat-square&logo=plotly)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red?style=flat-square&logo=streamlit)

---

##  Executive Summary

Analyzed **50,000+ user journeys** across FlowBoard's product-led growth funnel (Website Visit → Free Trial → Onboarding → "Aha!" Moment → Paid Upgrade → 30-Day Retention).

### Key Findings:
- **Overall conversion rate** from website visit to 30-day retained paid user: ~4-5%
- **Biggest bottleneck**: The signup → onboarding step sees the steepest drop-off
- **Mobile users** have 2.3x higher abandonment at onboarding vs Desktop — a clear UX problem
- **Paid Ads** drive signups but have the worst 30-day retention; **Referral** users retain significantly better (statistically validated)
- **India & Brazil** show severe payment friction at the upgrade stage — likely due to limited payment methods
- **18% of top-of-funnel traffic is bot/non-human**, inflating conversion metrics by up to 7 percentage points
- **The 48-Hour Rule**: Users who complete onboarding within 24 hours are significantly more likely to upgrade and retain

### Revenue Impact:
A **5% improvement** at the biggest bottleneck could recover **$15,000-40,000+/month** in lost revenue.

---

##  Business Problem

FlowBoard is a SaaS project management tool (similar to Notion/Trello). While signups are strong, **paid conversion is lagging** behind industry benchmarks. The Growth team needs to understand:

1. **Where** are users dropping off in the funnel?
2. **Who** is struggling the most (by device, channel, geography)?
3. **How long** does it take users to convert, and does speed matter?
4. **How much revenue** is being lost at each bottleneck?
5. **What specific actions** should the product team take?

---

##  Dataset

| Attribute | Details |
|-----------|---------|
| **Source** | Synthetically generated with realistic behavioral patterns |
| **Users** | ~50,000 unique users |
| **Events** | ~200,000+ event records |
| **Date Range** | January - June 2025 |
| **Funnel Stages** | Website Visit → Signup → Onboarding Complete → First Project → Upgrade to Paid → 30-Day Retained |
| **Dimensions** | Device (3), Channel (5), Country (6), Time |

### Built-in Realistic Patterns:
- Device-based UX friction (Mobile struggles with onboarding)
- Channel-based retention differences (Paid Ads vs Referral)
- Geographic payment friction (India/Brazil)
- ~18% bot/non-human traffic
- Duplicate events, non-linear paths, data quality issues

---

##  Data Cleaning & Assumptions

| Issue | Count | Action Taken |
|-------|-------|--------------|
| Null timestamps | ~2,000 | Dropped (can't order funnel without them) |
| Null session IDs | ~4,000 | Filled with 'unknown' |
| Inconsistent platforms | ~100 | Standardized (e.g., 'MOBILE' → 'Mobile') |
| Bot traffic | ~9,000 users | Flagged using behavioral heuristics (>15 events, <2s inter-event time) |
| Duplicate events | ~20%+ | Deduplicated to first occurrence per user per stage |

### Assumptions:
- ARPU (Average Revenue Per User) = **$29/month**
- A "retained" user is one active at Day 30
- Bot detection threshold: >15 events AND <2 seconds average inter-event time

---

##  Methodology

### Analysis Approach:
1. **Core Funnel Analysis** — Overall conversion rates, drop-off points, revenue impact quantification
2. **Segmented Analysis** — Funnel broken down by Device, Channel, Geography, and Signup Cohort
3. **Time Analysis** — Inter-stage duration distributions, fast vs slow converter comparison, the "48-Hour Rule"
4. **Non-Linear Path Analysis** — Sankey diagram showing actual user journeys (not just the ideal path)
5. **Statistical Validation** — Chi-squared tests, confidence intervals, A/B test power analysis, effect sizes
6. **Bot Traffic Impact** — Before/after comparison showing how non-human traffic distorts metrics

### Statistical Tests:
- **Chi-squared test**: Validated that Mobile vs Desktop conversion difference is statistically significant (p < 0.05)
- **Wilson confidence intervals**: Confirmed sample size provides reliable estimates
- **Two-proportion z-test**: Confirmed Referral retention is significantly higher than Paid Ads
- **Cramér's V effect sizes**: Quantified the strength of segment-based differences
- **A/B test power analysis**: Calculated sample sizes needed to detect 2-10% improvements

---

## Key Findings

### 1. Overall Funnel
The funnel follows a typical SaaS pattern with the steepest drop-offs at signup and the upgrade-to-paid stage.

### 2. Mobile UX Problem
Mobile users complete onboarding at roughly half the rate of Desktop users — a statistically significant difference that represents a major UX gap.

### 3. Channel Economics
Paid Ads drive the highest volume of signups but have the worst 30-day retention. Referral users show both higher conversion AND higher retention, suggesting marketing budget reallocation.

### 4. Geographic Payment Friction
India and Brazil show dramatically lower upgrade rates (~35-40% lower than US/UK), strongly suggesting payment method limitations as the root cause.

### 5. Speed = Conversion
Users who reach the "Aha!" moment (first project created) faster are significantly more likely to upgrade. The relationship is particularly stark around the 48-hour mark.

### 6. Bot Traffic Distortion
18% of top-of-funnel traffic is non-human, inflating website visit counts and distorting conversion calculations. All funnel metrics should be reported post-filtering.

---

##  Actionable Recommendations

| # | Recommendation | Expected Impact | Priority |
|---|---------------|-----------------|----------|
| 1 | **Simplify mobile onboarding** — reduce form fields, add progress indicators | Recover 15-20% of mobile drop-offs |  High |
| 2 | **Add local payment methods** — UPI (India), PIX (Brazil), Boleto | Unlock upgrade conversion in top-2 growth markets |  High |
| 3 | **Implement onboarding nudges** — automated emails/push at 12h, 24h, 36h | Accelerate time-to-Aha!, improve conversion |  Medium |
| 4 | **Shift marketing budget** from Paid Ads → Referral program | Better LTV:CAC ratio, higher retention |  Medium |
| 5 | **Filter bot traffic** from all dashboards and reports | More accurate metrics for decision-making |  Medium |
| 6 | **A/B test checkout simplification** — needs ~5,000 users/group, ~2-3 week test | Validate improvement before full rollout |  Low |

---

##  Tech Stack

| Layer | Tool |
|-------|------|
| Data Processing | Python 3.9+, Pandas, NumPy |
| Visualization | Plotly (interactive), Matplotlib, Seaborn |
| Dashboard | Streamlit |
| Statistical Analysis | SciPy, statsmodels |
| Data Generation | Custom Python script with NumPy |
| Version Control | Git + GitHub |

---

##  Project Structure

```
flowboard-funnel-analysis/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── data/
│   ├── raw/                           # Original generated data
│   │   ├── users.csv                  # 50K user profiles
│   │   └── user_events.csv            # 200K+ event logs
│   ├── cleaned/                       # Processed data
│   │   ├── clean_events.csv
│   │   ├── clean_users.csv
│   │   ├── events_with_bot_flag.csv
│   │   └── user_bot_flags.csv
│   └── generate_data.py               # Synthetic data generator
├── notebooks/
│   ├── 01_data_cleaning.ipynb         # Data quality + bot detection
│   ├── 02_funnel_analysis.ipynb       # Core funnel + revenue impact + Sankey
│   ├── 03_segmented_analysis.ipynb    # Device/Channel/Geo/Cohort breakdowns
│   ├── 04_time_analysis.ipynb         # Duration analysis + 48-hour rule
│   └── 05_statistical_testing.ipynb   # Chi-squared, CIs, power analysis
├── sql/
│   └── funnel_queries.sql             # Production-ready SQL queries
├── dashboard/
│   └── app.py                         # Interactive Streamlit dashboard
└── visuals/                           # Generated visualizations
    ├── funnel_chart.png
    ├── sankey_diagram.png
    ├── revenue_impact.png
    ├── bot_detection.png
    └── ...
```

---

##  How to Run

### 1. Clone the repository
```bash
git clone https://github.com/Nishu9198/flowboard-funnel-analysis.git
cd flowboard-funnel-analysis
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Generate data (optional — data is included)
```bash
python data/generate_data.py
```

### 4. Run notebooks
Open Jupyter and run notebooks 01-05 in order:
```bash
jupyter notebook notebooks/
```

### 5. Launch the dashboard
```bash
streamlit run dashboard/app.py
```

---

