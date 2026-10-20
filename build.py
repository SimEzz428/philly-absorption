import json, glob, os
from collections import defaultdict, Counter
from statistics import median
from lib import (zip5, unit_bucket, days_between,
                 approx_gfa_per_unit, trailing_window)

os.makedirs("data", exist_ok=True)

TOO_LONG_DAYS = 3650
LAND_LOOKBACK_YEARS = 3


DENIED_STATUS = {"Denied", "Refused", "Amendment Denied"}
ZONING_TYPES = {"Zoning", "ZP_ZONING", "ZP_USE", "ZP_ZON/USE"}


def is_application(row):
    tow = row.get("typeofwork")
    if not tow or not tow.startswith("New Construction"):
        return False
    if row["permittype"] == "Residential Building":
        return True
    return (row["permittype"] == "Building"
            and row["occupancytype"]
            and "Residential" in row["occupancytype"])


def is_qualifying(row):
    if not row["certificateofoccupancydate"]:
        return False
    if not row["opa_account_num"]:
        return False
    tow = row.get("typeofwork")
    if not tow or not tow.startswith("New Construction"):
        return False
    if row["permittype"] == "Residential Building":
        return True
    if (row["permittype"] == "Building"
            and row["occupancytype"]
            and "Residential" in row["occupancytype"]):
        return True
    return False


opa_by_parcel = {}
for path in sorted(glob.glob("data/raw/opa/*.ndjson")):
    for line in open(path):
        prop = json.loads(line)
        opa_by_parcel[prop["parcel_number"]] = (
            prop.get("category_code_description"),
            prop.get("building_code_description"),
        )
print(f"{len(opa_by_parcel):,} parcels indexed")


deeds_by_parcel   = defaultdict(list)
deeds_by_zip_year = defaultdict(list)
land_by_zip_year  = defaultdict(list)
total_deeds = 0
deed_snapshot = ""            
for path in sorted(glob.glob("data/raw/rtt/*.ndjson")):
    for line in open(path):
        row = json.loads(line)
        if not row["opa_account_num"]:
            continue
        deeds_by_parcel[row["opa_account_num"]].append(row)
        total_deeds += 1

        if row["display_date"] > deed_snapshot:
            deed_snapshot = row["display_date"]

        z = zip5(row["zip_code"])
        real_sale = (z and row["total_consideration"]
                     and row["total_consideration"] >= 10_000
                     and row["property_count"] == 1)
        if not real_sale:
            continue

        yr = row["display_date"][:4]
        deeds_by_zip_year[(z, yr)].append(row["total_consideration"])

        p = opa_by_parcel.get(row["opa_account_num"])
        if p and p[0] and "VACANT LAND" in p[0]:
            land_by_zip_year[(z, yr)].append(row["total_consideration"])

zip_year_median = {k: median(v) for k, v in deeds_by_zip_year.items() if len(v) >= 20}
zip_land_median = {k: median(v) for k, v in land_by_zip_year.items()  if len(v) >= 10}
print(f"{total_deeds:,} deeds across {len(deeds_by_parcel):,} parcels")
print(f"{len(zip_year_median):,} zip-year sale medians  |  {len(zip_land_median):,} land medians")
print(f"deed snapshot: {deed_snapshot[:10]}")


permits = []
permits_by_zip_year = Counter()
apps_by_zip   = Counter()      
denied_by_zip = Counter()     
zoning_apps_by_zip   = Counter()   
zoning_denied_by_zip = Counter()   
zoning_by_parcel = {}          
for path in sorted(glob.glob("data/raw/permits/*.ndjson")):
    for line in open(path):
        row = json.loads(line)

       
        if row["permittype"] in ZONING_TYPES:
            z = zip5(row["zip"])
            if z and len(z) == 5 and z.isdigit():
                zoning_apps_by_zip[z] += 1
                if row.get("status") in DENIED_STATUS:
                    zoning_denied_by_zip[z] += 1

            if row["opa_account_num"]:
                d = row["permitissuedate"]
                if d:
                    p = row["opa_account_num"]
                    if p not in zoning_by_parcel or d < zoning_by_parcel[p]:
                        zoning_by_parcel[p] = d

        if is_application(row):
            z = zip5(row["zip"])
            apps_by_zip[z] += 1
            if row.get("status") in DENIED_STATUS:
                denied_by_zip[z] += 1

        if is_qualifying(row):
            permits.append(row)
            yr = row["permitissuedate"][:4] if row["permitissuedate"] else "none"
            permits_by_zip_year[(zip5(row["zip"]), yr)] += 1

