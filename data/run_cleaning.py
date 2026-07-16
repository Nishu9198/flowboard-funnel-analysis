"""
Run the data cleaning pipeline directly (equivalent to Notebook 01).
This ensures the cleaned data files exist for all other notebooks and the dashboard.
"""
import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("  FlowBoard — Data Cleaning Pipeline")
print("=" * 60)

# ── 1. Load raw data ──
print("\n[1/7] Loading raw data...")
users_raw = pd.read_csv(os.path.join(BASE, 'data', 'raw', 'users.csv'), parse_dates=['signup_date'])
events_raw = pd.read_csv(os.path.join(BASE, 'data', 'raw', 'user_events.csv'), parse_dates=['event_timestamp'])
print(f"  Users:  {len(users_raw):,} rows")
print(f"  Events: {len(events_raw):,} rows")

# ── 2. Handle missing values ──
print("\n[2/7] Handling missing values...")
events = events_raw.copy()
null_ts = events['event_timestamp'].isna().sum()
events = events.dropna(subset=['event_timestamp'])
null_sess = events['session_id'].isna().sum()
events['session_id'] = events['session_id'].fillna('unknown')
print(f"  Dropped {null_ts:,} null timestamps")
print(f"  Filled {null_sess:,} null session IDs")

# ── 3. Standardize platform values ──
print("\n[3/7] Standardizing platform values...")
platform_mapping = {
    'Desktop': 'Desktop', 'desktop': 'Desktop',
    'Mobile': 'Mobile', 'MOBILE': 'Mobile', 'mobile_web': 'Mobile',
    'Tablet': 'Tablet',
}
events['platform'] = events['platform'].map(platform_mapping)
unmapped = events['platform'].isna().sum()
events = events.dropna(subset=['platform'])
print(f"  Standardized. Dropped {unmapped} unmappable rows.")

# ── 4. Bot detection ──
print("\n[4/7] Detecting bot traffic...")
user_stats = events.groupby('user_id').agg(
    total_events=('event_id', 'count'),
    first_event=('event_timestamp', 'min'),
    last_event=('event_timestamp', 'max'),
).reset_index()

user_stats['duration_seconds'] = (user_stats['last_event'] - user_stats['first_event']).dt.total_seconds()
user_stats['avg_inter_event_sec'] = np.where(
    user_stats['total_events'] > 1,
    user_stats['duration_seconds'] / (user_stats['total_events'] - 1),
    999
)
user_stats['is_bot'] = (user_stats['total_events'] > 15) & (user_stats['avg_inter_event_sec'] < 2.0)
bot_count = user_stats['is_bot'].sum()
print(f"  Flagged {bot_count:,} bot users ({bot_count/len(user_stats)*100:.1f}%)")

# ── 5. Filter bots ──
print("\n[5/7] Filtering bot traffic...")
bot_user_ids = set(user_stats[user_stats['is_bot']]['user_id'])

events_all = events.copy()
events_all['is_bot'] = events_all['user_id'].isin(bot_user_ids)

events_human = events[~events['user_id'].isin(bot_user_ids)].copy()
print(f"  Bot events: {events_all['is_bot'].sum():,}")
print(f"  Human events: {len(events_human):,}")

# ── 6. Deduplicate ──
print("\n[6/7] Deduplicating events...")
before = len(events_human)
events_human = events_human.sort_values('event_timestamp')
events_dedup = events_human.drop_duplicates(subset=['user_id', 'event_name'], keep='first').copy()
removed = before - len(events_dedup)
print(f"  Removed {removed:,} duplicate events")

# Add stage ordering
STAGE_ORDER = {
    'website_visit': 1, 'signup': 2, 'onboarding_complete': 3,
    'first_project_created': 4, 'upgrade_to_paid': 5, 'day_30_active': 6,
}
STAGE_LABELS = {
    'website_visit': 'Website Visit', 'signup': 'Free Trial Signup',
    'onboarding_complete': 'Onboarding Complete', 'first_project_created': 'First Project (Aha!)',
    'upgrade_to_paid': 'Upgrade to Paid', 'day_30_active': '30-Day Retained',
}
events_dedup['stage_order'] = events_dedup['event_name'].map(STAGE_ORDER)
events_dedup['stage_label'] = events_dedup['event_name'].map(STAGE_LABELS)

# Merge with user attributes
users_clean = users_raw[~users_raw['user_id'].isin(bot_user_ids)].copy()
events_final = events_dedup.merge(
    users_clean[['user_id', 'device', 'acquisition_channel', 'country', 'plan_type']],
    on='user_id', how='left'
)

# ── 7. Save ──
print("\n[7/7] Saving cleaned data...")
cleaned_dir = os.path.join(BASE, 'data', 'cleaned')
os.makedirs(cleaned_dir, exist_ok=True)

events_final.to_csv(os.path.join(cleaned_dir, 'clean_events.csv'), index=False)
users_clean.to_csv(os.path.join(cleaned_dir, 'clean_users.csv'), index=False)
events_all.to_csv(os.path.join(cleaned_dir, 'events_with_bot_flag.csv'), index=False)
user_stats[['user_id', 'is_bot', 'total_events', 'avg_inter_event_sec']].to_csv(
    os.path.join(cleaned_dir, 'user_bot_flags.csv'), index=False
)

print(f"  ✓ clean_events.csv        ({len(events_final):,} rows)")
print(f"  ✓ clean_users.csv          ({len(users_clean):,} rows)")
print(f"  ✓ events_with_bot_flag.csv ({len(events_all):,} rows)")
print(f"  ✓ user_bot_flags.csv")

# Summary
print("\n" + "=" * 60)
print("  CLEANING COMPLETE")
print("=" * 60)
print(f"  Raw events:     {len(events_raw):,}")
print(f"  Clean events:   {len(events_final):,}")
print(f"  Clean users:    {len(users_clean):,}")
print(f"  Bots removed:   {bot_count:,}")
print(f"  Dupes removed:  {removed:,}")
print("=" * 60)
