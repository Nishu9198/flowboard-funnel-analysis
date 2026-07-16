"""
FlowBoard — Synthetic User Journey Data Generator
===================================================
Generates realistic SaaS product funnel data for ~50,000 users
with ~200K+ event records, including:
  - Device/channel/geography-based conversion biases
  - Bot/non-human traffic (~18%)
  - Duplicate events
  - Non-linear paths (skips, loop-backs)
  - Realistic time distributions between stages
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import uuid
import os
import warnings
warnings.filterwarnings('ignore')

np.random.seed(42)

# ─── Configuration ────────────────────────────────────────────────────────────

NUM_USERS = 50000
DATE_START = datetime(2025, 1, 1)
DATE_END = datetime(2025, 6, 30)

FUNNEL_STAGES = [
    'website_visit',
    'signup',
    'onboarding_complete',
    'first_project_created',
    'upgrade_to_paid',
    'day_30_active'
]

DEVICES = ['Desktop', 'Mobile', 'Tablet']
DEVICE_WEIGHTS = [0.50, 0.40, 0.10]

CHANNELS = ['Organic', 'Paid Ads', 'Referral', 'Social Media', 'Direct']
CHANNEL_WEIGHTS = [0.30, 0.25, 0.15, 0.18, 0.12]

COUNTRIES = ['US', 'India', 'UK', 'Germany', 'Brazil', 'Canada']
COUNTRY_WEIGHTS = [0.30, 0.25, 0.15, 0.12, 0.10, 0.08]

# ARPU for revenue impact calculations
ARPU_MONTHLY = 29  # dollars

# ─── Conversion Probabilities ─────────────────────────────────────────────────
# Base conversion rate at each stage (probability of reaching next stage)

BASE_CONVERSION = {
    'website_visit→signup': 0.62,
    'signup→onboarding_complete': 0.55,
    'onboarding_complete→first_project_created': 0.68,
    'first_project_created→upgrade_to_paid': 0.28,
    'upgrade_to_paid→day_30_active': 0.72,
}

# ─── Segment-Specific Multipliers ─────────────────────────────────────────────
# These multiply the base conversion to create realistic segment differences

DEVICE_MULTIPLIERS = {
    # Mobile users struggle more with onboarding (complex forms)
    'Desktop': {
        'website_visit→signup': 1.05,
        'signup→onboarding_complete': 1.10,
        'onboarding_complete→first_project_created': 1.08,
        'first_project_created→upgrade_to_paid': 1.05,
        'upgrade_to_paid→day_30_active': 1.02,
    },
    'Mobile': {
        'website_visit→signup': 0.92,
        'signup→onboarding_complete': 0.72,  # 2.3x higher drop-off vs desktop
        'onboarding_complete→first_project_created': 0.85,
        'first_project_created→upgrade_to_paid': 0.88,
        'upgrade_to_paid→day_30_active': 0.95,
    },
    'Tablet': {
        'website_visit→signup': 1.00,
        'signup→onboarding_complete': 0.90,
        'onboarding_complete→first_project_created': 0.95,
        'first_project_created→upgrade_to_paid': 0.92,
        'upgrade_to_paid→day_30_active': 0.98,
    },
}

CHANNEL_MULTIPLIERS = {
    # Paid ads users convert faster but retain less
    'Organic': {
        'website_visit→signup': 1.00,
        'signup→onboarding_complete': 1.05,
        'onboarding_complete→first_project_created': 1.08,
        'first_project_created→upgrade_to_paid': 1.02,
        'upgrade_to_paid→day_30_active': 1.10,
    },
    'Paid Ads': {
        'website_visit→signup': 1.15,
        'signup→onboarding_complete': 1.00,
        'onboarding_complete→first_project_created': 0.95,
        'first_project_created→upgrade_to_paid': 1.10,
        'upgrade_to_paid→day_30_active': 0.78,  # Lower retention
    },
    'Referral': {
        'website_visit→signup': 1.20,
        'signup→onboarding_complete': 1.12,
        'onboarding_complete→first_project_created': 1.10,
        'first_project_created→upgrade_to_paid': 1.08,
        'upgrade_to_paid→day_30_active': 1.15,
    },
    'Social Media': {
        'website_visit→signup': 0.88,
        'signup→onboarding_complete': 0.82,
        'onboarding_complete→first_project_created': 0.90,
        'first_project_created→upgrade_to_paid': 0.85,
        'upgrade_to_paid→day_30_active': 0.80,
    },
    'Direct': {
        'website_visit→signup': 1.05,
        'signup→onboarding_complete': 1.02,
        'onboarding_complete→first_project_created': 1.00,
        'first_project_created→upgrade_to_paid': 1.00,
        'upgrade_to_paid→day_30_active': 1.05,
    },
}

COUNTRY_MULTIPLIERS = {
    # India/Brazil have payment friction → lower upgrade rates
    'US': {
        'website_visit→signup': 1.05,
        'signup→onboarding_complete': 1.02,
        'onboarding_complete→first_project_created': 1.05,
        'first_project_created→upgrade_to_paid': 1.10,
        'upgrade_to_paid→day_30_active': 1.05,
    },
    'India': {
        'website_visit→signup': 1.02,
        'signup→onboarding_complete': 0.95,
        'onboarding_complete→first_project_created': 1.00,
        'first_project_created→upgrade_to_paid': 0.65,  # Payment friction
        'upgrade_to_paid→day_30_active': 0.90,
    },
    'UK': {
        'website_visit→signup': 1.03,
        'signup→onboarding_complete': 1.05,
        'onboarding_complete→first_project_created': 1.02,
        'first_project_created→upgrade_to_paid': 1.05,
        'upgrade_to_paid→day_30_active': 1.08,
    },
    'Germany': {
        'website_visit→signup': 0.98,
        'signup→onboarding_complete': 1.08,
        'onboarding_complete→first_project_created': 1.05,
        'first_project_created→upgrade_to_paid': 1.00,
        'upgrade_to_paid→day_30_active': 1.10,
    },
    'Brazil': {
        'website_visit→signup': 1.00,
        'signup→onboarding_complete': 0.88,
        'onboarding_complete→first_project_created': 0.92,
        'first_project_created→upgrade_to_paid': 0.60,  # Payment friction
        'upgrade_to_paid→day_30_active': 0.85,
    },
    'Canada': {
        'website_visit→signup': 1.02,
        'signup→onboarding_complete': 1.00,
        'onboarding_complete→first_project_created': 1.03,
        'first_project_created→upgrade_to_paid': 1.05,
        'upgrade_to_paid→day_30_active': 1.05,
    },
}

# ─── Time Between Stages (in hours) ───────────────────────────────────────────
# (mean, std) for lognormal distribution

TIME_BETWEEN_STAGES = {
    'website_visit→signup': (0.5, 0.8),       # Quick — same session
    'signup→onboarding_complete': (4, 12),     # Hours to a day
    'onboarding_complete→first_project_created': (24, 48),  # 1-3 days
    'first_project_created→upgrade_to_paid': (120, 96),     # 5-10 days
    'upgrade_to_paid→day_30_active': (720, 120),            # ~30 days
}

# ─── Bot Traffic Configuration ─────────────────────────────────────────────────

BOT_FRACTION = 0.18  # 18% of website_visit users are bots
BOT_CHARACTERISTICS = {
    'max_events_per_session': 50,   # Bots fire many events rapidly
    'min_inter_event_seconds': 0.2, # Near-instant actions
    'max_inter_event_seconds': 2.0,
    'max_funnel_stage': 2,          # Bots rarely get past signup
}


def generate_user_id():
    """Generate a realistic user ID."""
    return f"user_{uuid.uuid4().hex[:12]}"


def generate_session_id():
    """Generate a session ID."""
    return f"sess_{uuid.uuid4().hex[:10]}"


def get_conversion_prob(stage_transition, device, channel, country):
    """Calculate adjusted conversion probability based on segment multipliers."""
    base = BASE_CONVERSION[stage_transition]
    device_mult = DEVICE_MULTIPLIERS[device][stage_transition]
    channel_mult = CHANNEL_MULTIPLIERS[channel][stage_transition]
    country_mult = COUNTRY_MULTIPLIERS[country][stage_transition]
    
    # Combine multipliers (geometric mean approach to avoid extreme values)
    adjusted = base * device_mult * channel_mult * country_mult
    return min(adjusted, 0.98)  # Cap at 98%


def generate_time_delta(stage_transition, is_fast_converter=False):
    """Generate realistic time delta between funnel stages."""
    mean_hours, std_hours = TIME_BETWEEN_STAGES[stage_transition]
    
    if is_fast_converter:
        mean_hours *= 0.4
        std_hours *= 0.3
    
    # Use lognormal for right-skewed distribution (realistic)
    hours = np.random.lognormal(
        mean=np.log(max(mean_hours, 0.1)),
        sigma=np.log(max(std_hours / mean_hours + 1, 1.1))
    )
    return timedelta(hours=max(hours, 0.05))


def generate_bot_events(user_id, signup_date, device, channel, country):
    """Generate bot-like event patterns."""
    events = []
    session_id = generate_session_id()
    current_time = signup_date
    
    # Bots fire rapid events — mostly just website_visit and maybe signup
    num_events = np.random.randint(15, BOT_CHARACTERISTICS['max_events_per_session'])
    bot_stages = FUNNEL_STAGES[:np.random.choice([1, 2], p=[0.6, 0.4])]
    
    for i in range(num_events):
        event_name = np.random.choice(bot_stages)
        inter_event = np.random.uniform(
            BOT_CHARACTERISTICS['min_inter_event_seconds'],
            BOT_CHARACTERISTICS['max_inter_event_seconds']
        )
        current_time += timedelta(seconds=inter_event)
        
        events.append({
            'event_id': f"evt_{uuid.uuid4().hex[:12]}",
            'user_id': user_id,
            'event_name': event_name,
            'event_timestamp': current_time,
            'session_id': session_id,
            'platform': device,
        })
    
    return events


def generate_human_events(user_id, signup_date, device, channel, country):
    """Generate realistic human user journey events."""
    events = []
    current_time = signup_date
    session_id = generate_session_id()
    
    is_fast_converter = np.random.random() < 0.15  # 15% are fast converters
    
    # Every user has a website visit
    events.append({
        'event_id': f"evt_{uuid.uuid4().hex[:12]}",
        'user_id': user_id,
        'event_name': 'website_visit',
        'event_timestamp': current_time,
        'session_id': session_id,
        'platform': device,
    })
    
    # Add some duplicate events (user refreshing, clicking multiple times)
    if np.random.random() < 0.25:  # 25% chance of duplicate
        dup_time = current_time + timedelta(seconds=np.random.randint(1, 30))
        events.append({
            'event_id': f"evt_{uuid.uuid4().hex[:12]}",
            'user_id': user_id,
            'event_name': 'website_visit',
            'event_timestamp': dup_time,
            'session_id': session_id,
            'platform': device,
        })
    
    # Walk through funnel stages
    transitions = list(BASE_CONVERSION.keys())
    
    for i, transition in enumerate(transitions):
        prob = get_conversion_prob(transition, device, channel, country)
        
        if np.random.random() > prob:
            # User dropped off — but maybe they come back later (non-linear)
            if np.random.random() < 0.08:  # 8% chance of loop-back
                # User comes back after a delay and tries previous stage again
                loop_time = current_time + timedelta(hours=np.random.randint(12, 72))
                prev_stage = FUNNEL_STAGES[i]
                new_session = generate_session_id()
                events.append({
                    'event_id': f"evt_{uuid.uuid4().hex[:12]}",
                    'user_id': user_id,
                    'event_name': prev_stage,
                    'event_timestamp': loop_time,
                    'session_id': new_session,
                    'platform': device,
                })
            break
        
        # User proceeds to next stage
        time_delta = generate_time_delta(transition, is_fast_converter)
        current_time += time_delta
        next_stage = FUNNEL_STAGES[i + 1]
        
        # New session if time gap > 30 minutes
        if time_delta > timedelta(minutes=30):
            session_id = generate_session_id()
        
        events.append({
            'event_id': f"evt_{uuid.uuid4().hex[:12]}",
            'user_id': user_id,
            'event_name': next_stage,
            'event_timestamp': current_time,
            'session_id': session_id,
            'platform': device,
        })
        
        # Add duplicate events for certain stages (user clicking button twice)
        if next_stage in ['signup', 'onboarding_complete'] and np.random.random() < 0.20:
            dup_time = current_time + timedelta(seconds=np.random.randint(1, 15))
            events.append({
                'event_id': f"evt_{uuid.uuid4().hex[:12]}",
                'user_id': user_id,
                'event_name': next_stage,
                'event_timestamp': dup_time,
                'session_id': session_id,
                'platform': device,
            })
        
        # Some users skip a step (non-linear path) — e.g., create project before completing onboarding
        if next_stage == 'onboarding_complete' and np.random.random() < 0.05:
            skip_time = current_time + timedelta(minutes=np.random.randint(5, 60))
            events.append({
                'event_id': f"evt_{uuid.uuid4().hex[:12]}",
                'user_id': user_id,
                'event_name': 'first_project_created',
                'event_timestamp': skip_time,
                'session_id': session_id,
                'platform': device,
            })
    
    return events


def generate_users():
    """Generate user profiles."""
    users = []
    date_range_days = (DATE_END - DATE_START).days
    
    for _ in range(NUM_USERS):
        signup_date = DATE_START + timedelta(
            days=np.random.randint(0, date_range_days),
            hours=np.random.randint(0, 24),
            minutes=np.random.randint(0, 60),
        )
        
        device = np.random.choice(DEVICES, p=DEVICE_WEIGHTS)
        channel = np.random.choice(CHANNELS, p=CHANNEL_WEIGHTS)
        country = np.random.choice(COUNTRIES, p=COUNTRY_WEIGHTS)
        
        users.append({
            'user_id': generate_user_id(),
            'signup_date': signup_date,
            'device': device,
            'acquisition_channel': channel,
            'country': country,
            'plan_type': 'Free Trial',
        })
    
    return pd.DataFrame(users)


def generate_all_events(users_df):
    """Generate event logs for all users."""
    all_events = []
    num_bots = int(len(users_df) * BOT_FRACTION)
    bot_indices = set(np.random.choice(len(users_df), size=num_bots, replace=False))
    
    for idx, row in users_df.iterrows():
        if idx in bot_indices:
            events = generate_bot_events(
                row['user_id'], row['signup_date'],
                row['device'], row['acquisition_channel'], row['country']
            )
        else:
            events = generate_human_events(
                row['user_id'], row['signup_date'],
                row['device'], row['acquisition_channel'], row['country']
            )
        all_events.extend(events)
    
    return pd.DataFrame(all_events)


def add_data_quality_issues(events_df):
    """Add realistic data quality issues."""
    df = events_df.copy()
    
    # 1. Add some null timestamps (~0.5%)
    null_mask = np.random.random(len(df)) < 0.005
    df.loc[null_mask, 'event_timestamp'] = pd.NaT
    
    # 2. Add some null session_ids (~1%)
    null_sess_mask = np.random.random(len(df)) < 0.01
    df.loc[null_sess_mask, 'session_id'] = None
    
    # 3. Add some inconsistent platform values (~0.3%)
    inconsistent_mask = np.random.random(len(df)) < 0.003
    df.loc[inconsistent_mask, 'platform'] = np.random.choice(
        ['desktop', 'MOBILE', 'mobile_web', ''], 
        size=inconsistent_mask.sum()
    )
    
    return df


def main():
    print("=" * 60)
    print("  FlowBoard — Synthetic Data Generator")
    print("=" * 60)
    
    # Create output directories
    raw_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'raw')
    os.makedirs(raw_dir, exist_ok=True)
    
    cleaned_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'cleaned')
    os.makedirs(cleaned_dir, exist_ok=True)
    
    # Step 1: Generate users
    print("\n[1/4] Generating 50,000 user profiles...")
    users_df = generate_users()
    print(f"  ✓ {len(users_df):,} users generated")
    print(f"  ✓ Devices: {dict(users_df['device'].value_counts())}")
    print(f"  ✓ Channels: {dict(users_df['acquisition_channel'].value_counts())}")
    print(f"  ✓ Countries: {dict(users_df['country'].value_counts())}")
    
    # Step 2: Generate events
    print("\n[2/4] Generating user journey events...")
    events_df = generate_all_events(users_df)
    print(f"  ✓ {len(events_df):,} raw events generated")
    print(f"  ✓ Event distribution:")
    for event, count in events_df['event_name'].value_counts().items():
        print(f"      {event}: {count:,}")
    
    # Step 3: Add data quality issues
    print("\n[3/4] Adding realistic data quality issues...")
    events_df = add_data_quality_issues(events_df)
    null_ts = events_df['event_timestamp'].isna().sum()
    null_sess = events_df['session_id'].isna().sum()
    print(f"  ✓ Null timestamps: {null_ts}")
    print(f"  ✓ Null session IDs: {null_sess}")
    
    # Step 4: Save
    print("\n[4/4] Saving datasets...")
    
    users_path = os.path.join(raw_dir, 'users.csv')
    events_path = os.path.join(raw_dir, 'user_events.csv')
    
    users_df.to_csv(users_path, index=False)
    events_df.to_csv(events_path, index=False)
    
    print(f"  ✓ Users saved → {users_path}")
    print(f"  ✓ Events saved → {events_path}")
    
    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Total users:      {len(users_df):,}")
    print(f"  Total events:     {len(events_df):,}")
    print(f"  Bot users (~18%): {int(len(users_df) * BOT_FRACTION):,}")
    print(f"  Date range:       {DATE_START.date()} to {DATE_END.date()}")
    print(f"  Users file size:  {os.path.getsize(users_path) / 1024 / 1024:.1f} MB")
    print(f"  Events file size: {os.path.getsize(events_path) / 1024 / 1024:.1f} MB")
    print("=" * 60)


if __name__ == '__main__':
    main()