print(f"{len(permits):,} qualifying permits        <- expect 6,774")
print(f"{sum(apps_by_zip.values()):,} residential new-construction building "
      f"applications, {sum(denied_by_zip.values()):,} refused "
      f"({sum(denied_by_zip.values())/max(sum(apps_by_zip.values()),1):.2%})")
print(f"{sum(zoning_apps_by_zip.values()):,} ZONING applications, "
      f"{sum(zoning_denied_by_zip.values()):,} refused "
      f"({sum(zoning_denied_by_zip.values())/max(sum(zoning_apps_by_zip.values()),1):.2%})"
      f"   <- where refusal actually happens")
print(f"{len(zoning_by_parcel):,} parcels with a zoning permit")

MIN_APPS = 30

denial_rate = {z: denied_by_zip[z] / n
               for z, n in apps_by_zip.items() if z and n >= MIN_APPS}
zoning_denial_rate = {z: zoning_denied_by_zip[z] / n
                      for z, n in zoning_apps_by_zip.items() if z and n >= MIN_APPS}


permits_per_parcel = Counter(p["opa_account_num"] for p in permits)


by_units_total   = Counter(); by_units_matched = Counter()
by_cat_total     = Counter(); by_cat_matched   = Counter()
build_counts     = Counter()      
gfa_counts       = Counter()      
obs_counts       = Counter()      
land_counts      = Counter()      
neg_by_system    = Counter()
records = []
matched = no_deeds = no_deed_after_co = 0

for permit in permits:
    parcel  = permit["opa_account_num"]
    co_date = permit["certificateofoccupancydate"]
    issue   = permit["permitissuedate"]
    done    = permit["permitcompleteddate"]
    units   = permit["numberofunits"]
    area    = permit["areaofdisturbance"]
    stories = permit["numberofstories"]
    bucket  = unit_bucket(units)


    observed = days_between(co_date, deed_snapshot)
    obs_counts["unobservable" if observed <= 0 else "ok"] += 1

    prop = opa_by_parcel.get(parcel)
    cat  = "NOT IN OPA" if prop is None else (prop[0] or "UNCLASSIFIED")

    by_units_total[bucket] += 1
    by_cat_total[cat] += 1

    
    build_days = days_between(issue, co_date)
    if build_days is None:
        build_counts["no_issue_date"] += 1
    elif build_days < 0:
        build_counts["negative"] += 1
        neg_by_system[permit.get("systemofrecord")] += 1
    elif build_days > TOO_LONG_DAYS:
        build_counts["too_long"] += 1
    else:
        build_counts["ok"] += 1

   
    gfa_per_unit = approx_gfa_per_unit(area, stories, units)
    if gfa_per_unit is None:
        gfa_counts["no_units" if not units else "no_area_or_stories"] += 1
    else:
        gfa_counts["ok"] += 1

    candidates = deeds_by_parcel.get(parcel, [])
    after = [d for d in candidates if d["display_date"] > co_date]

    if not candidates:
        no_deeds += 1
        first_sale = None
    elif not after:
        no_deed_after_co += 1
        first_sale = None
    else:
        first_sale = min(after, key=lambda d: d["display_date"])
        matched += 1
        by_units_matched[bucket] += 1
        by_cat_matched[cat] += 1

   
    acq = acq_lag = None
    if not issue:
        land_counts["no_issue_date"] += 1
    else:
        before = [d for d in candidates if d["display_date"] < issue]
        priced = [d for d in before
                  if d["total_consideration"] and d["total_consideration"] >= 10_000]
        single = [d for d in priced if d["property_count"] == 1]
        if single:
            acq = max(single, key=lambda d: d["display_date"])
            acq_lag = days_between(acq["display_date"], issue)
            land_counts["observed" if acq_lag <= LAND_LOOKBACK_YEARS * 365
                        else "outside_window"] += 1
        elif priced:
            land_counts["bulk_only"] += 1
        elif before:
            land_counts["nominal_only"] += 1
        else:
            land_counts["no_prior_deed"] += 1

    records.append({
        "permitnumber":        permit["permitnumber"],
        "system":              permit.get("systemofrecord"),
        "cat":                 cat,
        "bucket":              bucket,
        "units":               units,
        "tract":               permit["censustract"],
        "zip5":                zip5(permit["zip"]),
        "area":                area,
        "stories":             stories,
        "issue_date":          issue[:10] if issue else None,
        "co_date":             co_date[:10],
        "completed_date":      done[:10] if done else None,
        "permit_to_co_days":   build_days,
        "approx_gfa_per_unit": gfa_per_unit,
       
        "days_observed":       observed,
        "observable":          observed > 0,
     
        "land_price":          acq["total_consideration"] if acq else None,
        "land_date":           acq["display_date"][:10] if acq else None,
        "land_lag_days":       acq_lag,
        "land_in_window":      (acq_lag is not None
                                and acq_lag <= LAND_LOOKBACK_YEARS * 365),
       
        "land_to_sale_days":   (days_between(acq["display_date"],
                                             first_sale["display_date"])
                                if (acq and first_sale) else None),

        "entitlement_days":    days_between(zoning_by_parcel.get(parcel), issue),
        "zip_denial_rate":     denial_rate.get(zip5(permit["zip"])),
        "zip_zoning_denial":   zoning_denial_rate.get(zip5(permit["zip"])),
        "multi_permit":        permits_per_parcel[parcel] > 1,
        "parcel_in_opa":       prop is not None,
        "matched":             first_sale is not None,
        "sale_date":           first_sale["display_date"][:10] if first_sale else None,
        "days":                days_between(co_date, first_sale["display_date"]) if first_sale else None,
        "price":               first_sale["total_consideration"] if first_sale else None,
        "property_count":      first_sale["property_count"] if first_sale else None,
    })


