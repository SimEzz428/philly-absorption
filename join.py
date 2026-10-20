import json, glob
from collections import defaultdict, Counter
from datetime import datetime
from statistics import median

by_units_total   = Counter()
by_units_matched = Counter()
by_cat_total     = Counter()
by_cat_matched   = Counter()

records = []

def unit_bucket(n):
    if not n:    return "unknown"
    if n == 1:   return "1"
    if n <= 4:   return "2-4"
    if n <= 19:  return "5-19"
    return "20+"

def days_between(iso_a, iso_b):
    a = datetime.fromisoformat(iso_a.replace("Z", "+00:00"))
    b = datetime.fromisoformat(iso_b.replace("Z", "+00:00"))
    return (b - a).days

def pct(values, ps):
    v = sorted(values)
    n = len(v)
    return [(p, v[min(int(n * p / 100), n - 1)]) for p in ps]

def zip5(z):
    return z[:5] if z else None

deeds_by_parcel   = defaultdict(list)
deeds_by_zip_year = defaultdict(list)
total_deeds = 0
matched = 0
no_deeds = 0
no_deed_after_co = 0
unmatched = []

for path in sorted(glob.glob("data/raw/rtt/*.ndjson")):
    for line in open(path):
        row = json.loads(line)
        if not row["opa_account_num"]:
            continue
        deeds_by_parcel[row["opa_account_num"]].append(row)
        total_deeds += 1

        z = zip5(row["zip_code"])
        if (z and row["total_consideration"] and row["total_consideration"] >= 10_000
                and row["property_count"] == 1):
            deeds_by_zip_year[(z, row["display_date"][:4])].append(row["total_consideration"])

zip_year_median = {k: median(v) for k, v in deeds_by_zip_year.items() if len(v) >= 20}
print(f"{len(zip_year_median):,} zip-year price medians (>=20 deeds each)")

opa_by_parcel = {}
for path in sorted(glob.glob("data/raw/opa/*.ndjson")):
    for line in open(path):
        prop = json.loads(line)
        opa_by_parcel[prop["parcel_number"]] = prop

print(f"{len(opa_by_parcel):,} parcels indexed")

def is_qualifying(row):
    if not row["certificateofoccupancydate"]:
        return False
    if not row["opa_account_num"]:
        return False
    if row["permittype"] == "Residential Building":
        return True
    if (row["permittype"] == "Building"
            and row["occupancytype"]
            and "Residential" in row["occupancytype"]):
        return True
    return False

permits = []
permits_by_zip_year = Counter()
for path in sorted(glob.glob("data/raw/permits/*.ndjson")):
    for line in open(path):
        row = json.loads(line)
        if is_qualifying(row):
            permits.append(row)
            issue_yr = row["permitissuedate"][:4] if row["permitissuedate"] else "none"
            permits_by_zip_year[(zip5(row["zip"]), issue_yr)] += 1

for permit in permits:
    parcel  = permit["opa_account_num"]
    co_date = permit["certificateofoccupancydate"]
    bucket  = unit_bucket(permit["numberofunits"])
    by_units_total[bucket] += 1

    prop = opa_by_parcel.get(parcel)
    cat = prop["category_code_description"] if prop else "NOT IN OPA"
    by_cat_total[cat] += 1

    candidates = deeds_by_parcel.get(parcel, [])

    if not candidates:
        no_deeds += 1
        unmatched.append(permit)
        continue

    after = [d for d in candidates if d["display_date"] > co_date]

    if not after:
        no_deed_after_co += 1
        unmatched.append(permit)
        continue

    first_sale = min(after, key=lambda d: d["display_date"])

    matched += 1
    by_units_matched[bucket] += 1
    by_cat_matched[cat] += 1

    records.append({
        "permitnumber":   permit["permitnumber"],
        "cat":            cat,
        "bucket":         bucket,
        "units":          permit["numberofunits"],
        "tract":          permit["censustract"],
        "zip5":           zip5(permit["zip"]),
        "co_date":        co_date[:10],
        "sale_date":      first_sale["display_date"][:10],
        "days":           days_between(co_date, first_sale["display_date"]),
        "price":          first_sale["total_consideration"],
        "property_count": first_sale["property_count"],
    })

nominal = [r for r in records if not r["price"] or r["price"] < 10_000]
bulk    = [r for r in records if r["property_count"] != 1]
clean   = [r for r in records
           if r["price"] and r["price"] >= 10_000
           and r["property_count"] == 1]

for r in clean:
    z = r["zip5"]
    y = int(r["co_date"][:4])
    prior = [zip_year_median[(z, str(yy))]
             for yy in (y - 2, y - 1)
             if (z, str(yy)) in zip_year_median]
    r["zip_price"]    = median(prior) if prior else None
    r["zip_activity"] = sum(permits_by_zip_year[(z, str(yy))] for yy in (y - 2, y - 1))
    this = zip_year_median.get((z, str(y - 1)))
    prev = zip_year_median.get((z, str(y - 3)))
    r["zip_growth"] = (this / prev) if (this and prev) else None

