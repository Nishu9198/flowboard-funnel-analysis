"""
FlowBoard — Interactive Funnel Analysis Dashboard
===================================================
A professional Streamlit dashboard with 5 tabs:
  1. Overview — KPI cards + funnel chart
  2. Segmented — Filtered funnel by device/channel/geography
  3. Time Analysis — Inter-stage durations + fast vs slow
  4. User Paths — Interactive Sankey diagram
  5. Bot Filter — Before/after bot traffic comparison

Run: streamlit run dashboard/app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import os

# ─── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="FlowBoard — Funnel Analysis",
    page_icon=" ",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .main-header h1 {
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
    }
    .main-header p {
        margin: 0.3rem 0 0 0;
        opacity: 0.85;
        font-size: 0.95rem;
    }
    
    .kpi-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        border-left: 4px solid;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .kpi-card h3 {
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
        color: #2c3e50;
    }
    .kpi-card p {
        margin: 0.2rem 0 0 0;
        color: #6c757d;
        font-size: 0.85rem;
        font-weight: 500;
    }
    
    .insight-box {
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 1rem 1.2rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
        font-size: 0.95rem;
        color: #2c3e50;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ─── Constants ────────────────────────────────────────────────────────────────

ARPU = 29
STAGE_ORDER = {
    'website_visit': 1, 'signup': 2, 'onboarding_complete': 3,
    'first_project_created': 4, 'upgrade_to_paid': 5, 'day_30_active': 6,
}
STAGE_LABELS = {
    'website_visit': 'Website Visit', 'signup': 'Free Trial Signup',
    'onboarding_complete': 'Onboarding Complete',
    'first_project_created': 'First Project (Aha!)',
    'upgrade_to_paid': 'Upgrade to Paid', 'day_30_active': '30-Day Retained',
}
STAGE_COLORS = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6', '#1abc9c']

# ─── Data Loading ─────────────────────────────────────────────────────────────

@st.cache_data
def load_data():
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    clean_events_path = os.path.join(base_path, 'data', 'cleaned', 'clean_events.csv')
    clean_users_path = os.path.join(base_path, 'data', 'cleaned', 'clean_users.csv')
    
    # Auto-generate data if it doesn't exist (for Streamlit Cloud deployment)
    if not os.path.exists(clean_events_path):
        import subprocess, sys
        gen_script = os.path.join(base_path, 'data', 'generate_data.py')
        clean_script = os.path.join(base_path, 'data', 'run_cleaning.py')
        subprocess.run([sys.executable, gen_script], cwd=base_path, check=True)
        subprocess.run([sys.executable, clean_script], cwd=base_path, check=True)
    
    events = pd.read_csv(clean_events_path, parse_dates=['event_timestamp'])
    users = pd.read_csv(clean_users_path, parse_dates=['signup_date'])
    
    # Try to load bot-flagged data
    bot_path = os.path.join(base_path, 'data', 'cleaned', 'events_with_bot_flag.csv')
    events_with_bots = None
    if os.path.exists(bot_path):
        events_with_bots = pd.read_csv(bot_path, parse_dates=['event_timestamp'])
    
    return events, users, events_with_bots


def build_funnel(events_df):
    """Build funnel data from events dataframe."""
    funnel = (
        events_df.groupby('event_name')['user_id']
        .nunique()
        .reset_index()
        .rename(columns={'user_id': 'users', 'event_name': 'stage'})
    )
    funnel['stage_order'] = funnel['stage'].map(STAGE_ORDER)
    funnel['stage_label'] = funnel['stage'].map(STAGE_LABELS)
    funnel = funnel.sort_values('stage_order').reset_index(drop=True)
    
    top = funnel.iloc[0]['users']
    funnel['pct_of_total'] = (funnel['users'] / top * 100).round(2)
    funnel['stage_conversion'] = (funnel['users'] / funnel['users'].shift(1) * 100).round(2)
    funnel['users_dropped'] = funnel['users'].shift(1) - funnel['users']
    funnel['drop_rate'] = (100 - funnel['stage_conversion']).round(2)
    funnel['revenue_lost'] = funnel['users_dropped'] * ARPU
    
    return funnel


def create_funnel_chart(funnel_data, title="User Journey Funnel"):
    """Create an interactive plotly funnel chart."""
    fig = go.Figure()
    
    fig.add_trace(go.Funnel(
        y=funnel_data['stage_label'],
        x=funnel_data['users'],
        textinfo="value+percent initial+percent previous",
        textposition="inside",
        marker=dict(
            color=STAGE_COLORS[:len(funnel_data)],
            line=dict(width=2, color='white')
        ),
        connector=dict(line=dict(color="royalblue", width=1.5)),
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=18, family='Inter')),
        font=dict(size=13, family='Inter'),
        height=500,
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    
    return fig


# ─── Load Data ────────────────────────────────────────────────────────────────

events, users, events_with_bots = load_data()

# ─── Header ───────────────────────────────────────────────────────────────────

st.markdown("""
<div class="main-header">
    <h1> FlowBoard — User Journey Funnel Analysis</h1>
    <p>SaaS Product-Led Growth • 50,000 Users • Jan-Jun 2025</p>
