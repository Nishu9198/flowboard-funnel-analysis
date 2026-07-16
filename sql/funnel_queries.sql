-- ============================================================================
-- FlowBoard — Funnel Analysis SQL Queries
-- ============================================================================
-- These queries demonstrate SQL proficiency for funnel analysis.
-- Compatible with: PostgreSQL, MySQL, BigQuery, Snowflake
-- ============================================================================


-- ============================================================================
-- 1. DEDUPLICATION: First Event Per User Per Stage
-- ============================================================================
-- Problem: Users often trigger the same event multiple times (page refresh,
-- double-clicks, retries). We need only the FIRST occurrence.

WITH deduplicated_events AS (
    SELECT 
        event_id,
        user_id,
        event_name,
        event_timestamp,
        session_id,
        platform,
        ROW_NUMBER() OVER (
            PARTITION BY user_id, event_name 
            ORDER BY event_timestamp ASC
        ) AS event_rank
    FROM user_events
    WHERE event_timestamp IS NOT NULL
)
SELECT *
FROM deduplicated_events
WHERE event_rank = 1;


-- ============================================================================
-- 2. BOT DETECTION: Identify Non-Human Traffic
-- ============================================================================
-- Heuristics: Bots fire many events in rapid succession.
-- Flag users with > 15 events AND average inter-event time < 2 seconds.

WITH user_event_stats AS (
    SELECT 
        user_id,
        COUNT(*) AS total_events,
        MIN(event_timestamp) AS first_event,
        MAX(event_timestamp) AS last_event,
        EXTRACT(EPOCH FROM (MAX(event_timestamp) - MIN(event_timestamp))) AS total_duration_seconds
    FROM user_events
    WHERE event_timestamp IS NOT NULL
    GROUP BY user_id
),
bot_scores AS (
    SELECT 
        user_id,
        total_events,
        total_duration_seconds,
        CASE 
            WHEN total_events > 1 
            THEN total_duration_seconds / (total_events - 1) 
            ELSE 999 
        END AS avg_inter_event_seconds,
        CASE 
            WHEN total_events > 15 
                AND total_duration_seconds / NULLIF(total_events - 1, 0) < 2.0
            THEN TRUE 
            ELSE FALSE 
        END AS is_bot
    FROM user_event_stats
)
SELECT 
    is_bot,
    COUNT(*) AS user_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct_of_total
FROM bot_scores
GROUP BY is_bot;


-- ============================================================================
-- 3. CORE FUNNEL: Stage-by-Stage Conversion
-- ============================================================================
-- Calculate how many users reach each stage and the conversion rate.

WITH first_events AS (
    SELECT 
        user_id,
        event_name,
        MIN(event_timestamp) AS first_occurrence
    FROM user_events
    WHERE event_timestamp IS NOT NULL
    GROUP BY user_id, event_name
),
stage_counts AS (
    SELECT 
        event_name AS funnel_stage,
        COUNT(DISTINCT user_id) AS users_at_stage,
        CASE event_name
            WHEN 'website_visit'          THEN 1
            WHEN 'signup'                 THEN 2
            WHEN 'onboarding_complete'    THEN 3
            WHEN 'first_project_created'  THEN 4
            WHEN 'upgrade_to_paid'        THEN 5
            WHEN 'day_30_active'          THEN 6
        END AS stage_order
    FROM first_events
    GROUP BY event_name
)
SELECT 
    funnel_stage,
    users_at_stage,
    ROUND(
        users_at_stage * 100.0 / FIRST_VALUE(users_at_stage) OVER (ORDER BY stage_order),
        2
    ) AS pct_of_top_of_funnel,
    ROUND(
        users_at_stage * 100.0 / LAG(users_at_stage) OVER (ORDER BY stage_order),
        2
    ) AS stage_conversion_rate,
    LAG(users_at_stage) OVER (ORDER BY stage_order) - users_at_stage AS users_dropped
FROM stage_counts
ORDER BY stage_order;


-- ============================================================================
-- 4. SEGMENTED FUNNEL: Conversion by Device Type
-- ============================================================================

WITH first_events AS (
    SELECT 
        ue.user_id,
        ue.event_name,
        u.device,
        MIN(ue.event_timestamp) AS first_occurrence
    FROM user_events ue
    JOIN users u ON ue.user_id = u.user_id
    WHERE ue.event_timestamp IS NOT NULL
    GROUP BY ue.user_id, ue.event_name, u.device
),
device_stage_counts AS (
    SELECT 
        device,
        event_name AS funnel_stage,
        COUNT(DISTINCT user_id) AS users_at_stage,
        CASE event_name
            WHEN 'website_visit'          THEN 1
            WHEN 'signup'                 THEN 2
            WHEN 'onboarding_complete'    THEN 3
            WHEN 'first_project_created'  THEN 4
            WHEN 'upgrade_to_paid'        THEN 5
            WHEN 'day_30_active'          THEN 6
        END AS stage_order
    FROM first_events
    GROUP BY device, event_name
)
SELECT 
    device,
    funnel_stage,
    users_at_stage,
    ROUND(
        users_at_stage * 100.0 / FIRST_VALUE(users_at_stage) OVER (
            PARTITION BY device ORDER BY stage_order
        ),
        2
    ) AS pct_of_device_top,
    ROUND(
        users_at_stage * 100.0 / LAG(users_at_stage) OVER (
            PARTITION BY device ORDER BY stage_order
        ),
        2
    ) AS stage_conversion_rate
