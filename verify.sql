-- Reproduces every SQL-derived number quoted in README.md.
--
--     psql philly -f verify.sql
--
-- If a number here disagrees with the README, the README is wrong. Anything
-- the README claims that this file cannot produce must be re-derived,
-- attributed to a live query with its date, or deleted - an unreproducible
-- number makes every other number look unchecked.

\echo '=== 1. raw row counts =========================================='
SELECT 'permits'    AS t, count(*) FROM permits
UNION ALL SELECT 'deeds',      count(*) FROM deeds
UNION ALL SELECT 'properties', count(*) FROM properties;
-- README: 937,512 permits / 582,164 deeds / 583,713 properties
-- NB deeds here are already filtered (DEED, priced, 2010+). The 1.1M figure
-- in Finding 8 refers to the UNFILTERED source table and is NOT in this
-- database. Attribute it or cut it.

\echo '=== 2. the two permitting systems =============================='
SELECT systemofrecord, count(*), min(permitissuedate)::date AS first,
       max(permitissuedate)::date AS last
FROM permits GROUP BY 1 ORDER BY 2 DESC;
-- README Finding 9: HANSEN ends 2020-03-12

\echo '=== 3. the natural key ========================================='
SELECT 'permitnumber alone' AS key, count(*) AS duplicate_values FROM (
  SELECT permitnumber FROM permits GROUP BY 1 HAVING count(*) > 1) t
UNION ALL
SELECT 'systemofrecord+permittype+permitnumber', count(*) FROM (
  SELECT systemofrecord, permittype, permitnumber FROM permits
  GROUP BY 1,2,3 HAVING count(*) > 1) t;
-- README Finding 9 claims 224 for permitnumber alone. Whatever this prints is
-- the truth; the 224 was measured on an earlier population.

\echo '=== 4. the funnel =============================================='
SELECT count(*) AS qualifying FROM qualifying_permits;                 -- 8,868
SELECT count(*) AS new_construction FROM new_construction;             -- 6,774
SELECT typeofwork, count(*),
       round(100.0*count(*)/sum(count(*)) OVER (), 1) AS pct
FROM qualifying_permits GROUP BY 1 ORDER BY 2 DESC;
-- README: 2,094 Addition and/or Alteration = 23.6%

\echo '=== 5. in scope: single parcel, identifier extant =============='
WITH dup AS (SELECT opa_account_num FROM new_construction
             GROUP BY opa_account_num HAVING count(*) > 1)
SELECT count(*) FILTER (WHERE nc.opa_account_num IN (SELECT * FROM dup))
         AS multi_permit_rows,
       count(*) FILTER (WHERE p.parcel_number IS NULL
                          AND nc.opa_account_num NOT IN (SELECT * FROM dup))
         AS retired_only,
       count(*) FILTER (WHERE nc.opa_account_num NOT IN (SELECT * FROM dup)
                          AND p.parcel_number IS NOT NULL)
         AS in_scope
FROM new_construction nc
LEFT JOIN properties p ON p.parcel_number = nc.opa_account_num;
-- README: 1,170 multi-permit, 163 retired, 5,441 in scope

\echo '=== 6. the subdivision mechanism: three measurements ==========='
WITH dup AS (SELECT opa_account_num FROM new_construction
             GROUP BY opa_account_num HAVING count(*) > 1),
j AS (SELECT nc.opa_account_num IN (SELECT * FROM dup) AS multi,
             p.parcel_number IS NOT NULL AS in_opa,
             EXISTS (SELECT 1 FROM deeds d
                     WHERE d.opa_account_num = nc.opa_account_num
                       AND d.display_date > nc.certificateofoccupancydate) AS matched
      FROM new_construction nc
      LEFT JOIN properties p ON p.parcel_number = nc.opa_account_num)
SELECT multi,
       count(*) AS permits,
       round(100.0*count(*) FILTER (WHERE matched)/count(*), 1) AS match_pct,
       round(100.0*count(*) FILTER (WHERE NOT in_opa)/count(*), 1) AS absent_from_opa_pct
FROM j GROUP BY 1;
-- README: match 14.9% vs 37.0%; absent 20.2% vs 2.9%