for r in records:
    if r["matched"]:
        r["nominal"] = not r["price"] or r["price"] < 10_000
        r["bulk"]    = r["property_count"] != 1
        r["clean"]   = not (r["nominal"] or r["bulk"])
    else:
        r["nominal"] = r["bulk"] = r["clean"] = None

    
    z = r["zip5"]
    y = int(r["issue_date"][:4]) if r["issue_date"] else None
    window = trailing_window(y)
    if z and window:
        prior = [zip_year_median[(z, yy)] for yy in window if (z, yy) in zip_year_median]
        land  = [zip_land_median[(z, yy)] for yy in window if (z, yy) in zip_land_median]
        r["zip_price"]    = median(prior) if prior else None
        r["zip_land"]     = median(land) if land else None
        r["zip_spread"]   = (r["zip_price"] - r["zip_land"]) if (prior and land) else None
        r["zip_activity"] = sum(permits_by_zip_year[(z, yy)] for yy in window)
    else:
        r["zip_price"] = r["zip_land"] = r["zip_spread"] = r["zip_activity"] = None


bd = sorted(r["permit_to_co_days"] for r in records
            if r["permit_to_co_days"] is not None and r["permit_to_co_days"] >= 0)
if bd:
    def pctl(p):
        return bd[min(int(len(bd) * p), len(bd) - 1)]
    print(f"\npermit->CO days   n={len(bd):,}   "
          f"p10 {pctl(.10):,}  p50 {pctl(.50):,}  p90 {pctl(.90):,}  "
          f"p99 {pctl(.99):,}  max {bd[-1]:,}")

by_cat_build = defaultdict(list)
for r in records:
    d = r["permit_to_co_days"]
    if d is not None and 0 <= d <= TOO_LONG_DAYS:
        by_cat_build[r["cat"]].append(d)
print("\npermit->CO median by category")
for cat, v in sorted(by_cat_build.items(), key=lambda kv: -len(kv[1]))[:8]:
    print(f"  {cat:<30} n={len(v):>5,}   median {median(v):>6,.0f}")