</div>
""", unsafe_allow_html=True)

# ─── Tabs ─────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    " Overview", " Segmented", " Time Analysis", " User Paths", " Bot Filter"
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════

with tab1:
    funnel_data = build_funnel(events)
    
    # KPI Cards
    total_users = funnel_data.iloc[0]['users']
    total_converted = funnel_data.iloc[-1]['users']
    overall_conv = funnel_data.iloc[-1]['pct_of_total']
    total_revenue_lost = funnel_data['revenue_lost'].sum()
    biggest_drop_idx = funnel_data['revenue_lost'].dropna().idxmax()
    biggest_bottleneck = funnel_data.loc[biggest_drop_idx, 'stage_label']
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="kpi-card" style="border-color: #3498db;">
            <h3>{total_users:,.0f}</h3>
            <p>Total Website Visitors</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="kpi-card" style="border-color: #2ecc71;">
            <h3>{overall_conv:.1f}%</h3>
            <p>Overall Conversion Rate</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="kpi-card" style="border-color: #e74c3c;">
            <h3>${total_revenue_lost:,.0f}</h3>
            <p>Monthly Revenue Lost</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="kpi-card" style="border-color: #f39c12;">
            <h3>{biggest_bottleneck}</h3>
            <p>Biggest Bottleneck</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Funnel Chart
    col_left, col_right = st.columns([3, 2])
    
    with col_left:
        fig = create_funnel_chart(funnel_data, " Overall User Journey Funnel")
        st.plotly_chart(fig, use_container_width=True)
    
    with col_right:
        st.markdown("###  Revenue Impact per Bottleneck")
        revenue_data = funnel_data[funnel_data['revenue_lost'].notna()].copy()
        revenue_data = revenue_data.sort_values('revenue_lost', ascending=True)
        
        fig_rev = go.Figure(go.Bar(
            y=revenue_data['stage_label'],
            x=revenue_data['revenue_lost'],
            orientation='h',
            marker=dict(
                color=revenue_data['revenue_lost'],
                colorscale='Reds',
                line=dict(width=1, color='white')
            ),
            text=[f"${v:,.0f}" for v in revenue_data['revenue_lost']],
            textposition='outside',
        ))
        fig_rev.update_layout(
            height=400,
            margin=dict(l=20, r=80, t=20, b=20),
            xaxis_title="Monthly Revenue Lost ($)",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig_rev, use_container_width=True)
    
    # Data table
    with st.expander(" View Detailed Funnel Data"):
        display_cols = ['stage_label', 'users', 'pct_of_total', 'stage_conversion', 
                       'users_dropped', 'drop_rate', 'revenue_lost']
        st.dataframe(
            funnel_data[display_cols].rename(columns={
                'stage_label': 'Stage', 'users': 'Users', 
                'pct_of_total': '% of Top', 'stage_conversion': 'Stage Conv %',
                'users_dropped': 'Users Dropped', 'drop_rate': 'Drop Rate %',
                'revenue_lost': 'Revenue Lost ($)'
            }),
            use_container_width=True
        )

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: SEGMENTED
# ═══════════════════════════════════════════════════════════════════════════════

with tab2:
    st.markdown("###  Segmented Funnel Analysis")
    st.markdown("Break down the funnel by different dimensions to find **who** is struggling.")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        segment_option = st.radio(
            "Segment by:",
            ["Device", "Acquisition Channel", "Geography"],
            index=0
        )
        
        segment_map = {
            "Device": "device",
            "Acquisition Channel": "acquisition_channel",
            "Geography": "country",
        }
        segment_col = segment_map[segment_option]
    
    with col2:
        # Build segmented funnel
        seg_funnel = (
            events.groupby([segment_col, 'event_name'])['user_id']
            .nunique()
            .reset_index()
            .rename(columns={'user_id': 'users', 'event_name': 'stage'})
        )
        seg_funnel['stage_order'] = seg_funnel['stage'].map(STAGE_ORDER)
        seg_funnel['stage_label'] = seg_funnel['stage'].map(STAGE_LABELS)
        seg_funnel = seg_funnel.sort_values([segment_col, 'stage_order'])
        
        # Calculate pct of top per segment
        top_per_seg = seg_funnel[seg_funnel['stage'] == 'website_visit'].set_index(segment_col)['users']
        seg_funnel['pct_of_top'] = seg_funnel.apply(
            lambda r: (r['users'] / top_per_seg.get(r[segment_col], 1) * 100), axis=1
        ).round(2)
        
        # Grouped bar chart
        fig = px.bar(
            seg_funnel,
            x='stage_label',
            y='pct_of_top',
            color=segment_col,
            barmode='group',
            title=f"Funnel Conversion by {segment_option}",
            labels={'pct_of_top': '% of Top-of-Funnel', 'stage_label': 'Funnel Stage'},
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(
            height=500,
            font=dict(size=13, family='Inter'),
            legend_title=segment_option,
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Heatmap
    st.markdown("###  Conversion Heatmap")
    pivot = seg_funnel.pivot_table(
        index=segment_col, columns='stage_label', values='pct_of_top'
    )
    stage_order_labels = [STAGE_LABELS[s] for s in sorted(STAGE_ORDER.keys(), key=lambda x: STAGE_ORDER[x])]
    pivot = pivot.reindex(columns=[c for c in stage_order_labels if c in pivot.columns])
    
    fig_heat = px.imshow(
        pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        text_auto='.1f',
        color_continuous_scale='YlOrRd',
        aspect='auto',
        title=f"Conversion Rate (%) — {segment_option} × Funnel Stage",
    )
    fig_heat.update_layout(height=400, font=dict(size=12, family='Inter'))
    st.plotly_chart(fig_heat, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: TIME ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

with tab3:
    st.markdown("###  Time-Based Funnel Analysis")
    st.markdown("Understand **how long** users take between stages and how speed correlates with conversion.")
    
    # Pivot to get user timestamps at each stage
    user_stage_times = events.pivot_table(
        index='user_id', columns='event_name',
        values='event_timestamp', aggfunc='min'
    ).reset_index()
    
    # Calculate inter-stage times
    stages_ordered = sorted(STAGE_ORDER.keys(), key=lambda x: STAGE_ORDER[x])
    time_data = []
    
    for i in range(len(stages_ordered) - 1):
        from_s, to_s = stages_ordered[i], stages_ordered[i+1]
        if from_s in user_stage_times.columns and to_s in user_stage_times.columns:
            dur = (user_stage_times[to_s] - user_stage_times[from_s]).dt.total_seconds() / 3600
            valid = dur[dur > 0].dropna()
            if len(valid) > 0:
                time_data.append({
                    'Transition': f"{STAGE_LABELS[from_s]} → {STAGE_LABELS[to_s]}",
                    'Users': len(valid),
                    'Median (hrs)': round(valid.median(), 1),
                    'Mean (hrs)': round(valid.mean(), 1),
                    'P25 (hrs)': round(valid.quantile(0.25), 1),
                    'P75 (hrs)': round(valid.quantile(0.75), 1),
                })
    
    if time_data:
        time_df = pd.DataFrame(time_data)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("####  Median Time Between Stages")
            fig_time = go.Figure(go.Bar(
                y=time_df['Transition'],
                x=time_df['Median (hrs)'],
                orientation='h',
                marker=dict(
                    color=time_df['Median (hrs)'],
                    colorscale='Viridis',
                    line=dict(width=1, color='white')
                ),
                text=[f"{v:.1f}h" for v in time_df['Median (hrs)']],
                textposition='outside',
            ))
            fig_time.update_layout(
                height=350,
                margin=dict(l=20, r=80, t=20, b=20),
                xaxis_title="Hours",
            )
            st.plotly_chart(fig_time, use_container_width=True)
        
        with col2:
            st.markdown("####  Detailed Time Metrics")
            st.dataframe(time_df, use_container_width=True)
    
    # Fast vs Slow converters
    st.markdown("---")
    st.markdown("### Fast vs Slow Converters")
    
    if 'signup' in user_stage_times.columns and 'first_project_created' in user_stage_times.columns:
        time_to_aha = (
            user_stage_times['first_project_created'] - user_stage_times['signup']
        ).dt.total_seconds() / 3600
        valid_aha = time_to_aha[time_to_aha > 0].dropna()
        
        if len(valid_aha) > 0:
            median_aha = valid_aha.median()
            
            fast_mask = valid_aha <= median_aha
            slow_mask = valid_aha > median_aha
            
            fast_ids = set(user_stage_times.loc[fast_mask.index[fast_mask], 'user_id'])
            slow_ids = set(user_stage_times.loc[slow_mask.index[slow_mask], 'user_id'])
            paid_ids = set(user_stage_times[user_stage_times.get('upgrade_to_paid', pd.Series()).notna()]['user_id']) if 'upgrade_to_paid' in user_stage_times.columns else set()
            
            fast_rate = len(fast_ids & paid_ids) / max(len(fast_ids), 1) * 100
            slow_rate = len(slow_ids & paid_ids) / max(len(slow_ids), 1) * 100
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Median Time to Aha!", f"{median_aha:.1f} hours")
            with col2:
                st.metric("Fast Converter Upgrade Rate", f"{fast_rate:.1f}%")
            with col3:
                st.metric("Slow Converter Upgrade Rate", f"{slow_rate:.1f}%", 
                          delta=f"{slow_rate - fast_rate:.1f}pp vs fast")
            
            st.markdown(f"""
            <div class="insight-box">
                <strong> Key Insight:</strong> Users who reach the "Aha!" moment faster are 
                <strong>{fast_rate/max(slow_rate, 0.01):.1f}x more likely</strong> to upgrade to paid.
                Recommendation: Implement automated onboarding nudges at 12h, 24h, and 36h marks.
            </div>
            """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: USER PATHS (Sankey)
# ═══════════════════════════════════════════════════════════════════════════════

with tab4:
    st.markdown("###  Non-Linear User Paths — Sankey Diagram")
    st.markdown("Real users don't follow a straight line. This shows the **actual paths** users take.")
    
    # Build transitions
    user_paths = (
        events.sort_values(['user_id', 'event_timestamp'])
        .groupby('user_id')['event_name']
        .apply(list)
        .reset_index()
    )
    
    transitions = []
    for _, row in user_paths.iterrows():
        unique_path = []
        seen = set()
        for s in row['event_name']:
            if s not in seen:
                unique_path.append(s)
                seen.add(s)
        
        for i in range(len(unique_path) - 1):
            transitions.append((unique_path[i], unique_path[i+1]))
        
        last = unique_path[-1]
        if STAGE_ORDER.get(last, 0) < 6:
            transitions.append((last, f'Dropped'))
    
    trans_df = pd.DataFrame(transitions, columns=['source', 'target'])
    trans_counts = trans_df.groupby(['source', 'target']).size().reset_index(name='count')
    trans_counts = trans_counts[trans_counts['count'] > 30]
    
    all_nodes = list(set(trans_counts['source'].tolist() + trans_counts['target'].tolist()))
    node_idx = {n: i for i, n in enumerate(all_nodes)}
    
    node_colors = []
    for n in all_nodes:
        if n == 'Dropped':
            node_colors.append('rgba(231, 76, 60, 0.8)')
        elif n in STAGE_ORDER:
            node_colors.append(STAGE_COLORS[STAGE_ORDER[n] - 1])
        else:
            node_colors.append('rgba(149, 165, 166, 0.6)')
    
    link_colors = []
    for _, r in trans_counts.iterrows():
        if 'Dropped' in str(r['target']):
            link_colors.append('rgba(231, 76, 60, 0.2)')
        else:
            link_colors.append('rgba(52, 152, 219, 0.25)')
    
    fig_sankey = go.Figure(go.Sankey(
        node=dict(
            pad=20, thickness=25,
            line=dict(color='white', width=1.5),
            label=[STAGE_LABELS.get(n, n) for n in all_nodes],
            color=node_colors,
        ),
        link=dict(
            source=[node_idx[s] for s in trans_counts['source']],
            target=[node_idx[t] for t in trans_counts['target']],
            value=trans_counts['count'].tolist(),
            color=link_colors,
        )
    ))
    fig_sankey.update_layout(
        title="User Journey Flow — Where Do Users Go?",
        font=dict(size=13, family='Inter'),
        height=600,
    )
    st.plotly_chart(fig_sankey, use_container_width=True)
    
    # Top paths
    with st.expander(" Most Common User Paths"):
        path_strings = user_paths['event_name'].apply(
            lambda p: ' → '.join(dict.fromkeys(p))
        )
        top_paths = path_strings.value_counts().head(10).reset_index()
        top_paths.columns = ['Path', 'Users']
        top_paths['Path'] = top_paths['Path'].apply(
            lambda p: ' → '.join([STAGE_LABELS.get(s.strip(), s.strip()) for s in p.split(' → ')])
        )
        st.dataframe(top_paths, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5: BOT FILTER
# ═══════════════════════════════════════════════════════════════════════════════

with tab5:
    st.markdown("###  Bot Traffic Impact Analysis")
    st.markdown("Compare funnel metrics **before and after** removing bot/non-human traffic.")
    
    if events_with_bots is not None:
        # Build both funnels
        events_bots_dedup = (
            events_with_bots.sort_values('event_timestamp')
            .drop_duplicates(subset=['user_id', 'event_name'], keep='first')
        )
        
        funnel_with = build_funnel(events_bots_dedup)
        funnel_without = build_funnel(events)
        
        # Stats
        bot_users = events_with_bots[events_with_bots['is_bot'] == True]['user_id'].nunique() if 'is_bot' in events_with_bots.columns else 0
        total_all = events_with_bots['user_id'].nunique()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Users (incl. bots)", f"{total_all:,}")
        with col2:
            st.metric("Bot Users Detected", f"{bot_users:,}", delta=f"{bot_users/max(total_all,1)*100:.1f}%")
        with col3:
            st.metric("Clean Human Users", f"{total_all - bot_users:,}")
        
        # Comparison chart
        comparison = funnel_with[['stage_label', 'users', 'pct_of_total']].rename(
            columns={'users': 'with_bots', 'pct_of_total': 'pct_with_bots'}
        ).merge(
            funnel_without[['stage_label', 'users', 'pct_of_total']].rename(
                columns={'users': 'without_bots', 'pct_of_total': 'pct_without_bots'}
            ),
            on='stage_label', how='outer'
        )
        comparison['inflation_pp'] = (comparison['pct_with_bots'] - comparison['pct_without_bots']).round(2)
        
        fig_compare = go.Figure()
        fig_compare.add_trace(go.Bar(
            name='With Bot Traffic',
            x=comparison['stage_label'],
            y=comparison['pct_with_bots'],
            marker_color='rgba(231, 76, 60, 0.6)',
        ))
        fig_compare.add_trace(go.Bar(
            name='Clean (Bots Removed)',
            x=comparison['stage_label'],
            y=comparison['pct_without_bots'],
            marker_color='rgba(46, 204, 113, 0.7)',
        ))
        fig_compare.update_layout(
            title="Funnel Conversion: Before vs After Bot Filtering",
            yaxis_title="% of Top-of-Funnel",
            barmode='group',
            height=450,
            font=dict(size=13, family='Inter'),
        )
        st.plotly_chart(fig_compare, use_container_width=True)
        
        st.markdown(f"""
        <div class="insight-box">
            <strong> Key Finding:</strong> Bot traffic inflates top-of-funnel metrics, 
            making conversion rates appear different than they actually are. 
            Always filter non-human traffic before making business decisions.
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander(" Detailed Comparison"):
            st.dataframe(comparison, use_container_width=True)
    else:
        st.warning("Bot-flagged data not found. Run Notebook 01 (Data Cleaning) first.")


