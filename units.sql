\echo '=== Q4.1 alteration vs new construction, apartment parcels ==='
SELECT CASE WHEN p.typeofwork LIKE 'New Construction%' THEN 'new construction'
            ELSE 'addition/alteration' END AS work,
       count(*) AS permits,
       count(p.numberofunits) AS with_units,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY p.numberofunits)) AS med_units,
       round(percentile_cont(0.9) WITHIN GROUP (ORDER BY p.numberofunits)) AS p90_units,
       max(p.numberofunits) AS max_units
FROM permits p
JOIN properties pr ON pr.parcel_number = p.opa_account_num
WHERE pr.category_code_description LIKE 'APARTMENTS%'
  AND p.permittype IN ('Building', 'Residential Building')
  AND p.numberofunits IS NOT NULL
GROUP BY 1;

\echo '=== Q4.2 do permits on one parcel share a unit count? ==='
SELECT opa_account_num,
       count(*) AS permits,
       count(DISTINCT numberofunits) AS distinct_unit_values,
       min(numberofunits) AS min_u, max(numberofunits) AS max_u,
       sum(numberofunits) AS summed
FROM new_construction
GROUP BY 1 HAVING count(*) > 20
ORDER BY 2 DESC LIMIT 8;
-- distinct_unit_values = 1 across the board  -> building size
-- several distinct values summing to a plausible project -> units created

-- ===========================================================================
-- Q6 - the coverage collapse. Two populations, because the answer differs.
    -- ===========================================================================
\echo '=== Q6.1 coverage by issue year, ALL new-construction permits ==='
SELECT date_part('year', permitissuedate)::int AS yr,
       count(*) AS permits,
       count(numberofunits) AS with_units,
       round(100.0*count(numberofunits)/count(*), 1) AS pct
FROM permits
WHERE typeofwork LIKE 'New Construction%'
  AND permitissuedate IS NOT NULL
GROUP BY 1 ORDER BY 1;

\echo '=== Q6.2 coverage by issue year, INSIDE the analysis population ==='
SELECT date_part('year', permitissuedate)::int AS yr,
       count(*) AS permits,
       count(numberofunits) AS with_units,
       round(100.0*count(numberofunits)/count(*), 1) AS pct
FROM new_construction
WHERE permitissuedate IS NOT NULL
GROUP BY 1 ORDER BY 1;
