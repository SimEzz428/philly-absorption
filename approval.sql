-- APPROVAL FRICTION - the fourth factor of the original question, untouched
-- until now.
--
--     psql philly -f approval.sql
--
-- Why it is a separate file from verify.sql: a denied permit never receives a
-- certificate of occupancy, so it is excluded from the 6,774 population BY
-- CONSTRUCTION. Denial rate therefore cannot be computed from built.json - it
-- needs the full permits table, and the denominator is every application, not
-- every completion.
--
-- Entitlement delay is capital sitting idle before the clock this project
-- already measures even starts. The roadmap's note: essentially nobody models
-- it.

-- ===========================================================================
-- STEP 1 - do the columns exist? Run this FIRST.
-- The roadmap says denialdate and denialdocumentlink are in the downloaded
-- data, but load_pg.py took its column list from the first NDJSON line, so
-- they may not have survived into the schema.
-- ===========================================================================
\echo '=== columns that could carry denial or status ==='
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'permits'
  AND (column_name ILIKE '%denial%' OR column_name ILIKE '%deni%'
    OR column_name ILIKE '%status%' OR column_name ILIKE '%approv%'
    OR column_name ILIKE '%appl%')
ORDER BY ordinal_position;

\echo '=== what permit types exist at all? ==='
-- Looking for a zoning permit type. Philadelphia requires zoning approval
-- before a building permit on many projects, so the gap between the two on
-- one parcel IS the entitlement delay.
SELECT permittype, count(*) FROM permits GROUP BY 1 ORDER BY 2 DESC LIMIT 25;

\echo '=== and what status values? ==='
SELECT status, count(*) FROM permits GROUP BY 1 ORDER BY 2 DESC LIMIT 20;

-- ===========================================================================
-- STEP 2 - DENIAL RATE. Run only after step 1 confirms a denial column.
-- If denialdate is absent, `status` is the fallback: check step 1's output for
-- a value meaning denied/refused/withdrawn and substitute it below.
-- ===========================================================================
-- \echo '=== denial rate by zip, residential building applications ==='
-- SELECT zip5, applications, denied,
--        round(100.0*denied/applications, 1) AS denial_pct
-- FROM (
--   SELECT left(zip,5) AS zip5,
--          count(*) AS applications,
--          count(*) FILTER (WHERE denialdate IS NOT NULL) AS denied
--   FROM permits
--   WHERE typeofwork LIKE 'New Construction%'
--     AND (permittype = 'Residential Building'
--          OR (permittype = 'Building' AND occupancytype LIKE '%Residential%'))
--   GROUP BY 1
-- ) t
-- WHERE applications >= 30
-- ORDER BY denial_pct DESC;
--
-- Read it against the build-budget ranking. A submarket with a high allowable
-- budget AND a high denial rate is not the bargain it looks like: every denied
-- application is sunk design and filing cost with no asset at the end, and it
-- is not in the 6,774 because it never completed.

-- ===========================================================================
-- STEP 3 - ENTITLEMENT LAG. Run only if step 1 shows a zoning permit type.
-- Same parcel, zoning permit then building permit. This is the segment BEFORE
-- the 369-day land-holding figure overlaps with - read them together, not
-- added.
-- ===========================================================================
-- \echo '=== zoning permit -> building permit, days, by zip ==='
-- WITH zoning AS (
--   SELECT opa_account_num, min(permitissuedate) AS zoned
--   FROM permits
--   WHERE permittype ILIKE '%zoning%' AND opa_account_num IS NOT NULL
--   GROUP BY 1
-- )
-- SELECT left(nc.zip,5) AS zip5, count(*) AS n,
--        round(percentile_cont(0.5) WITHIN GROUP (ORDER BY
--          EXTRACT(epoch FROM (nc.permitissuedate - z.zoned))/86400)) AS median_lag_days
-- FROM new_construction nc
-- JOIN zoning z ON z.opa_account_num = nc.opa_account_num
-- WHERE z.zoned < nc.permitissuedate
-- GROUP BY 1 HAVING count(*) >= 20
-- ORDER BY median_lag_days DESC;

-- ===========================================================================
-- IF THE COLUMNS ARE NOT THERE
-- Then approval friction is not answerable from what you stored, and the
-- honest move is to say so in the README's "cannot be known" table with the
-- reason - the column exists in the source and was dropped at load - rather
-- than leaving the fourth factor silently missing. Re-ingesting for one column
-- is not worth it before Oct 27.
-- ===========================================================================