lags = sorted(r["land_lag_days"] for r in records if r["land_lag_days"] is not None)
if lags:
    print(f"\nLAND ACQUISITION - coverage by lookback window "
          f"({len(records):,} permits)")
    print(f"  {'window':<12}{'with a price':>14}{'coverage':>10}   median land $")
    for yrs in (1, 2, 3, 5, 10, None):
        cut = yrs * 365 if yrs else 10**9
        hit = [r for r in records
               if r["land_lag_days"] is not None and r["land_lag_days"] <= cut]
        label = f"{yrs} year{'s' if yrs and yrs > 1 else ''}" if yrs else "no limit"
        med = median(r["land_price"] for r in hit) if hit else 0
        star = "  <- LAND_LOOKBACK_YEARS" if yrs == LAND_LOOKBACK_YEARS else ""
        print(f"  {label:<12}{len(hit):>14,}{len(hit)/len(records):>10.1%}"
              f"   ${med:>11,.0f}{star}")
    print(f"  acquisition -> permit issue: median {median(lags):,} days "
          f"({median(lags)/365:.1f} years of holding before entitlement)")

def pctl_e(v, p):
    return v[min(int(len(v) * p), len(v) - 1)]

ent = sorted(r["entitlement_days"] for r in records
             if r["entitlement_days"] is not None and r["entitlement_days"] >= 0)
if ent:
    print("\nAPPROVAL FRICTION")
    worst = sorted(zoning_denial_rate.items(), key=lambda kv: -kv[1])[:5]
    best  = sorted(zoning_denial_rate.items(), key=lambda kv: kv[1])[:5]
    print("  zoning refusal, highest: " + "  ".join(f"{z} {r:.1%}" for z, r in worst))
    print("  zoning refusal, lowest:  " + "  ".join(f"{z} {r:.1%}" for z, r in best))
    print("\n  ENTITLEMENT QUEUE - zoning permit -> building permit")
    print(f"  n={len(ent):,}   p10 {pctl_e(ent,.10):,}  median {median(ent):,.0f}  "
          f"p90 {pctl_e(ent,.90):,} days")
    print("  ^ sits INSIDE the acquisition->permit gap, so it EXPLAINS the wait")
    print("    rather than extending it. At a 9% rate on $100k of land, each")
    print(f"    100 days of queue costs ${100/365*0.09*100_000:,.0f}.")

full = [r["land_to_sale_days"] for r in records if r["land_to_sale_days"]]
if full:
    print(f"\nFULL CAPITAL CLOCK - land out to final sale, n={len(full):,}")
    print(f"  median {median(full):,.0f} days "
          f"({median(full)/365:.1f} years), vs permit->sale only")

print(f"\nbuild_counts  {dict(build_counts)}  sum={sum(build_counts.values()):,}")
print(f"gfa_counts    {dict(gfa_counts)}  sum={sum(gfa_counts.values()):,}")
print(f"obs_counts    {dict(obs_counts)}  sum={sum(obs_counts.values()):,}")
print(f"land_counts   {dict(land_counts)}  sum={sum(land_counts.values()):,}")
if neg_by_system:
    print(f"negatives by system  {dict(neg_by_system)}")
print(f"match  {matched:,} + no_deeds {no_deeds:,} + no_deed_after_co {no_deed_after_co:,} "
      f"= {matched + no_deeds + no_deed_after_co:,}")


json.dump({
    "deed_snapshot":      deed_snapshot[:10],
    "too_long_days":      TOO_LONG_DAYS,
    "permits_total":      len(permits),
    "deeds_indexed":      total_deeds,
    "parcels_with_deeds": len(deeds_by_parcel),
    "opa_parcels":        len(opa_by_parcel),
    "matched":            matched,
    "no_deeds":           no_deeds,
    "no_deed_after_co":   no_deed_after_co,
    "build_counts":       dict(build_counts),
    "gfa_counts":         dict(gfa_counts),
    "obs_counts":         dict(obs_counts),
    "land_counts":        dict(land_counts),
    "land_lookback_years": LAND_LOOKBACK_YEARS,
    "applications":       sum(apps_by_zip.values()),
    "refused":            sum(denied_by_zip.values()),
    "denial_rate_by_zip": denial_rate,
    "zoning_applications": sum(zoning_apps_by_zip.values()),
    "zoning_refused":      sum(zoning_denied_by_zip.values()),
    "zoning_denial_by_zip": zoning_denial_rate,
    "neg_by_system":      dict(neg_by_system),
    "by_units_total":     dict(by_units_total),
    "by_units_matched":   dict(by_units_matched),
    "by_cat_total":       dict(by_cat_total),
    "by_cat_matched":     dict(by_cat_matched),
    "records":            records,
}, open("data/built.json", "w"))

print(f"\nwrote data/built.json - {len(records):,} records ({matched:,} matched)")