\echo '=== 7. what the duplicated parcels are (FULL count, not a sample) ==='
WITH dup AS (SELECT opa_account_num FROM new_construction
             GROUP BY opa_account_num HAVING count(*) > 1)
SELECT count(*) AS dup_parcels_in_opa,
       count(*) FILTER (WHERE p.building_code_description LIKE 'VACANT LAND%'
                           OR p.building_code_description LIKE 'PKG LOT%')
         AS still_vacant,
       round(100.0*count(*) FILTER (WHERE p.building_code_description LIKE 'VACANT LAND%'
                                       OR p.building_code_description LIKE 'PKG LOT%')
             /count(*), 1) AS pct
FROM dup JOIN properties p ON p.parcel_number = dup.opa_account_num;
-- README claims "82 of 93", which was the top-15 rows only. Replace with
-- whatever this prints - it is the complete count.

\echo '=== 8. completion date validated ==============================='
SELECT count(*) AS both_dates_present,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY
         EXTRACT(epoch FROM (certificateofoccupancydate - permitcompleteddate))/86400)) AS median_gap_days,
       count(*) FILTER (WHERE certificateofoccupancydate
                            > permitcompleteddate + interval '365 days') AS co_over_a_year_later,
       count(*) FILTER (WHERE permitcompleteddate
                            > certificateofoccupancydate + interval '365 days') AS completed_later
FROM new_construction WHERE permitcompleteddate IS NOT NULL;
-- README: 6,767 present, median gap 0, 176 one-sided, 0 the other way

\echo '=== 9. zero ordering violations ================================'
SELECT count(*) AS co_before_issue
FROM new_construction
WHERE certificateofoccupancydate < permitissuedate;
-- README: zero, in all 6,774

\echo '=== 10. deed snapshot and the unobservable tail ================'
SELECT max(display_date)::date AS deed_snapshot FROM deeds;            -- 2026-09-02
SELECT count(*) AS unobservable
FROM new_construction
WHERE certificateofoccupancydate >= (SELECT max(display_date) FROM deeds);
-- README: 99. The >= is deliberate and was a reconciliation fix: with > this
-- returned 93, because a C of O landing exactly on the snapshot gives a
-- ZERO-day observation window, which is still unobservable. build.py counts
-- `days_observed <= 0`; this now agrees.

\echo '=== 11. parentjobid: closes roadmap Stage 4 ===================='
-- Finding 3 says one building spawns electrical/mechanical/plumbing
-- sub-permits, linked by parentjobid, and that "grouping permits into projects
-- is a required stage". I excluded multi-permit parcels instead of grouping
-- them. This settles whether grouping was ever possible.
--
-- If parentjobid is null across the whole population, the permittype filter
-- (Building / Residential Building) already removed every sub-permit, the
-- 2.76-permits-per-address distortion never touched this analysis, and
-- exclusion was the right call. That is a conclusion, not a gap.
SELECT count(*)                                   AS population,
       count(parentjobid)                         AS with_parent,
       count(DISTINCT parentjobid)                AS distinct_parents
FROM new_construction;

-- And among the duplicated parcels specifically - if they share a parentjobid
-- they are one project and could be grouped; if not, they are siblings.
WITH dup AS (SELECT opa_account_num FROM new_construction
             GROUP BY opa_account_num HAVING count(*) > 1)
SELECT nc.opa_account_num, count(*) AS permits,
       count(nc.parentjobid) AS with_parent,
       count(DISTINCT nc.parentjobid) AS distinct_parents
FROM new_construction nc JOIN dup ON dup.opa_account_num = nc.opa_account_num
GROUP BY 1 ORDER BY 2 DESC LIMIT 10;

\echo '=== 12. SQL/Python reconciliation =============================='
SELECT count(DISTINCT p.cartodb_id) AS matched_sql
FROM new_construction p JOIN deeds d
  ON d.opa_account_num = p.opa_account_num
 AND d.display_date > p.certificateofoccupancydate;
-- Must agree with build.py's printed match count. Two implementations
-- agreeing proves consistency, not correctness - but a disagreement proves
-- a bug, which is why this is worth running.