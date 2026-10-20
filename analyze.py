import json
from collections import defaultdict, Counter
from statistics import median

B = json.load(open("data/built.json"))
records = B["records"]

def in_scope(r):
    return (not r["multi_permit"]) and r["parcel_in_opa"]

scope = [r for r in records if in_scope(r)]
clean = [r for r in scope if r["clean"]]

CATS = ("SINGLE FAMILY", "MULTI FAMILY")

print(f"{B['permits_total']:,} qualifying permits   (new construction only)")
print(f"{len(scope):,} in scope             (single parcel, identifier extant)")
print(f"{B['deeds_indexed']:,} deeds across {B['parcels_with_deeds']:,} parcels")
print(f"deed snapshot        {B['deed_snapshot']}")

m_scope = sum(1 for r in scope if r["matched"])
print(f"\nmatched, all permits {B['matched']:,}  ({B['matched']/B['permits_total']:.1%})")
print(f"matched, in scope    {m_scope:,}  ({m_scope/len(scope):.1%})   <- the honest rate")
print(f"no deeds on parcel   {B['no_deeds']:,}")
print(f"no deed after CofO   {B['no_deed_after_co']:,}")

print("\n--- match rate by category, in scope ---")
t_by_cat = Counter(r["cat"] for r in scope)
m_by_cat = Counter(r["cat"] for r in scope if r["matched"])
for cat, t in t_by_cat.most_common():
    m = m_by_cat.get(cat, 0)
    print(f"{m:>5} / {t:<5} = {m/t:>6.1%}   {cat}")

print("\n--- validation ledger, in scope ---")
nominal = [r for r in scope if r["nominal"]]
bulk    = [r for r in scope if r["bulk"]]
both    = [r for r in scope if r["nominal"] and r["bulk"]]
print(f"  matched                {m_scope:>6,}")
print(f"  - nominal (<$10k)      {len(nominal):>6,}")
print(f"  - bulk deeds (>1 prop) {len(bulk):>6,}")
print(f"  + overlap (both)       {len(both):>6,}")
print(f"  = clean                {len(clean):>6,}")

print("\n--- CENSORING CHECK: build time by ISSUE year ---")
print(f"{'issue yr':<10}{'n':>7}{'median d':>10}{'p90':>8}   follow-up to snapshot")
by_iy = defaultdict(list)
for r in scope:
    if r["issue_date"] and r["permit_to_co_days"] is not None:
        by_iy[r["issue_date"][:4]].append(r["permit_to_co_days"])
snap_year = int(B["deed_snapshot"][:4])
for yr in sorted(by_iy):
    v = sorted(by_iy[yr])
    p90 = v[min(int(len(v) * .9), len(v) - 1)]
    print(f"{yr:<10}{len(v):>7,}{median(v):>10,.0f}{p90:>8,}"
          f"   ~{(snap_year - int(yr)) * 365:,} days")
print("^ a cohort whose follow-up window is shorter than its own p90 is censored")

print("\n--- ABSORPTION, clean, in scope ---")
by_cat = defaultdict(list)
for r in clean:
    by_cat[r["cat"]].append(r)
print(f"{'n':>5}  {'category':<28}{'build d':>9}{'sell d':>8}{'total':>8}   median price")
for cat, rs in sorted(by_cat.items(), key=lambda kv: -len(kv[1])):
    sell  = median(r["days"] for r in rs)
    bld   = [r["permit_to_co_days"] for r in rs if r["permit_to_co_days"] is not None]
    bldm  = median(bld) if bld else 0
    print(f"{len(rs):>5}  {cat:<28}{bldm:>9,.0f}{sell:>8,.0f}{bldm+sell:>8,.0f}"
          f"   ${median(r['price'] for r in rs):>12,.0f}")

SALE_CUT    = "2025"
ISSUE_FLOOR = "2019"
ISSUE_CUT   = "2022"

sale_pool = [r for r in clean
             if r["cat"] in CATS and r["co_date"][:4] <= SALE_CUT
             and r["issue_date"]
             and ISSUE_FLOOR <= r["issue_date"][:4] <= ISSUE_CUT]

build_pool = [r for r in scope
              if r["cat"] in CATS and r["issue_date"]
              and ISSUE_FLOOR <= r["issue_date"][:4] <= ISSUE_CUT
              and r["permit_to_co_days"] is not None]

print(f"\nsale_pool  {len(sale_pool):,}   (clean sale, CofO <= {SALE_CUT}, issue "
      f"{ISSUE_FLOOR}-{ISSUE_CUT})   <- must equal model.py")
print(f"build_pool {len(build_pool):,}   (no sale needed, issue "
      f"{ISSUE_FLOOR}-{ISSUE_CUT})   <- must equal model.py")

print("\n--- FEATURE COVERAGE ---")
for name, p in (("sale_pool", sale_pool), ("build_pool", build_pool)):
    print(f"  {name}")
    for f in ("zip_price", "zip_land", "zip_spread", "approx_gfa_per_unit"):
        have = sum(1 for r in p if r[f])
        print(f"    {f:<22}{have:>6,} = {have/len(p):>4.0%}")

MIN_OBS = 5