print("\n--- match rate by unit count ---")
for b in ["1", "2-4", "5-19", "20+", "unknown"]:
    t, m = by_units_total[b], by_units_matched[b]
    if t:
        print(f"{b:<9}{m:>6} / {t:<6} = {m/t:.1%}")

total = matched + no_deeds + no_deed_after_co
print(f"\n{len(permits):,} qualifying permits")
print(f"{total_deeds:,} deeds indexed across {len(deeds_by_parcel):,} parcels")
print(f"matched            {matched:,}  ({matched/len(permits):.1%})")
print(f"no deeds on parcel {no_deeds:,}  ({no_deeds/len(permits):.1%})")
print(f"no deed after CofO {no_deed_after_co:,}  ({no_deed_after_co/len(permits):.1%})")
print(f"total              {total:,}   should be {len(permits):,}")

print("\n--- category of the 8,868 ---")
for cat, n in by_cat_total.most_common():
    print(f"{n:>6}  {cat}")

print("\n--- match rate by category ---")
for cat, t in by_cat_total.most_common():
    m = by_cat_matched[cat]
    print(f"{m:>5} / {t:<5} = {m/t:>6.1%}   {cat}")

print("\n--- validation ledger ---")
print(f"  matched                {len(records):>6,}")
print(f"  - nominal (<$10k)      {len(nominal):>6,}")
print(f"  - bulk deeds (>1 prop) {len(bulk):>6,}")
print(f"  = clean                {len(clean):>6,}")
print(f"  (both: {len(nominal) + len(bulk) + len(clean) - len(records):>,})")

neg = [r for r in clean if r["days"] < 0]
print(f"\n{len(neg)} negative days (should be 0)")

print("\n--- ABSORPTION, clean records ---")
recs_by_cat = defaultdict(list)
for r in clean:
    recs_by_cat[r["cat"]].append(r)

print(f"{'n':>5}  {'category':<30}{'median d':>9}{'min':>7}{'max':>7}   median price")
for cat, rs in sorted(recs_by_cat.items(), key=lambda kv: -len(kv[1])):
    days   = sorted(r["days"] for r in rs)
    prices = sorted(r["price"] for r in rs)
    print(f"{len(rs):>5}  {cat:<30}{median(days):>9.0f}{days[0]:>7}{days[-1]:>7}"
          f"   ${median(prices):>12,.0f}")

print("\n--- clean records by C of O year ---")
for yr, c in sorted(Counter(r["co_date"][:4] for r in clean).items()):
    print(f"  {yr}  {c:>5}")

print("\n--- days distribution (clean) ---")
for p, v in pct([r["days"] for r in clean],
                [0, 1, 5, 10, 25, 50, 75, 90, 95, 99, 100]):
    print(f"  p{p:<4} {v:>6} days")

pool = [r for r in clean
        if r["cat"] in ("SINGLE FAMILY", "MULTI FAMILY")
        and r["co_date"][:4] <= "2025"]

print("\n--- FEATURE COVERAGE ---")
have_price = [r for r in pool if r["zip_price"]]
print(f"  zip_price present   {len(have_price):,} / {len(pool):,} = {len(have_price)/len(pool):.0%}")
print(f"  zip_activity range  {min(r['zip_activity'] for r in pool)}"
      f"-{max(r['zip_activity'] for r in pool)}")
print(f"  distinct zips       {len(set(r['zip5'] for r in pool))}")

print("\n--- BASELINE ---")
print(f"{len(pool):,} records, years {min(r['co_date'][:4] for r in pool)}"
      f"-{max(r['co_date'][:4] for r in pool)}")

MIN_OBS = 5

def baseline_table(target, label):
    print(f"\n--- BASELINE: predicting {label} ---")
    print(f"{'fold':<24}{'n':>6}{'global':>10}{'tract':>10}{'zip':>10}{'cat':>10}")
    for cutoff in ["2022", "2023", "2024"]:
        nxt   = str(int(cutoff) + 1)
        train = [r for r in pool if r["co_date"][:4] <= cutoff]
        test  = [r for r in pool if r["co_date"][:4] == nxt]
        if not test:
            continue

        g = median(r[target] for r in train)

        preds = {}
        for key in ("tract", "zip5", "cat"):
            d = defaultdict(list)
            for r in train:
                d[r[key]].append(r[target])
            preds[key] = {k: median(v) for k, v in d.items() if len(v) >= MIN_OBS}

        row = [median(abs(r[target] - g) for r in test)]
        for key in ("tract", "zip5", "cat"):
            row.append(median(abs(r[target] - preds[key].get(r[key], g)) for r in test))

        print(f"train<={cutoff} test {nxt:<10}{len(test):>6}"
              + "".join(f"{v:>10,.0f}" for v in row))

print(f"\n{len(pool):,} records, years {min(r['co_date'][:4] for r in pool)}"
      f"-{max(r['co_date'][:4] for r in pool)}")

baseline_table("days",  "DAYS")
baseline_table("price", "PRICE ($)")