FROM device_stage_counts
ORDER BY device, stage_order;


-- ============================================================================
-- 5. TIME BETWEEN STAGES: Inter-Stage Duration Analysis
-- ============================================================================
-- Calculate how long users take between consecutive funnel stages.

WITH first_events AS (
    SELECT 
        user_id,
        event_name,
        MIN(event_timestamp) AS first_occurrence,
        CASE event_name
            WHEN 'website_visit'          THEN 1
            WHEN 'signup'                 THEN 2
            WHEN 'onboarding_complete'    THEN 3
            WHEN 'first_project_created'  THEN 4
            WHEN 'upgrade_to_paid'        THEN 5
            WHEN 'day_30_active'          THEN 6
        END AS stage_order
    FROM user_events
    WHERE event_timestamp IS NOT NULL
    GROUP BY user_id, event_name
),
stage_transitions AS (
    SELECT 
        user_id,
        event_name AS current_stage,
        first_occurrence AS current_time,
        LEAD(event_name) OVER (
            PARTITION BY user_id ORDER BY stage_order
        ) AS next_stage,
        LEAD(first_occurrence) OVER (
            PARTITION BY user_id ORDER BY stage_order
        ) AS next_time,
        EXTRACT(EPOCH FROM (
            LEAD(first_occurrence) OVER (PARTITION BY user_id ORDER BY stage_order) 
            - first_occurrence
        )) / 3600.0 AS hours_to_next_stage
    FROM first_events
)
SELECT 
    current_stage || ' → ' || next_stage AS transition,
    COUNT(*) AS user_count,
    ROUND(AVG(hours_to_next_stage)::NUMERIC, 2) AS avg_hours,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY hours_to_next_stage)::NUMERIC, 2) AS median_hours,
    ROUND(MIN(hours_to_next_stage)::NUMERIC, 2) AS min_hours,
    ROUND(MAX(hours_to_next_stage)::NUMERIC, 2) AS max_hours
FROM stage_transitions
WHERE next_stage IS NOT NULL
    AND hours_to_next_stage > 0
GROUP BY current_stage, next_stage, 
    CASE current_stage
        WHEN 'website_visit' THEN 1
        WHEN 'signup' THEN 2
        WHEN 'onboarding_complete' THEN 3
        WHEN 'first_project_created' THEN 4
        WHEN 'upgrade_to_paid' THEN 5
    END
ORDER BY CASE current_stage
    WHEN 'website_visit' THEN 1
    WHEN 'signup' THEN 2
    WHEN 'onboarding_complete' THEN 3
    WHEN 'first_project_created' THEN 4
    WHEN 'upgrade_to_paid' THEN 5
END;


-- ============================================================================
-- 6. REVENUE IMPACT: Lost Revenue Per Bottleneck
-- ============================================================================
-- Quantify the revenue opportunity at each drop-off point.
-- Assumes ARPU = $29/month.

WITH first_events AS (
    SELECT user_id, event_name
    FROM (
        SELECT 
            user_id, event_name,
            ROW_NUMBER() OVER (PARTITION BY user_id, event_name ORDER BY event_timestamp) AS rn
        FROM user_events
        WHERE event_timestamp IS NOT NULL
    ) t
    WHERE rn = 1
),
stage_counts AS (
    SELECT 
        event_name AS funnel_stage,
        COUNT(DISTINCT user_id) AS users,
        CASE event_name
            WHEN 'website_visit'          THEN 1
            WHEN 'signup'                 THEN 2
            WHEN 'onboarding_complete'    THEN 3
            WHEN 'first_project_created'  THEN 4
            WHEN 'upgrade_to_paid'        THEN 5
            WHEN 'day_30_active'          THEN 6
        END AS stage_order
    FROM first_events
    GROUP BY event_name
),
revenue_impact AS (
    SELECT 
        funnel_stage,
        users,
        LAG(users) OVER (ORDER BY stage_order) AS prev_stage_users,
        LAG(users) OVER (ORDER BY stage_order) - users AS users_lost,
        (LAG(users) OVER (ORDER BY stage_order) - users) * 29 AS monthly_revenue_lost,
        ROUND(
            (LAG(users) OVER (ORDER BY stage_order) - users) * 29 * 0.05,
            2
        ) AS recoverable_at_5pct_improvement
    FROM stage_counts
)
SELECT * FROM revenue_impact
WHERE users_lost IS NOT NULL
ORDER BY monthly_revenue_lost DESC;


-- ============================================================================
-- 7. COHORT ANALYSIS: Weekly Signup Cohorts
-- ============================================================================

WITH first_events AS (
    SELECT 
        ue.user_id,
        ue.event_name,
        u.signup_date,
        DATE_TRUNC('week', u.signup_date) AS signup_week
    FROM user_events ue
    JOIN users u ON ue.user_id = u.user_id
    WHERE ue.event_timestamp IS NOT NULL
    GROUP BY ue.user_id, ue.event_name, u.signup_date
)
SELECT 
    signup_week,
    event_name AS funnel_stage,
    COUNT(DISTINCT user_id) AS users,
    CASE event_name
        WHEN 'website_visit' THEN 1
        WHEN 'signup' THEN 2
        WHEN 'onboarding_complete' THEN 3
        WHEN 'first_project_created' THEN 4
        WHEN 'upgrade_to_paid' THEN 5
        WHEN 'day_30_active' THEN 6
    END AS stage_order
FROM first_events
GROUP BY signup_week, event_name
ORDER BY signup_week, stage_order;