def baseline_table(pool, target, label, split="issue_date", cutoffs=("2019", "2020", "2021")):
    print(f"\n--- BASELINE: {label}   (split on {split}) ---")
    print(f"{'fold':<26}{'n':>6}{'global':>10}{'tract':>10}{'zip':>10}{'cat':>10}{'best':>8}")
    for cutoff in cutoffs:
        nxt   = str(int(cutoff) + 1)
        train = [r for r in pool if r[split] and r[split][:4] <= cutoff]
        test  = [r for r in pool if r[split] and r[split][:4] == nxt]
        if not test or not train:
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
        lift = (row[0] - min(row[1:])) / row[0]
        print(f"train<={cutoff} test {nxt:<12}{len(test):>6}"
              + "".join(f"{v:>10,.0f}" for v in row)
              + f"{lift:>8.1%}")

baseline_table(build_pool, "permit_to_co_days", "BUILD DAYS (permit -> CofO)")
baseline_table(sale_pool,  "days",              "SELL DAYS (CofO -> first sale)")
baseline_table(sale_pool,  "price",             "PRICE ($)")

by_zip = defaultdict(list)
for r in sale_pool:
    by_zip[r["zip5"]].append(r)

rows = []
for z, rs in by_zip.items():
    if len(rs) < 20:
        continue
    lands = [r["zip_land"] for r in rs if r["zip_land"]]
    bld   = [r["permit_to_co_days"] for r in rs if r["permit_to_co_days"] is not None]
    if not lands or not bld:
        continue
    sell  = median(r["days"] for r in rs)
    build = median(bld)
    total = build + sell
    sale  = median(r["price"] for r in rs)
    land  = median(lands)
    spread = sale - land
    rows.append((z, len(rs), build, sell, total, sale, land, spread,
                 spread / max(total, 1), spread / max(sell, 1)))

hdr = (f"{'zip':<8}{'n':>5}{'build':>7}{'sell':>6}{'total':>7}"
       f"{'sale $':>12}{'land $':>11}{'spread $':>11}{'$/day':>8}")

print("\n--- ZIP MARKETS (20+ projects), ranked by SPREAD ---")
print(hdr)
for t in sorted(rows, key=lambda x: -x[7]):
    print(f"{t[0]:<8}{t[1]:>5}{t[2]:>7,.0f}{t[3]:>6,.0f}{t[4]:>7,.0f}"
          f"{t[5]:>12,.0f}{t[6]:>11,.0f}{t[7]:>11,.0f}{t[8]:>8,.0f}")

print("\n--- same markets, ranked by SPREAD PER DAY OF TOTAL CARRY ---")
print(hdr)
for t in sorted(rows, key=lambda x: -x[8]):
    print(f"{t[0]:<8}{t[1]:>5}{t[2]:>7,.0f}{t[3]:>6,.0f}{t[4]:>7,.0f}"
          f"{t[5]:>12,.0f}{t[6]:>11,.0f}{t[7]:>11,.0f}{t[8]:>8,.0f}")

def spearman(early, late):
    keys = sorted(set(early) & set(late))
    if len(keys) < 4:
        return None, len(keys)
    def ranks(d):
        order = sorted(keys, key=lambda k: d[k])
        return {k: i for i, k in enumerate(order)}
    re_, rl = ranks(early), ranks(late)
    n = len(keys)
    d2 = sum((re_[k] - rl[k]) ** 2 for k in keys)
    return 1 - 6 * d2 / (n * (n * n - 1)), n

def period_medians(pool, target, lo, hi, key="zip5", min_n=8):
    d = defaultdict(list)
    for r in pool:
        if r[key] and r[target] is not None and lo <= r["issue_date"][:4] <= hi:
            d[r[key]].append(r[target])
    return {k: median(v) for k, v in d.items() if len(v) >= min_n}

print("\n--- PERSISTENCE: does the submarket ranking hold? ---")
print(f"{'target':<22}{'pool':<12}{'zips':>6}{'rho':>8}   reading")
for target, pool, label in (("permit_to_co_days", build_pool, "build_pool"),
                            ("days",              sale_pool,  "sale_pool"),
                            ("price",             sale_pool,  "sale_pool")):
    early = period_medians(pool, target, "2019", "2020")
    late  = period_medians(pool, target, "2021", "2022")
    rho, n = spearman(early, late)
    if rho is None:
        print(f"{target:<22}{label:<12}{n:>6}       -   too few shared zips")
        continue
    read = ("stable" if rho > 0.6 else
            "weak" if rho > 0.3 else
            "NOT persistent" if rho > -0.3 else "reversed")
    print(f"{target:<22}{label:<12}{n:>6}{rho:>8.2f}   {read}")

print("""
rho near 1    the same submarkets lead in both periods: the ranking transfers
rho near 0    the order scrambles between periods. A ranking built on 2019-20
              would NOT have predicted 2021-22, which caps what the tool can
              claim no matter how good the within-period fit looks
2019-20 vs 2021-22, by permit issue year, zips with 8+ projects in each.""")

print("\n--- how much the ranking moves ---")
by_spread = [t[0] for t in sorted(rows, key=lambda x: -x[7])]
by_total  = [t[0] for t in sorted(rows, key=lambda x: -x[8])]
by_sell   = [t[0] for t in sorted(rows, key=lambda x: -x[9])]
print(f"{'zip':<8}{'by spread':>11}{'by total carry':>16}{'by sell carry':>15}")
for z in by_spread:
    print(f"{z:<8}{by_spread.index(z)+1:>11}{by_total.index(z)+1:>16}"
          f"{by_sell.index(z)+1:>15}")